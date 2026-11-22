"""
Federated continual learning on the IEEE 33-bus benchmark: one run = (data seed, topology,
buffer length W, topology features). Prequential protocol: every round each client first
predicts its new samples with its current model (test), then stores them (75% train buffer,
25% held-out calibration buffer), trains E local SGD steps, and communicates.

Outputs per-sample test records for analyse.py: logits of the deployed model, of a locally
fine-tuned copy (star only), temperature-scaled probabilities (static / sliding) and conformal
set coverage/size for four calibration schemes.
"""
import sys, itertools, numpy as np

ZONES = [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12], [13, 14, 15, 16, 17],
         [18, 19, 20, 21], [22, 23, 24], [25, 26, 27, 28], [29, 30, 31, 32]]
K = 8
ZONE_TREE = [(0, 1), (0, 4), (0, 5), (1, 2), (1, 6), (2, 3), (6, 7)]   # physical adjacency of zones
N_ROUNDS, E_LOCAL, BATCH, LR, HIDDEN = 300, 5, 32, 0.1, 32
ALPHA = 0.10
STATIC_CAL = (100, 125)        # rounds whose calibration data form the static calibration set
CAL_WIN = 24                   # sliding calibration window (rounds)


# ------------------------------------------------------------------ communication graphs
def metropolis(edges, n=K):
    A = np.zeros((n, n))
    for i, j in edges:
        A[i, j] = A[j, i] = 1
    d = A.sum(1); W = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            if A[i, j]:
                W[i, j] = 1.0 / (1 + max(d[i], d[j]))
        W[i, i] = 1 - W[i].sum()
    return W


def hop_dist(edges, n=K):
    D = np.full((n, n), 99); np.fill_diagonal(D, 0)
    for i, j in edges:
        D[i, j] = D[j, i] = 1
    for k in range(n):
        D = np.minimum(D, D[:, [k]] + D[[k], :])
    return D


def misaligned_tree():
    """Same tree shape as the physical zone graph, relabelled so that physically adjacent
    zones are as far apart as possible in the communication graph (isomorphic => same spectral gap)."""
    best, best_perm = -1, None
    for perm in itertools.permutations(range(K)):
        e = [(perm[i], perm[j]) for i, j in ZONE_TREE]
        D = hop_dist(e)
        s = sum(D[i, j] for i, j in ZONE_TREE)
        if s > best:
            best, best_perm = s, perm
    return [(best_perm[i], best_perm[j]) for i, j in ZONE_TREE]


TOPOLOGIES = {"star": None, "aligned": ZONE_TREE, "misaligned": misaligned_tree(), "local": []}


def spectral_gap(W):
    ev = np.sort(np.abs(np.linalg.eigvals(W)))[::-1]
    return 1 - ev[1]


# ------------------------------------------------------------------ model: 1-hidden-layer MLP
def init_params(rng, d):
    return {"W1": rng.normal(0, 1 / np.sqrt(d), (d, HIDDEN)), "b1": np.zeros(HIDDEN),
            "W2": rng.normal(0, 1 / np.sqrt(HIDDEN), (HIDDEN, 1)), "b2": np.zeros(1)}


def flat(p):
    return np.concatenate([p[k].ravel() for k in ("W1", "b1", "W2", "b2")])


def unflat(v, d):
    i = 0; out = {}
    for k, shp in (("W1", (d, HIDDEN)), ("b1", (HIDDEN,)), ("W2", (HIDDEN, 1)), ("b2", (1,))):
        n = int(np.prod(shp)); out[k] = v[i:i + n].reshape(shp); i += n
    return out


def logits(p, X):
    return (np.tanh(X @ p["W1"] + p["b1"]) @ p["W2"] + p["b2"]).ravel()


def sgd_steps(p, X, y, rng, steps=E_LOCAL):
    p = {k: v.copy() for k, v in p.items()}
    n = len(y)
    if n == 0:
        return p
    for _ in range(steps):
        idx = rng.integers(0, n, min(BATCH, n))
        xb, yb = X[idx], y[idx]
        h = np.tanh(xb @ p["W1"] + p["b1"])
        z = (h @ p["W2"] + p["b2"]).ravel()
        pr = 1 / (1 + np.exp(-np.clip(z, -30, 30)))
        dz = ((pr - yb) / len(yb))[:, None]
        gW2 = h.T @ dz; gb2 = dz.sum(0)
        da = (dz @ p["W2"].T) * (1 - h ** 2)
        gW1 = xb.T @ da; gb1 = da.sum(0)
        p["W1"] -= LR * gW1; p["b1"] -= LR * gb1; p["W2"] -= LR * gW2; p["b2"] -= LR * gb2
    return p


def sig(z):
    return 1 / (1 + np.exp(-np.clip(z, -30, 30)))


T_GRID = np.exp(np.linspace(np.log(0.25), np.log(4.0), 41))


def fit_temperature(z, y):
    if len(y) < 8 or y.min() == y.max():
        return 1.0
    nll = [-(y * np.log(sig(z / T) + 1e-12) + (1 - y) * np.log(1 - sig(z / T) + 1e-12)).mean() for T in T_GRID]
    return float(T_GRID[int(np.argmin(nll))])


def conformal_q(scores, alpha=ALPHA):
    n = len(scores)
    if n == 0:
        return 1.0
    k = int(np.ceil((n + 1) * (1 - alpha)))
    return 1.0 if k > n else float(np.sort(scores)[k - 1])


def score(z, y):
    p1 = sig(z)
    return np.where(y == 1, 1 - p1, p1)          # 1 - p_hat(y)


def pred_set(z, q):
    p1 = sig(z)
    inc1 = (1 - p1) <= q; inc0 = p1 <= q
    return inc0, inc1


# ------------------------------------------------------------------ features
def features(d, feat_mode):
    R = d["Rcur"] if feat_mode == "current" else d["Rst"]
    X = d["Xcur"] if feat_mode == "current" else d["Xst"]
    h = d["hour"]
    return np.column_stack([d["P"], d["Q"], d["Pzone"], d["Phead"], d["Qhead"], R, X,
                            np.sin(2 * np.pi * h / 24), np.cos(2 * np.pi * h / 24)])


def run(data_path, topo, W_buf, feat_mode, seed):
    d = dict(np.load(data_path))
    rng = np.random.default_rng(1000 + seed)
    Xall = features(d, feat_mode)
    first_day = d["round"] < 24                       # scaler from day 1 (secure-aggregated moments)
    mu, sd = Xall[first_day].mean(0), Xall[first_day].std(0) + 1e-9
    Xall = (Xall - mu) / sd
    yall = d["y"].astype(float)
    rnd, zone = d["round"], d["zone"]
    dim = Xall.shape[1]
    p0 = init_params(rng, dim)
    models = [p0 for _ in range(K)]
    Wmix = None if topo in ("star", "local") else metropolis(TOPOLOGIES[topo])
    train_buf = [[] for _ in range(K)]; cal_buf = [[] for _ in range(K)]   # lists of index arrays per round
    T_static = np.ones(K)
    q_static_local = np.ones(K); q_static_pooled = 1.0
    out = {k: [] for k in ["idx", "z", "z_ft", "p_ts_slide", "p_ts_static",
                           "cov_ps", "size_ps", "cov_ls", "size_ls", "cov_lw", "size_lw", "cov_pw", "size_pw"]}
    idx_by_rz = {}
    for r in range(N_ROUNDS):
        for k in range(K):
            idx_by_rz[(r, k)] = np.where((rnd == r) & (zone == k))[0]
    for r in range(N_ROUNDS):
        # ---------------- static calibration frozen at end of STATIC_CAL window
        if r == STATIC_CAL[1]:
            pooled = []
            for k in range(K):
                ci = np.concatenate([c for rr, c in cal_buf[k] if STATIC_CAL[0] <= rr < STATIC_CAL[1]])
                zc = logits(models[k], Xall[ci]); yc = yall[ci]
                T_static[k] = fit_temperature(zc, yc)
                s = score(zc, yc); q_static_local[k] = conformal_q(s); pooled.append(s)
            q_static_pooled = conformal_q(np.concatenate(pooled))
        # ---------------- sliding-window pooled conformal quantile (all clients' recent held-out data)
        win_scores = []
        win_cal = {}
        for k in range(K):
            ci = [c for rr, c in cal_buf[k] if rr >= r - CAL_WIN]
            ci = np.concatenate(ci) if ci else np.array([], int)
            win_cal[k] = ci
            if len(ci):
                win_scores.append(score(logits(models[k], Xall[ci]), yall[ci]))
        q_pw = conformal_q(np.concatenate(win_scores)) if win_scores else 1.0
        # ---------------- test (prequential) then store
        for k in range(K):
            idx = idx_by_rz[(r, k)]
            z = logits(models[k], Xall[idx])
            ci = win_cal[k]
            zc = logits(models[k], Xall[ci]) if len(ci) else np.array([])
            T_sl = fit_temperature(zc, yall[ci]) if len(ci) else 1.0
            q_lw = conformal_q(score(zc, yall[ci])) if len(ci) else 1.0
            # static-local q is re-scored with the current model on the frozen calibration rounds
            if r >= STATIC_CAL[1]:
                cs = np.concatenate([c for rr, c in cal_buf[k] if STATIC_CAL[0] <= rr < STATIC_CAL[1]])
                q_ls = conformal_q(score(logits(models[k], Xall[cs]), yall[cs]))
            else:
                q_ls = 1.0
            y = yall[idx]
            out["idx"].append(idx); out["z"].append(z)
            out["p_ts_slide"].append(sig(z / T_sl)); out["p_ts_static"].append(sig(z / T_static[k]))
            for tag, q in (("ps", q_static_pooled), ("ls", q_ls), ("lw", q_lw), ("pw", q_pw)):
                i0, i1 = pred_set(z, q)
                out["cov_" + tag].append(np.where(y == 1, i1, i0).astype(np.int8))
                out["size_" + tag].append((i0.astype(int) + i1.astype(int)).astype(np.int8))
            if topo == "star":
                tb = [c for rr, c in train_buf[k] if rr >= r - W_buf]
                if tb:
                    tb = np.concatenate(tb)
                    ft = sgd_steps(models[k], Xall[tb], yall[tb], rng, steps=E_LOCAL)
                    out["z_ft"].append(logits(ft, Xall[idx]))
                else:
                    out["z_ft"].append(z)
            else:
                out["z_ft"].append(z)
            perm = rng.permutation(len(idx)); ncal = len(idx) // 4
            cal_buf[k].append((r, idx[perm[:ncal]])); train_buf[k].append((r, idx[perm[ncal:]]))
            train_buf[k] = [(rr, c) for rr, c in train_buf[k] if rr > r - W_buf]
            cal_buf[k] = [(rr, c) for rr, c in cal_buf[k] if rr > r - CAL_WIN or STATIC_CAL[0] <= rr < STATIC_CAL[1]]
        # ---------------- local training
        new = []; sizes = []
        for k in range(K):
            tb = np.concatenate([c for _, c in train_buf[k]])
            new.append(sgd_steps(models[k], Xall[tb], yall[tb], rng)); sizes.append(len(tb))
        # ---------------- communication
        if topo == "star":
            w = np.array(sizes, float) / sum(sizes)
            g = sum(wk * flat(m) for wk, m in zip(w, new))
            models = [unflat(g.copy(), dim) for _ in range(K)]
        elif topo == "local":
            models = new
        else:
            F = np.stack([flat(m) for m in new])
            F = Wmix @ F
            models = [unflat(F[k].copy(), dim) for k in range(K)]
    res = {k: np.concatenate(v) for k, v in out.items()}
    return res


if __name__ == "__main__":
    data_path, topo, W_buf, feat_mode, seed, out_path = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4], int(sys.argv[5]), sys.argv[6]
    res = run(data_path, topo, W_buf, feat_mode, seed)
    np.savez_compressed(out_path, **res)
    print("ok", out_path)
