"""Refresh the Stage 4 per-year table in extras.json from the current stage4.json and econ.json (no reruns)."""
import json, os
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
ex = json.load(open(os.path.join(R, "extras.json"))); s4 = json.load(open(os.path.join(R, "stage4.json"))); E = json.load(open(os.path.join(R, "econ.json")))
H = ex["stage4_per_year"]["hot_days"]
ex["stage4_per_year"] = dict(hot_days=H, ac_year_round_kWh=E["hvac_alternative"]["electricity_kwh"], ac_cop_mean=E["hvac_alternative"]["cop"],
                             ideas={r["idea"]: dict(peak_C=r["peak_C"], below_60=r["below_60"], kWh_per_year=r["extra_kWh_per_day"] * H) for r in s4["ideas"]})
json.dump(ex, open(os.path.join(R, "extras.json"), "w"), indent=1)
print("AC year-round", round(ex["stage4_per_year"]["ac_year_round_kWh"]), "kWh; per-year ideas", {k: round(v["kWh_per_year"]) for k, v in ex["stage4_per_year"]["ideas"].items() if v["kWh_per_year"] > 0})
