"""Electrical feasibility (ASSUMED all-series string, sloped Na-ion OCV 2.55-3.70 V, 151 Ah, R calibrated to 6.1 W):
can the cabinet deliver 30 kW for 2 h with k cells bypassed from t=0? Constant power vs constant current. SOC tracked."""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from network import Network
import params as P
RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
rows = []
for window in (1.0, 1.05):
    for mode in ("power", "current"):
        for k in (0, 4, 8, 13):
            byp = np.zeros((1, 8, 16), bool)
            if k:
                byp.reshape(-1)[np.linspace(0, 127, k).astype(int)] = True
            n = Network(B=1, mode="passive", T_amb=40.0, elec=True, elec_mode=mode, soc0=window, soc_min=0.0,
                        n_min_active=100, r_switch=P.R_SWITCH)
            n.bypass = byp
            t_end = None; Ivals = []; Vvals = []
            while n.t < 3 * 3600:
                n.step(10.0, record=True)
                Ivals.append(float(n.I[0])); Vvals.append(float(n.V[0]))
                if not bool(n.running[0]):
                    t_end = n.t; break
            E = float(n.E["elec_out"][0]) / 3.6e6
            rows.append(dict(usable_window=window, mode=mode, k_bypassed=k, runtime_h=(t_end or n.t) / 3600, energy_kWh=E,
                             I_start_A=Ivals[0], I_end_A=Ivals[-2] if len(Ivals) > 1 else Ivals[0],
                             V_start=Vvals[0], V_end=Vvals[-2] if len(Vvals) > 1 else Vvals[0],
                             peak_C=float(n.rec["Tmax"].max()), bypass_switch_loss_kWh=float(n.E["loss_sw"][0]) / 3.6e6,
                             meets_30kW_2h=(mode == "power" and (t_end or 1e9) >= 7200 - 1)))
            r = rows[-1]
            print(f"window {window:.2f} {mode:7s} k={k:2d}: runtime {r['runtime_h']:.2f} h, E {r['energy_kWh']:.1f} kWh, I {r['I_start_A']:.0f}->{r['I_end_A']:.0f} A, "
                  f"V {r['V_start']:.0f}->{r['V_end']:.0f} V, peak {r['peak_C']:.1f} C, switch loss {r['bypass_switch_loss_kWh']*1000:.0f} Wh, 30kW x 2h: {r['meets_30kW_2h']}")
json.dump(rows, open(os.path.join(RES, "feasibility.json"), "w"), indent=1)
