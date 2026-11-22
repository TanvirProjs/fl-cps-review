"""
Data generation for the reference benchmark (Section 11 of the revised manuscript).

IEEE 33-bus radial distribution feeder (Baran & Wu 1989, pandapower case33bw), solved with
AC power flow at 15-min resolution. Timeline (one FL round = 4 time steps = 1 h):
  rounds   0-149 : nominal operation
  rounds 150-299 : unmetered rooftop PV on the lateral buses 25-32 (zones Z6, Z7)  -> concept drift
  rounds 225-299 : network reconfiguration: tie 17-32 closed, line 31-32 opened   -> change of G_p
Each sample is (bus i, time t). Label y = 1[V_i(t) < 0.95 p.u.] (under-voltage alarm).
Features (as measured by the zone's edge device + feeder-head broadcast):
  P_i, Q_i      gross bus demand from smart meters (PV is behind the meter and NOT metered)
  P_zone        zone gross demand
  P_head, Q_head substation active/reactive power (net of PV, measured at the feeder head)
  R_path, X_path path impedance from substation to bus i (from the digital twin's copy of G_p)
  sin/cos(hour)
R_path/X_path are stored twice: from the nominal G_p ("stale") and from the current G_p ("current").
"""
import sys, json, numpy as np, warnings
warnings.filterwarnings("ignore")
import pandapower as pp, pandapower.networks as pn

ZONES = [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12], [13, 14, 15, 16, 17],
         [18, 19, 20, 21], [22, 23, 24], [25, 26, 27, 28], [29, 30, 31, 32]]
PV_BUSES = list(range(25, 33))
STEPS_PER_ROUND, N_ROUNDS = 4, 300
R_DRIFT, R_RECONF = 150, 225
TIE_CLOSE, LINE_OPEN = 35, 31          # pandapower line indices: tie 17-32, line 31-32


def path_impedance(net):
    """R and X (ohm) from bus 0 along the in-service radial tree; parent of each bus."""
    import collections
    adj = collections.defaultdict(list)
    for idx, ln in net.line[net.line.in_service].iterrows():
        r = ln.r_ohm_per_km * ln.length_km; x = ln.x_ohm_per_km * ln.length_km
        adj[ln.from_bus].append((ln.to_bus, r, x)); adj[ln.to_bus].append((ln.from_bus, r, x))
    R = np.zeros(len(net.bus)); X = np.zeros(len(net.bus)); parent = -np.ones(len(net.bus), int)
    seen = {0}; q = [0]
    while q:
        u = q.pop(0)
        for v, r, x in adj[u]:
            if v not in seen:
                seen.add(v); R[v] = R[u] + r; X[v] = X[u] + x; parent[v] = u; q.append(v)
    assert len(seen) == len(net.bus), "network not connected/radial"
    return R, X, parent


def load_shape(h):
    return 0.50 + 0.38 * np.exp(-((h - 13.0) / 3.0) ** 2) + 0.40 * np.exp(-((h - 19.5) / 2.2) ** 2)   # mixed commercial (midday) + residential (evening) feeder


def generate(seed, out):
    rng = np.random.default_rng(seed)
    net = pn.case33bw()
    base_p = net.load.set_index("bus").p_mw.reindex(range(33)).fillna(0).values
    base_q = net.load.set_index("bus").q_mvar.reindex(range(33)).fillna(0).values
    load_idx = net.load.set_index("bus").index.values          # buses with load (1..32)
    for b in PV_BUSES:
        pp.create_sgen(net, b, p_mw=0.0, q_mvar=0.0)
    R_nom, X_nom, par_nom = path_impedance(net)
    zone_scale = np.array([1.0, 1.0, 1.05, 1.1, 0.95, 1.0, 1.05, 1.1])
    bus_scale = np.ones(33)
    for z, buses in enumerate(ZONES):
        bus_scale[buses] = zone_scale[z]
    T = N_ROUNDS * STEPS_PER_ROUND
    noise = np.zeros(33); cloud = 1.0
    day_factor = 1.0 + 0.05 * rng.standard_normal(T // 96 + 2)
    rec = {k: [] for k in ["t", "round", "bus", "zone", "P", "Q", "Pzone", "Phead", "Qhead",
                           "Rst", "Xst", "Rcur", "Xcur", "hour", "V", "y"]}
    lines_log = []                                     # (t, parent, child) for in-service tree
    R_cur, X_cur, par_cur = R_nom, X_nom, par_nom
    for t in range(T):
        r = t // STEPS_PER_ROUND; h = (t % 96) / 4.0
        if r == R_RECONF and t % STEPS_PER_ROUND == 0:
            net.line.loc[TIE_CLOSE, "in_service"] = True; net.line.loc[LINE_OPEN, "in_service"] = False
            R_cur, X_cur, par_cur = path_impedance(net)
        noise = 0.85 * noise + np.sqrt(1 - 0.85 ** 2) * 0.08 * rng.standard_normal(33)
        mult = load_shape(h) * day_factor[t // 96] * bus_scale * np.exp(noise)
        P = base_p * mult; Q = base_q * mult * (1 + 0.03 * rng.standard_normal(33))
        net.load["p_mw"] = P[net.load.bus.values]; net.load["q_mvar"] = Q[net.load.bus.values]
        cloud = float(np.clip(0.8 * cloud + 0.2 * rng.uniform(0.3, 1.0), 0.2, 1.0))
        irr = max(0.0, np.sin(np.pi * (h - 6.0) / 12.0)) if 6.0 < h < 18.0 else 0.0
        pv = 0.40 * irr * cloud if r >= R_DRIFT else 0.0
        net.sgen["p_mw"] = pv
        pp.runpp(net, numba=False)
        V = net.res_bus.vm_pu.values
        Ph = float(net.res_ext_grid.p_mw.iloc[0]); Qh = float(net.res_ext_grid.q_mvar.iloc[0])
        for z, buses in enumerate(ZONES):
            Pz = P[buses].sum()
            for b in buses:
                for k, v in [("t", t), ("round", r), ("bus", b), ("zone", z), ("P", P[b]), ("Q", Q[b]),
                             ("Pzone", Pz), ("Phead", Ph), ("Qhead", Qh), ("Rst", R_nom[b]), ("Xst", X_nom[b]),
                             ("Rcur", R_cur[b]), ("Xcur", X_cur[b]), ("hour", h), ("V", V[b]),
                             ("y", int(V[b] < 0.95))]:
                    rec[k].append(v)
        if t % STEPS_PER_ROUND == 0:
            lines_log.append((r, par_cur.tolist()))
    arr = {k: np.array(v) for k, v in rec.items()}
    parents = np.array([p for _, p in lines_log])        # (rounds, 33) parent per bus
    np.savez_compressed(out, parents=parents, **arr)
    return arr


if __name__ == "__main__":
    seed = int(sys.argv[1]); out = sys.argv[2]
    a = generate(seed, out)
    y = a["y"]; r = a["round"]; z = a["zone"]
    print(f"seed {seed}: samples {len(y)}, alarm rate {y.mean():.3f}, "
          f"pre {y[r < 150].mean():.3f}, post-PV {y[(r >= 150) & (r < 225)].mean():.3f}, post-reconf {y[r >= 225].mean():.3f}")
    print("alarm rate by zone pre/postPV/postreconf:",
          [(round(y[(z == k) & (r < 150)].mean(), 2), round(y[(z == k) & (r >= 150) & (r < 225)].mean(), 2),
            round(y[(z == k) & (r >= 225)].mean(), 2)) for k in range(8)])
    print("V min/max", a["V"].min().round(3), a["V"].max().round(3))
