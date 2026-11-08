"""GPU studies on the calibrated network (CuPy, batch = scenarios):
 1. Shapley attribution: which heat inducer causes how many kelvin at the hottest cell (all 2^8 on/off combinations)
 2. Sobol sensitivity (SALib, Saltelli) of the peak interior temperature, hot-start passive case
 3. Bypass-set study: hotspot-selected vs random sets of 1/4/8/13 cells vs equal derating, aged cell present
"""
import sys, os, json, time, itertools, math
sys.path.insert(0, "/mnt/c/Users/anina/Downloads/MITEC/reon_thermal/model")
import numpy as np
from network import Network
import params as P
from run_cases import CAL
RES = "/mnt/c/Users/anina/Downloads/MITEC/reon_thermal/results"
TGT = (6, 7)   # M07_C08: hottest cell in the passive baseline and the aged-cell slot

from solar import roof, west as side   # pvlib clear sky, Phoenix 21 June, discharge 14:00-16:00

def run_batch(net, q, tend=7200.0, dt=10.0):
    xp = net.xp
    net.q_presc = xp.asarray(q)
    peak = xp.full(net.B, -1e9); peak_tgt = xp.full(net.B, -1e9)
    while net.t < tend - 1e-9:
        net.step(dt, record=True)
        Ti = net.rec["Tmax"]
        peak = xp.maximum(peak, Ti.max((1, 2))); peak_tgt = xp.maximum(peak_tgt, Ti[:, TGT[0], TGT[1]])
    return xp.asnumpy(peak), xp.asnumpy(peak_tgt), xp.asnumpy(net.rec["Tmax"])

def shapley():
    names = ["own Joule heat (6.1 W)", "other 127 cells' heat", "ageing (+12.2 W, 3x R)", "busbar + switch losses",
             "hot site (40 C vs 25 C)", "hot start (55 C)", "inverter inside (750 W)", "sun on roof/side"]
    combos = np.array(list(itertools.product([0, 1], repeat=8)), bool)
    B = len(combos)
    q = np.zeros((B, 8, 16))
    loss = P.I_RATED ** 2 * P.R_CONN + P.I_RATED ** 2 * 0.0   # 0.57 W per cell joint (series switch assumed inside 6.1 W)
    for b, c in enumerate(combos):
        if c[1]: q[b] += P.Q_NORMAL; q[b, TGT[0], TGT[1]] -= P.Q_NORMAL
        if c[0]: q[b, TGT[0], TGT[1]] += P.Q_NORMAL
        if c[2]: q[b, TGT[0], TGT[1]] += P.Q_AGED - P.Q_NORMAL
        if c[3]: q[b] += loss
    Tamb = np.where(combos[:, 4], 40.0, 25.0)
    Tinit = np.where(combos[:, 5], 55.0, Tamb)
    kw = dict(CAL.get("passive", {}))
    net = Network(B=B, gpu=True, mode="passive", T_amb=Tamb, T_init=Tinit, h_ext=5.0,
                  Q_inverter=np.where(combos[:, 6], 750.0, 0.0), solar_roof=roof, solar_side=side,
                  solar_mult=combos[:, 7].astype(float), **kw)
    peak, ptgt, _ = run_batch(net, q)
    v = ptgt - 25.0
    idx = {tuple(c): i for i, c in enumerate(combos)}
    n = 8; phi = np.zeros(n)
    for i in range(n):
        for c in combos:
            if c[i]: continue
            s = c.sum(); w = math.factorial(s) * math.factorial(n - s - 1) / math.factorial(n)
            c2 = c.copy(); c2[i] = True
            phi[i] += w * (v[idx[tuple(c2)]] - v[idx[tuple(c)]])
    full = v[idx[tuple([True] * 8)]]
    out = dict(names=names, shapley_K=phi.tolist(), total_rise_K=float(full), sum_check=float(phi.sum()),
               baseline_C=25.0, cell=P.cell_id(TGT[0] + 1, TGT[1] + 1), metric="peak interior T of M07_C08 over 0-7200 s minus 25 C",
               all_on_peak_C=float(ptgt[-1]))
    # also the realistic 'normal day at a hot site' subset: own+pack+losses+site
    print("Shapley (K):", {nm: round(p, 2) for nm, p in zip(names, phi)}, "sum", round(phi.sum(), 2), "full", round(full, 2))
    return out

def sobol(N=512):
    from SALib.sample import saltelli
    from SALib.analyze import sobol as sob
    prob = dict(num_vars=11, names=["k_through", "heat_scale", "r_contact", "h_ext", "emissivity", "T_init_offset",
                                    "Q_circ", "G_ex", "h_mult", "G_support", "cell_R_spread"],
                bounds=[[0.5, 3.0], [0.85, 1.25], [0.0005, 0.003], [5, 10], [0.2, 0.9], [0.0, 15.0],
                        [0.01, 0.3], [0.3, 10.0], [0.5, 3.0], [0.0, 1.0], [0.0, 0.25]])
    X = saltelli.sample(prob, N, calc_second_order=False)
    B = len(X)
    rng = np.random.default_rng(1)
    z = rng.standard_normal((8, 16))
    out_peak = np.zeros(B); out_spread = np.zeros(B)
    chunk = 6144
    for s in range(0, B, chunk):
        x = X[s:s + chunk]; b = len(x)
        q = P.Q_NORMAL * x[:, 1][:, None, None] * np.exp(x[:, 10][:, None, None] * z[None])   # resistance spread -> heat spread
        net = Network(B=b, gpu=True, mode="passive", T_amb=40.0, T_init=40.0 + x[:, 5], kx=x[:, 0], r_contact=x[:, 2],
                      h_ext=x[:, 3], eps=x[:, 4], eps_wall=x[:, 4], Q_circ=x[:, 6], G_ex=x[:, 7], h_mult=x[:, 8], G_sup=x[:, 9])
        pk, _, Tend = run_batch(net, q)
        out_peak[s:s + b] = pk; out_spread[s:s + b] = Tend.max((1, 2)) - Tend.min((1, 2))
    Sp = sob.analyze(prob, out_peak, calc_second_order=False, print_to_console=False)
    Ss = sob.analyze(prob, out_spread, calc_second_order=False, print_to_console=False)
    res = dict(names=prob["names"], bounds=prob["bounds"], n_runs=int(B),
               peak=dict(S1=Sp["S1"].tolist(), ST=Sp["ST"].tolist(), ST_conf=Sp["ST_conf"].tolist(),
                         p05=float(np.percentile(out_peak, 5)), p50=float(np.percentile(out_peak, 50)), p95=float(np.percentile(out_peak, 95)),
                         min=float(out_peak.min()), max=float(out_peak.max()), frac_above_60=float((out_peak > 60).mean())),
               spread=dict(S1=Ss["S1"].tolist(), ST=Ss["ST"].tolist(), p50=float(np.median(out_spread)), p95=float(np.percentile(out_spread, 95))),
               note="ranges, not probabilities: inputs sampled uniformly within stated bounds (no justified distributions)")
    order = np.argsort(Sp["ST"])[::-1]
    print("Sobol ST (peak):", [(prob["names"][i], round(Sp["ST"][i], 3)) for i in order])
    print("peak range p05/p50/p95:", res["peak"]["p05"], res["peak"]["p50"], res["peak"]["p95"], "share>60:", res["peak"]["frac_above_60"])
    return res

def bypass_sets(n_random=256):
    """Aged cell at M07_C08, hot start 55 C @ 40 C ambient. Compare strategies at CONSTANT CURRENT (energy-feasible) and constant power."""
    base_q = np.full((8, 16), P.Q_NORMAL); base_q[TGT] = P.Q_AGED
    kw = dict(CAL.get("passive", {}))
    # rank cells by baseline peak (hotspot-selected)
    net = Network(B=1, gpu=True, mode="passive", T_amb=40.0, T_init=55.0, h_ext=5.0, **kw)
    _, _, Tend = run_batch(net, base_q[None])
    order = np.argsort(Tend[0].ravel())[::-1]
    rows = []
    qs = []; labels = []
    rng = np.random.default_rng(7)
    for k in (0, 1, 4, 8, 13):
        for elec in ("current", "power"):
            sel = order[:k]
            m = np.zeros(128, bool); m[sel] = True; m = m.reshape(8, 16)
            I = 1.0 if elec == "current" else 128.0 / (128 - k)
            q = np.where(m, 0.0, base_q * I ** 2); qs.append(q); labels.append(("hotspot", k, elec, 0))
            for r in range(n_random if k > 0 else 0):
                sel = rng.choice(128, k, replace=False)
                m = np.zeros(128, bool); m[sel] = True; m = m.reshape(8, 16)
                qs.append(np.where(m, 0.0, base_q * I ** 2)); labels.append(("random", k, elec, r))
    for frac in (1.0, 127 / 128, 124 / 128, 120 / 128, 115 / 128, 0.85, 0.8):
        qs.append(base_q * frac ** 2); labels.append(("derate", round(frac, 4), "derate", 0))
    Q = np.array(qs)
    net = Network(B=len(Q), gpu=True, mode="passive", T_amb=40.0, T_init=55.0, h_ext=5.0, **kw)
    pk, ptgt, _ = run_batch(net, Q)
    for (kind, k, elec, r), p in zip(labels, pk):
        power = (P.P_RATED_W * ((128 - k) / 128 if elec == "current" else 1.0)) if kind != "derate" else P.P_RATED_W * k
        rows.append(dict(kind=kind, k=k, elec=elec, rep=r, peak_C=float(p), power_kW=power / 1e3,
                         energy_feasible=(elec != "power" or k == 0)))
    summ = {}
    for kind in ("hotspot", "random"):
        for k in (1, 4, 8, 13):
            for elec in ("current", "power"):
                v = [x["peak_C"] for x in rows if x["kind"] == kind and x["k"] == k and x["elec"] == elec]
                if v: summ[f"{kind}_{k}_{elec}"] = dict(mean=float(np.mean(v)), min=float(np.min(v)), max=float(np.max(v)), n=len(v))
    summ["none"] = [x for x in rows if x["kind"] == "hotspot" and x["k"] == 0 and x["elec"] == "current"][0]["peak_C"]
    summ["derate"] = {str(x["k"]): x["peak_C"] for x in rows if x["kind"] == "derate"}
    print(json.dumps(summ, indent=0)[:1500])
    return dict(summary=summ, rows=[x for x in rows if x["kind"] != "random"], ranking=[P.cell_id(i // 16 + 1, i % 16 + 1) for i in order[:13]])

if __name__ == "__main__":
    which = sys.argv[1:] or ["shapley", "sobol", "bypass"]
    out = {}
    t0 = time.time()
    if "shapley" in which: out["shapley"] = shapley(); print(f"  t={time.time()-t0:.0f}s")
    if "bypass" in which: out["bypass_sets"] = bypass_sets(); print(f"  t={time.time()-t0:.0f}s")
    if "sobol" in which: out["sobol"] = sobol(); print(f"  t={time.time()-t0:.0f}s")
    prev = {}
    p = f"{RES}/gpu_studies.json"
    if os.path.exists(p): prev = json.load(open(p))
    prev.update(out)
    json.dump(prev, open(p, "w"), indent=1)
