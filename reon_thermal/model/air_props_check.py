"""Sensitivity of the answers to air properties: network constants (22 C) vs CoolProp at the operating temperature."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import params as P
from run_cases import run_case
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
cp = json.load(open(os.path.join(R, "coolprop_pvlib.json")))["air"]
cases = {"A_forced25": dict(mode="forced", T_amb=25.0, h_ext=5.0), "C_passive40": dict(mode="passive", T_amb=40.0, h_ext=5.0),
         "H_hotstart": dict(mode="passive", T_amb=40.0, h_ext=5.0, T_init=55.0)}
air_T = {"A_forced25": "25", "C_passive40": "50", "H_hotstart": "60"}
base = {k: run_case(k, **v)["peak_interior_C"] for k, v in cases.items()}
out = {}
for k, v in cases.items():
    a = cp[air_T[k]]; keep = (P.RHO_AIR, P.CP_AIR, P.K_AIR, P.MU_AIR, P.PR_AIR)
    P.RHO_AIR, P.CP_AIR, P.K_AIR, P.MU_AIR, P.PR_AIR = a["rho"], a["cp"], a["k"], a["mu"], a["Pr"]
    import network; network.P = P
    pk = run_case(k, **v)["peak_interior_C"]
    P.RHO_AIR, P.CP_AIR, P.K_AIR, P.MU_AIR, P.PR_AIR = keep
    out[k] = dict(constant_props_peak=base[k], coolprop_props_peak=pk, change_K=pk - base[k], air_T_used=air_T[k])
    print(k, out[k])
json.dump(out, open(os.path.join(R, "air_props_check.json"), "w"), indent=1)
