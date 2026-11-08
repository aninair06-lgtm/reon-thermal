"""Collect the simulated results the dashboard shows into one compact JSON, then inline it into index.html.
Inputs: ../results/*.json (backtest, trace, stage4, gpu_studies, OpenFOAM cell maps, econ, hotspot_tax)."""
import json, os
from collections import Counter

H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, "..", "results")
J = lambda f: json.load(open(os.path.join(R, f)))
bt, tr, s4, gs = J("backtest.json"), J("backtest_trace.json"), J("stage4.json"), J("gpu_studies.json")
ofC, ofD, ec, hs = J("openfoam/Ct_lam_m1_cells.json"), J("openfoam/Dt_lam_m1_cells.json"), J("econ.json"), J("hotspot_tax.json")


def acc(conf):
    tot = sum(conf.values()); ok = sum(v for k, v in conf.items() if k.split("->")[0] == k.split("->")[1])
    return round(100 * ok / tot, 1)


strat = {k: dict(E=round(v["energy_MWh_year"], 2), eff=round(v["efficiency_pct"], 2), risk=v["safety_risk_cell_days"],
                 soh=round(100 * v["soh_min"], 1), soh_mean=round(100 * v["soh_mean"], 1), usable=round(100 * v["usable_cell_control"], 1),
                 healthy_byp=v["healthy_cell_bypass_weeks"], acc=acc(v["confusion"]), healthy_retired=len([r for r in v["retired"] if r not in tr["cells"]]),
                 nbyp=[w["n_bypassed"] for w in v["weekly"]]) for k, v in bt.items()}

cells = {}
for cid, t in tr["cells"].items():
    after = [l for w, l in zip(t["weeks"], t["label"]) if w >= t["inj"]]
    cells[cid] = dict(kind=t["kind"], inj=t["inj"], flag=t["flag"], heat=t["thermal"], degr=t["degraded"],
                      cor=t["cor"], dT=t["dT"], soh=t["soh_dev"], label=t["label"], common=Counter(after).most_common(3))

idx = {c: i for i, c in enumerate(tr["ids"])}
for cid, c in cells.items():   # first week REON's policy would bypass this cell
    c["byp"] = next((f["week"] for f in tr["pack"]["fields"] if f["week"] >= c["inj"] and idx[cid] in f["byp"]), None)

p = tr["pack"]
weeks = dict(T_amb=p["T_amb"], Tmax=p["Tmax"], Tmed=p["Tmed"], soh_med=p["soh_med"], E=p["E"])
fields = [dict(dT=f["dT"], soh=f["soh"], lab=f["lab"], cor=f["cor"], byp=f["byp"]) for f in p["fields"]]

ideas = [dict(name=i["idea"], kind=i["kind"], peak=round(i["peak_C"], 1), ok=i["below_60"],
              extra=round(i["extra_kWh_per_day"], 2), E=round(i["energy_kWh"], 1)) for i in s4["ideas"]]
sh = gs["shapley"]
cfd = dict(C=dict(T=[round(x, 2) for x in ofC["T_end_max"]], peak=round(ofC["peak"], 2), spread=round(ofC["spread_end"], 2), byp=ofC["bypassed"]),
           D=dict(T=[round(x, 2) for x in ofD["T_end_max"]], peak=round(ofD["peak"], 2), spread=round(ofD["spread_end"], 2), byp=ofD["bypassed"]))
# life and NPV: this cabinet with its five backtest faults (econ.py cabinet_faults); the fault-free pack is kept for reference
cf = ec["cabinet_faults"]
econ = dict(life_fixed=cf["life_fixed_years"]["p50"], life_ctrl=cf["life_control_years"]["p50"], npv_gain=round(cf["economics"]["npv_gain_usd"]),
            life_fixed_clean=ec["life_fixed_years"]["p50"], life_ctrl_clean=ec["life_control_years"]["p50"],
            ac_kwh=round(ec["hvac_alternative"]["electricity_kwh"]), ac_co2=round(ec["hvac_alternative"]["co2_t"], 2),
            kw_fixed=round(hs["max_power_fixed_string_kW"], 1), kw_ctrl=round(hs["max_power_cell_control_kW"], 1),
            kwh_hot_day=round(hs["recovered_kWh_per_hot_day"], 1))

# weakest-cell and average SOH at the end of each week, REON policy vs no bypass (model/backtest_health.py)
hl = J("backtest_health.json")
# soh_*: all 128 cells, retired ones included; live_*: only cells still in service
health = {k: {s: [round(x, 4) for x in hl[k][s]] for s in ("soh_min", "soh_mean", "live_min", "live_mean")} for k in ("algo", "none")}

D = dict(ids=tr["ids"], labels=tr["labels"], strat=strat, cells=cells, weeks=weeks, fields=fields, ideas=ideas, health=health,
         shap=dict(names=sh["names"], K=[round(x, 2) for x in sh["shapley_K"]], total=round(sh["total_rise_K"], 2), peak=round(sh["all_on_peak_C"], 1), cell=sh["cell"]),
         cfd=cfd, econ=econ)
js = json.dumps(D, separators=(",", ":"))
open(os.path.join(H, "data.json"), "w").write(js)
src = open(os.path.join(H, "page.html"), encoding="utf-8").read() if os.path.exists(os.path.join(H, "page.html")) else None
if src:
    page = src.replace("/*__DATA__*/null", js)
    cut = page.index('<div class="hero">')
    head, body = page[:cut], page[cut:]
    # standalone file: declares UTF-8 so the middle dots, minus signs and degree signs render correctly when opened directly
    html = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            + head + '\n</head>\n<body>\n' + body + '\n</body>\n</html>\n')
    open(os.path.join(H, "index.html"), "w", encoding="utf-8").write(html)
    old = os.path.join(H, "_preview.html")
    if os.path.exists(old): os.remove(old)
print(len(js), "bytes;", {k: (v["flag"], v["byp"], v["heat"], v["degr"], v["common"]) for k, v in cells.items()})
print({k: (v["acc"], v["soh"], v["risk"], v["E"]) for k, v in strat.items()})
