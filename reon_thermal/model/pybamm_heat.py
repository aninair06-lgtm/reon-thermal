"""Heat-generation cross-check with PyBaMM's disclosed sodium-ion parameter set (Chayambuka et al. 2022).
NOT the REON cell: a published hard-carbon / NVPF-type Na-ion cell (3 mAh coin-cell geometry), used only to see whether
the brief's 6.1 W per cell at 0.5 C is plausible for sodium-ion. Irreversible heat Q = I (V_eq - V), with the
equilibrium curve V_eq(discharged charge) from a C/50 discharge; entropic heat not included. Scaled to the REON cell's
implied 151 Ah by keeping the same areal current (heat ~ capacity at the same C-rate)."""
import json, os
import numpy as np
import pybamm
param = pybamm.ParameterValues("Chayambuka2022")
cap = float(param["Nominal cell capacity [A.h]"])

def run(C):
    p = param.copy(); p["Current function [A]"] = C * cap
    sol = pybamm.Simulation(pybamm.sodium_ion.BasicDFN(), parameter_values=p).solve([0, 3600 / C * 1.05])
    t = sol["Time [s]"].entries; V = sol["Voltage [V]"].entries
    return t, V, C * cap * t / 3600.0          # time, voltage, discharged Ah

t0, V0, q0 = run(0.02)
out = dict(cell="Chayambuka2022 (PyBaMM), not the REON cell", capacity_Ah=cap, rate={})
for C in (0.25, 0.5, 1.0):
    t, V, q = run(C)
    Veq = np.interp(q, q0, V0)
    Q = C * cap * (Veq - V)
    Qm = float(np.trapezoid(Q, t) / (t[-1] - t[0]))
    E = float(np.trapezoid(C * cap * V, t) / 3600)
    out["rate"][str(C)] = dict(t_end_s=float(t[-1]), V_mean=float(np.mean(V)), heat_mean_W=Qm, heat_end_W=float(Q[-1]),
                               heat_as_pct_of_power=100 * Qm / float(np.mean(C * cap * V)), energy_Wh=E)
    print(C, out["rate"][str(C)])
r = out["rate"]["0.5"]
out["scaled_to_151Ah_0_5C_W"] = r["heat_mean_W"] * 151.0 / cap
out["scaled_end_of_discharge_W"] = r["heat_end_W"] * 151.0 / cap
out["brief_6_1W_as_pct_of_power"] = 100 * 6.1 / (30000 / 128)
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "pybamm_heat.json"), "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "rate"}, indent=1))
