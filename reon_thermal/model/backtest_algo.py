import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backtest as b
p = os.path.join(b.R, "backtest.json"); out = json.load(open(p))
out["algo"] = b.run_strategy("algo")
json.dump(out, open(p, "w"), indent=1, default=str)
for s in ("none", "hottest", "algo", "oracle"):
    r = out[s]
    print(f"{s:8s} E {r['energy_MWh_year']:.2f} MWh/yr  loss {r['loss_kWh_year']:.0f} kWh  eff {r['efficiency_pct']:.2f}%  Tmax {r['Tmax_year']:.1f}  "
          f"risk {r['safety_risk_cell_days']:.0f}  healthy-bypass {r['healthy_cell_bypass_weeks']}  SOHmin {r['soh_min']:.3f}  usable {r['usable_cell_control']:.3f}  detect {r['detection_delay_weeks']}")
c = out["algo"]["confusion"]; tot = sum(c.values()); ok = sum(v for k, v in c.items() if k.split("->")[0] == k.split("->")[1])
print("algo label accuracy %.1f%% over %d cell-weeks" % (100 * ok / tot, tot))
print({k: v for k, v in c.items() if k.split("->")[0] != k.split("->")[1] and v > 20})
