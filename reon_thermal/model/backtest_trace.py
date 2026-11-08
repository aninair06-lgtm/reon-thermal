"""Per-cell weekly traces for the dashboard: the algorithm watches a cabinet that does NOT bypass (faults develop
naturally), so we can see when each fault is (1) flagged by the algorithm, (2) visible as heat (cell > pack + 2 K at the
end of discharge), (3) visible as degradation (SOH 3 % below the pack median). Also cabinet snapshots."""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backtest as b
rng = np.random.default_rng(7); cab = b.Cabinet(seed=1); dia = b.Diagnoser(cab.R0o.copy(), cab.R0p.copy())
LABS = ["healthy", "temp_effect", "cooling", "plating", "damage", "tab", "corrosion", "sei", "ambiguous"]
log = []; nob = np.zeros((8, 16), bool)
tr = {cid: dict(kind=f["kind"], inj=f["week"], weeks=[], cor=[], raw=[], dT=[], soh_dev=[], label=[]) for cid, f in b.FAULTS.items()}
pack = dict(weeks=[], T_amb=[], Tmax=[], Tmed=[], soh_med=[], cor_med=[], E=[], fields=[])
for week in range(b.WEEKS):
    cab.inject(week, ~nob)
    if week == b.COLD_CHARGE_WEEK: log.append((week, dict(T_min=2.0, C_rate=1.0)))
    d = b.discharge(cab, b.ambient(week), nob, True)
    meas = b.measure(cab, d, rng)
    lab, raw, cor = dia.classify(week, meas, log)
    Tp = np.median(meas["T_end"]); soh = cab.cap / cab.cap0; sm = np.median(soh)
    for cid, t in tr.items():
        m, c = b.ix(cid)
        t["weeks"].append(week); t["cor"].append(round(float(cor[m, c]), 4)); t["raw"].append(round(float(raw[m, c]), 4))
        t["dT"].append(round(float(meas["T_end"][m, c] - Tp), 3)); t["soh_dev"].append(round(float(soh[m, c] - sm), 4)); t["label"].append(str(lab[m, c]))
    pack["weeks"].append(week); pack["T_amb"].append(round(b.ambient(week), 2)); pack["Tmax"].append(round(float(d["Tmax"].max()), 2))
    pack["Tmed"].append(round(float(Tp), 2)); pack["soh_med"].append(round(float(sm), 4)); pack["cor_med"].append(round(float(np.median(cor)), 4)); pack["E"].append(round(d["E_kWh"], 2))
    byp, _ = b.policy(lab, cor, b.ambient(week))
    pack["fields"].append(dict(week=week, dT=np.round(meas["T_end"] - Tp, 2).ravel().tolist(), soh=np.round(soh, 4).ravel().tolist(),
                               lab=[LABS.index(str(x)) for x in lab.ravel()], cor=np.round(cor, 3).ravel().tolist(),
                               byp=[int(i) for i in np.flatnonzero(byp.ravel())]))
    cab.age(d["T_mean"], np.ones((8, 16)))
for cid, t in tr.items():
    w = np.array(t["weeks"]); inj = t["inj"]
    flag = next((int(x) for x, l in zip(w, t["label"]) if x >= inj and l == t["kind"]), None)
    thermal = next((int(x) for x, dT in zip(w, t["dT"]) if x >= inj and dT > 2.0), None)
    degr = next((int(x) for x, s in zip(w, t["soh_dev"]) if x >= inj and s < -0.03), None)
    t.update(flag=flag, thermal=thermal, degraded=degr)
    print(f"{cid} {t['kind']:9s} injected wk{inj:2d}  flagged {flag}  heat-visible {thermal}  degraded {degr}  final dT {t['dT'][-1]:+.2f} K  cor {t['cor'][-1]:+.2f}  soh_dev {t['soh_dev'][-1]:+.3f}")
json.dump(dict(cells=tr, pack=pack, labels=LABS, ids=list(b.IDS)), open(os.path.join(b.R, "backtest_trace.json"), "w"))
