"""Stage 4 - beyond bypass: each idea quantified on the calibrated network for the WORST realistic day
(sealed cabinet, 40 C ambient, cabinet already at 55 C, one aged cell (3x R) at M07_C08, 30 kW for 2 h),
plus the heat-generation what-if from the PyBaMM sodium-ion cross-check."""
import sys, os, json, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_cases import run_case
import params as P
RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
AGED = (6, 7)
FAN_W = 40.0          # fan electrical power for 0.15 m3/s at ~100 Pa (AA)
COP = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "coolprop_pvlib.json")))["ac_cop_R32"]["40"]   # CoolProp R-32 cycle at 40 C
TM = json.load(open(os.path.join(RES, "network_Tmax_cell.json")))["C_passive40"]
cool = np.unravel_index(np.argmin(np.array(TM)), (8, 16))
base = dict(mode="passive", T_amb=40.0, h_ext=5.0, T_init=55.0, aged=AGED)

from solar import roof, west as side   # pvlib clear sky, Phoenix 21 June, discharge 14:00-16:00

ideas = [
 ("Do nothing (worst day)", dict(), "", 0.0),
 ("Bypass the aged cell", dict(bypass_ids=[P.cell_id(7, 8)], elec="current"), "control only", 0.0),
 ("Move the aged cell to the coolest slot", dict(aged=cool), "maintenance swap", 0.0),
 ("Turn cells so heat leaves along 25 W/m K", dict(extra=dict(kx=25.0)), "redesign of the stack", 0.0),
 ("Aluminium spreaders to the side walls (3 W/K per module end)", dict(extra=dict(G_sup=3.0)), "hardware, passive", 0.0),
 ("Heat pipe from every cell to the rear wall (1 W/K each)", dict(extra=dict(G_hp=1.0)), "hardware, passive", 0.0),
 ("Phase-change plates in the gaps (0.25 kg/cell, melts 46 C)", dict(extra=dict(pcm_kg=0.25)), "hardware, passive", 0.0),
 ("Chimney vent (natural draft ~0.03 m3/s, 40 C air)", dict(mode="forced", flow=0.03, extra=dict(T_supply=40.0)), "two grilles, no power", 0.0),
 ("Fan, no air conditioning (0.15 m3/s of 40 C air)", dict(mode="forced", flow=0.15, extra=dict(T_supply=40.0)), "fan", FAN_W * 2 / 1000),
 ("Night pre-cooling: start at 45 C", dict(T_init=45.0), "fan at night", FAN_W * 6 / 1000),
 ("Night pre-cooling: start at 40 C", dict(T_init=40.0), "fan at night", FAN_W * 8 / 1000),
 ("Worst day plus afternoon sun (dark paint, absorptance 0.6)", dict(solar=(roof, side)), "for comparison", 0.0),
 ("Reflective paint with that sun (absorptance 0.6 -> 0.2)", dict(solar=(roof, side), extra=dict(solar_mult=1 / 3)), "paint", 0.0),
 ("Same energy at half power over 4 h", dict(elec="derate", tend=4 * 3600.0, schedule=lambda t: (True, 0.5, -1)), "scheduling", 0.0),
 ("Air conditioning (0.15 m3/s supplied at 20 C)", dict(mode="forced", flow=0.15, extra=dict(T_supply=20.0)), "chiller", None),
 ("Bypass aged cell + pre-cool to 45 C", dict(T_init=45.0, bypass_ids=[P.cell_id(7, 8)], elec="current"), "control + fan", FAN_W * 6 / 1000),
 ("Bypass aged cell + phase-change plates", dict(bypass_ids=[P.cell_id(7, 8)], elec="current", extra=dict(pcm_kg=0.25)), "control + hardware", 0.0),
 ("Phase-change plates that melt at 57 C", dict(extra=dict(pcm_kg=0.25, pcm_Tm=57.0)), "hardware, passive", 0.0),
 ("Bypass aged cell + plates that melt at 57 C", dict(bypass_ids=[P.cell_id(7, 8)], elec="current", extra=dict(pcm_kg=0.25, pcm_Tm=57.0)), "control + hardware", 0.0),
]
rows = []
for name, kw, kind, e_extra in ideas:
    a = dict(base); a.update(kw)
    a.setdefault("elec", "power")
    r = run_case(name, **a)
    if e_extra is None:      # AC: electricity = heat removed by the supply air / COP (+ fan)
        e_extra = r["E_air_kWh"] / COP + FAN_W * 2 / 1000
    rows.append(dict(idea=name, kind=kind, peak_C=r["peak_interior_C"], peak_cell=r["peak_cell"], below_60=r["below_60"],
                     energy_kWh=r["energy_delivered_kWh"], extra_kWh_per_day=e_extra, closure_pct=r["energy_closure_pct"]))
    print(f"{name:62s} peak {r['peak_interior_C']:6.2f} C {r['peak_cell']}  <60 {r['below_60']!s:5s}  E {r['energy_delivered_kWh']:5.1f} kWh  extra {e_extra:5.2f} kWh/d")
# heat-generation what-if: PyBaMM Chayambuka2022 scaled heat (not the REON cell)
pb = json.load(open(os.path.join(RES, "pybamm_heat.json")))
qpb = pb["scaled_to_151Ah_0_5C_W"]
whatif = {}
for nm, kw in (("normal start 40 C", dict(T_init=None)), ("hot start 55 C", dict(T_init=55.0))):
    r = run_case("pb", "passive", 40.0, 5.0, q_base=qpb, **kw)
    lo, hi = 0.05, 1.0
    for _ in range(14):
        mid = 0.5 * (lo + hi)
        rr = run_case("pb", "passive", 40.0, 5.0, q_base=qpb, elec="derate", schedule=lambda t, m=mid: (True, m, -1), **kw)
        if rr["peak_interior_C"] < 59.95: lo = mid
        else: hi = mid
    whatif[nm] = dict(peak_C=r["peak_interior_C"], max_power_kW=30 * lo)
    print(f"PyBaMM heat {qpb:.1f} W/cell, {nm}: peak {r['peak_interior_C']:.1f} C, max power for <60 C {30*lo:.1f} kW")
json.dump(dict(case="sealed, 40 C ambient, start 55 C, aged cell M07_C08, 30 kW x 2 h", coolest_slot=P.cell_id(cool[0] + 1, cool[1] + 1),
               fan_W=FAN_W, ac_cop=COP, ideas=rows, pybamm_heat_W=qpb, pybamm_whatif=whatif),
          open(os.path.join(RES, "stage4.json"), "w"), indent=1)
