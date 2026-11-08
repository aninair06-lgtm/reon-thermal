"""Weekly cabinet health for the dashboard gauge: weakest-cell and average SOH at the end of every week, for the
REON policy ("algo") and for no bypass ("none"). Re-runs backtest.run_strategy unchanged and records the state after
each week's ageing step, so week 52 equals the soh_min / soh_mean already in backtest.json."""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backtest as b

rec = []
_age = b.Cabinet.age
def age(self, *a, **k):
    out = _age(self, *a, **k)
    soh = self.cap / self.cap0; live = soh[~self.retired]   # retirements are set before this week's ageing step
    rec.append((float(soh.min()), float(soh.mean()), int(self.retired.sum()), float(live.min()), float(live.mean())))
    return out
b.Cabinet.age = age

ref = json.load(open(os.path.join(b.R, "backtest.json")))
out = {}
for name in ("none", "algo"):
    rec.clear()
    r = b.run_strategy(name)
    assert len(rec) == b.WEEKS, (name, len(rec))
    assert abs(r["soh_min"] - ref[name]["soh_min"]) < 1e-9 and abs(r["soh_mean"] - ref[name]["soh_mean"]) < 1e-9, \
        (name, r["soh_min"], ref[name]["soh_min"])
    out[name] = dict(soh_min=[round(x[0], 5) for x in rec], soh_mean=[round(x[1], 5) for x in rec], retired=[x[2] for x in rec],
                     live_min=[round(x[3], 5) for x in rec], live_mean=[round(x[4], 5) for x in rec])
    print(name, "weakest", [round(100 * x[0], 1) for x in rec])
    print(name, "weakest in service", [round(100 * x[3], 1) for x in rec])
json.dump(out, open(os.path.join(b.R, "backtest_health.json"), "w"))
print("wrote backtest_health.json; end-of-year values match backtest.json")
