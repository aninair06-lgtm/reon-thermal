"""'Hot-spot tax': power a FIXED string must give up on a hot-start day because ONE aged cell runs hot,
versus cell-level control that bypasses that cell. Hot start 55 C, 40 C ambient, passive sealed cabinet."""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_cases import run_case
import params as P
RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
hz = (6, 7)
rows = []
def find(fn):
    lo, hi = 0.40, 1.0
    for _ in range(14):
        mid = 0.5 * (lo + hi)
        if fn(mid) < 59.95: lo = mid
        else: hi = mid
    return lo
fixed = lambda fr: run_case("x", "passive", 40.0, 5.0, T_init=55.0, aged=hz, elec="derate", schedule=lambda t: (True, fr, -1))["peak_interior_C"]
ctrl = lambda fr: run_case("x", "passive", 40.0, 5.0, T_init=55.0, aged=hz, bypass_ids=[P.cell_id(7, 8)], elec="derate",
                           schedule=lambda t: (True, fr * 128 / 127, -1))["peak_interior_C"]   # same delivered power with 127 active cells
nominal = lambda fr: run_case("x", "passive", 40.0, 5.0, T_init=55.0, elec="derate", schedule=lambda t: (True, fr, -1))["peak_interior_C"]
f_fixed, f_ctrl, f_nom = find(fixed), find(ctrl), find(nominal)
out = dict(case="hot start 55 C, 40 C ambient, sealed, one aged cell (3x R) at M07_C08",
           max_power_fixed_string_kW=30 * f_fixed, max_power_cell_control_kW=30 * f_ctrl, max_power_no_aged_cell_kW=30 * f_nom,
           recovered_kW=30 * (f_ctrl - f_fixed), recovered_kWh_per_hot_day=60 * (f_ctrl - f_fixed))
print(json.dumps(out, indent=1))
json.dump(out, open(os.path.join(RES, "hotspot_tax.json"), "w"), indent=1)
