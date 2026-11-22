"""
Analysis of the 120 benchmark runs. Writes CSV tables and figure data to results/.
Zone groups (fixed by the physics of the feeder, see gen_data.py):
  PV zones          Z6, Z7  : rooftop PV installed at round 150
  relieved zones    Z1-Z3   : no PV, but upstream trunk relieved -> midday alarms disappear
  never-alarm zones Z0,Z4,Z5: no alarm at any time (pure negative clients)
"""
import glob, os, re, numpy as np, csv
from collections import defaultdict

DATA = {s: dict(np.load(f"data/seed{s}.npz")) for s in range(5)}
GROUPS = {"PV": [6, 7], "relieved": [1, 2, 3], "drifted": [1, 2, 3, 6, 7], "never": [0, 4, 5], "all": list(range(8))}
PHASES = {"pre": (125, 150), "pv_0_12": (150, 162), "pv_12_24": (162, 174), "pv_steady": (200, 225),
          "rec_0_12": (225, 237), "rec_steady": (275, 300)}
ALPHA = 0.10
os.makedirs("results", exist_ok=True)


def sig(z):
    return 1 / (1 + np.exp(-np.clip(z, -30, 30)))


def ece(p, y, nb=10):
    """Top-label ECE, Eq. (7): bins of confidence max(p,1-p) on [0.5,1]."""
    if len(y) == 0:
        return np.nan
    conf = np.maximum(p, 1 - p); acc = ((p > 0.5) == (y == 1)).astype(float)
    b = np.minimum(((conf - 0.5) / (0.5 / nb)).astype(int), nb - 1)
    return float(sum(abs(acc[b == k].mean() - conf[b == k].mean()) * (b == k).mean() for k in range(nb) if (b == k).any()))


def load_run(path):
    m = re.match(r"runs/(\w+)_W(\d+)_(\w+)_s(\d)\.npz", path)
    topo, W, feat, s = m.group(1), int(m.group(2)), m.group(3), int(m.group(4))
    r = dict(np.load(path)); d = DATA[s]; idx = r["idx"]
    rec = {"y": d["y"][idx].astype(int), "rnd": d["round"][idx], "zone": d["zone"][idx], "bus": d["bus"][idx],
           "t": d["t"][idx], "V": d["V"][idx], "z": r["z"], "z_ft": r["z_ft"],
           "p_sl": r["p_ts_slide"], "p_st": r["p_ts_static"]}
    for k in ("ps", "ls", "lw", "pw"):
        rec["cov_" + k] = r["cov_" + k]; rec["size_" + k] = r["size_" + k]
    return (topo, W, feat, s), rec, d["parents"]


def ovr(rec, parents, mask_rounds, cross_only=False, zones_of_bus=None):
    """Ordering-violation rate: share of (line, time) pairs with |V_p - V_c| > 1e-3 p.u. where the
    model's implied ordering (higher alarm logit = lower voltage) disagrees with the true ordering."""
    sel = mask_rounds
    t = rec["t"][sel]; b = rec["bus"][sel]; z = rec["z"][sel]; V = rec["V"][sel]; rnd = rec["rnd"][sel]
    T0 = t.min(); nt = t.max() - T0 + 1
    Z = np.full((nt, 33), np.nan); VV = np.full((nt, 33), np.nan); R = np.zeros(nt, int)
    Z[t - T0, b] = z; VV[t - T0, b] = V; R[t - T0] = rnd
    viol = tot = 0
    for ti in range(nt):
        par = parents[R[ti]]
        for c in range(1, 33):
            p = par[c]
            if p <= 0 or np.isnan(Z[ti, c]) or np.isnan(Z[ti, p]):
                continue
            if cross_only and zones_of_bus[p] == zones_of_bus[c]:
                continue
            dv = VV[ti, p] - VV[ti, c]
            if abs(dv) <= 1e-3:
                continue
            tot += 1
            viol += int(np.sign(Z[ti, c] - Z[ti, p]) != np.sign(dv))
    return viol / tot if tot else np.nan


ZONES = [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12], [13, 14, 15, 16, 17],
         [18, 19, 20, 21], [22, 23, 24], [25, 26, 27, 28], [29, 30, 31, 32]]
ZOB = np.zeros(33, int)
for k, bs in enumerate(ZONES):
    ZOB[bs] = k

rows = []                       # long table: config, seed, phase, group, metric, value
per_client = []                 # config, seed, phase, zone, metric, value
series = defaultdict(list)      # (config, metric) -> list of per-seed per-round arrays
recovery = []
for path in sorted(glob.glob("runs/*_s?.npz")):
    (topo, W, feat, s), rec, parents = load_run(path)
    cfg = f"{topo}|W{W}|{feat}"
    p = sig(rec["z"]); pft = sig(rec["z_ft"])
    for ph, (a, b) in PHASES.items():
        inph = (rec["rnd"] >= a) & (rec["rnd"] < b)
        for g, zs in GROUPS.items():
            m = inph & np.isin(rec["zone"], zs)
            y = rec["y"][m]
            vals = {"err": float(((p[m] > 0.5) != (y == 1)).mean()),
                    "ece": ece(p[m], y), "ece_ts_sliding": ece(rec["p_sl"][m], y), "ece_ts_static": ece(rec["p_st"][m], y),
                    "brier": float(((p[m] - y) ** 2).mean()),
                    "err_ft": float(((pft[m] > 0.5) != (y == 1)).mean()), "ece_ft": ece(pft[m], y)}
            for k in ("ps", "ls", "lw", "pw"):
                vals["cov_" + k] = float(rec["cov_" + k][m].mean()); vals["size_" + k] = float(rec["size_" + k][m].mean())
            for mk, v in vals.items():
                rows.append((cfg, s, ph, g, mk, v))
        for zk in range(8):
            m = inph & (rec["zone"] == zk); y = rec["y"][m]
            pc = {"ece": ece(p[m], y), "ece_ft": ece(pft[m], y), "ece_ts_sliding": ece(rec["p_sl"][m], y),
                  "err": float(((p[m] > 0.5) != (y == 1)).mean())}
            for k in ("ps", "ls", "lw", "pw"):
                pc["cov_" + k] = float(rec["cov_" + k][m].mean())
            for mk, v in pc.items():
                per_client.append((cfg, s, ph, zk, mk, v))
        if feat == "current" and ph in ("pre", "pv_0_12", "pv_steady", "rec_0_12", "rec_steady"):
            rows.append((cfg, s, ph, "all", "ovr", ovr(rec, parents, inph)))
            rows.append((cfg, s, ph, "all", "ovr_cross", ovr(rec, parents, inph, True, ZOB)))
    # per-round series on drifted zones (rolling 4 rounds) for figures and recovery times
    dz = np.isin(rec["zone"], GROUPS["drifted"])
    er, ec, cv_ps, cv_lw, cv_pw = [], [], [], [], []
    for r in range(100, 300):
        m = dz & (rec["rnd"] > r - 4) & (rec["rnd"] <= r)
        y = rec["y"][m]
        er.append(((p[m] > 0.5) != (y == 1)).mean()); ec.append(ece(p[m], y))
        cv_ps.append(rec["cov_ps"][m].mean()); cv_lw.append(rec["cov_lw"][m].mean()); cv_pw.append(rec["cov_pw"][m].mean())
    for mk, arr in (("err", er), ("ece", ec), ("cov_ps", cv_ps), ("cov_lw", cv_lw), ("cov_pw", cv_pw)):
        series[(cfg, mk)].append(np.array(arr))
    # recovery time: rounds after onset until the rolling metric has shed 75% of its excess over the pre-drift level
    for mk, arr in (("err", np.array(er)), ("ece", np.array(ec)), ("covgap_lw", np.abs(np.array(cv_lw) - 0.9)),
                    ("covgap_ps", np.abs(np.array(cv_ps) - 0.9))):
        pre = np.nanmean(arr[25:50])                 # rounds 125-149
        post = arr[50:]                              # rounds 150-299
        peak_i = int(np.nanargmax(post[:12])); peak = post[peak_i]
        thr = pre + 0.25 * (peak - pre)
        rt = next((i for i in range(peak_i, 75) if np.all(post[i:i + 3] <= thr)), np.nan)
        recovery.append((cfg, s, mk, pre, peak, rt))

with open("results/long_metrics.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["config", "seed", "phase", "group", "metric", "value"]); w.writerows(rows)
with open("results/per_client_metrics.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["config", "seed", "phase", "zone", "metric", "value"]); w.writerows(per_client)
with open("results/recovery.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["config", "seed", "metric", "pre", "peak", "recovery_rounds"]); w.writerows(recovery)
np.savez_compressed("results/series.npz", **{f"{c}::{m}": np.stack(v) for (c, m), v in series.items()})
print("rows", len(rows), "per_client", len(per_client), "recovery", len(recovery))
