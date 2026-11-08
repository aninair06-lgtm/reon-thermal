import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backtest as b
rng = np.random.default_rng(7); cab = b.Cabinet(seed=1); dia = b.Diagnoser(cab.R0o.copy(), cab.R0p.copy())
byp = np.zeros((8, 16), bool); log = []
watch = ["M03_C05", "M05_C12", "M02_C09", "M06_C03", "M07_C08", "M01_C01", "M04_C08"]
for week in range(30):
    cab.inject(week, ~(byp | cab.retired))
    if week == b.COLD_CHARGE_WEEK: log.append((week, dict(T_min=2.0, C_rate=1.0)))
    d = b.discharge(cab, b.ambient(week), byp, True)
    meas = b.measure(cab, d, rng)
    lab, raw, cor = dia.classify(week, meas, log)
    byp, ret = b.policy(lab, cor, b.ambient(week + 1))
    for mc in ret: cab.retired[mc] = True
    cnt = {k: int((lab == k).sum()) for k in ("healthy", "temp_effect", "cooling", "plating", "damage", "tab", "corrosion", "sei", "ambiguous")}
    Tp = np.median(meas["T_end"]); dTe = b.B_LOCAL * (meas["q_last"] - np.median(meas["q_last"]))
    resid = meas["T_end"] - Tp - dTe
    print(f"wk{week:2d} Ta {b.ambient(week):4.1f} " + " ".join(f"{w[1:3]}{w[5:7]}:{lab[b.ix(w)][:5]}({raw[b.ix(w)]:+.2f}/{cor[b.ix(w)]:+.2f})" for w in watch) +
          f" | {cnt} | resid max {resid.max():.1f} at {b.IDS[int(resid.argmax())]}")
