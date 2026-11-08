"""Second left-out check: 3D case B (sealed, 25 C ambient, 2 h) vs the network calibrated on case C (40 C) only."""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_cases import run_case
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
b = json.load(open(os.path.join(R, "openfoam", "Bt_lam_m1_cells.json")))
t3 = np.array(b["t_s"]); Tm3 = np.array(b["T_mean"]); Tx3 = np.array(b["T_max"])
# network, radiation off to compare like with like (the 3D model has none), and with radiation (production)
out = dict(t_end=float(t3[-1]), peak_3D=float(Tx3.max()), mean_end_3D=float(Tm3[-1].mean()), spread_end_3D=float(Tm3[-1].max() - Tm3[-1].min()))
for tag, extra in (("network_no_radiation", dict(eps=0.0, eps_wall=0.0)), ("network_with_radiation", {})):
    r = run_case("B", "passive", 25.0, 5.0, extra=extra)
    h = np.array(r["history"])
    out[tag] = dict(peak=r["peak_interior_C"], mean_end=r["mean_end_C"], spread_end=r["spread_end_K"],
                    peak_err_vs_3D=r["peak_interior_C"] - out["peak_3D"], mean_err_vs_3D=r["mean_end_C"] - out["mean_end_3D"])
json.dump(out, open(os.path.join(R, "B_leftout_check.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
