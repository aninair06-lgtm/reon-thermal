"""Two-way coupled electro-thermal runs with literature Na-ion parameters (lit_params.py) on the calibrated network.
Writes results/cells.csv with current, voltage and SOC filled (the earlier prescribed-heat file is kept as
cells_prescribed_heat.csv) and results/ec_cases.json. All-series string (AA), constant delivered power 30 kW."""
import sys, os, json, csv, shutil
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from network import Network
from run_cases import CAL
import params as P
import lit_params as L
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
CAP = P.E_RATED_WH / (P.N_CELLS * L.MEAN_OCV)      # Ah per cell so that the OCV energy is the 60 kWh nameplate
IDS = [P.cell_id(m + 1, c + 1) for m in range(8) for c in range(16)]

def run(cid, mode="passive", T_amb=40.0, h_ext=5.0, T_init=None, R_ref=1.07e-3, dUdT=0.0, w_pol=L.W_POL, aged=None,
        bypass=(), P_W=P.P_RATED_W, tend=7200.0, dt=10.0, writer=None, flow=P.Q_FORCED, extra=None):
    kw = dict(mode=mode, T_amb=T_amb, h_ext=h_ext, T_init=T_init, flow=flow); kw.update(CAL.get(mode, {}))
    if extra: kw.update(extra)
    n = Network(B=1, **kw)
    soc = np.ones((8, 16)); rmult = np.ones((8, 16))
    if aged is not None: rmult[aged] = 3.0
    byp = np.zeros((8, 16), bool)
    for s in bypass: byp[int(s[1:3]) - 1, int(s[5:7]) - 1] = True
    E_out = 0.0; heat_hist = []; peak = -1e9; t_peak = 0; cell_peak = None; stop_reason = "time"; I = 0.0
    while n.t < tend - 1e-9:
        T = np.asarray(n.Tc[0])
        Ri = R_ref * rmult * L.r_shape(soc) * L.r_temp(T, w_pol=w_pol)
        U = L.ocv(soc) + dUdT * (T - 25.0)
        act = ~byp & (soc > 0)
        Voc = U[act].sum(); Rp = Ri[act].sum() + P.R_SWITCH * (~act).sum() + 0.0
        disc = Voc ** 2 - 4 * Rp * P_W
        if disc <= 0: stop_reason = "power limit"; break
        I = (Voc - np.sqrt(disc)) / (2 * Rp)
        Vt = np.where(act, U - I * Ri, U)
        if (Vt[act] < L.V_MIN).any(): stop_reason = "cell at 1.5 V"; break
        q = np.where(act, I ** 2 * Ri - I * (T + 273.15) * dUdT, I ** 2 * P.R_SWITCH)
        soc = soc - np.where(act, I, 0.0) * dt / (CAP * 3600.0)
        n.q_presc = q[None]; n.bypass = np.zeros((1, 8, 16), bool)
        n.step(dt, record=True)
        E_out += P_W * dt; heat_hist.append(float(q.mean()))
        Tint = np.asarray(n.rec["Tmax"][0])
        if Tint.max() > peak: peak, t_peak = float(Tint.max()), n.t; cell_peak = IDS[int(Tint.argmax())]
        if writer is not None and abs(n.t % 60.0) < 1e-6:
            r = n.rec
            for k in range(128):
                m, c = divmod(k, 16)
                writer.writerow([cid, int(round(n.t)), m + 1, IDS[k], round(float(r["Tmean"][0, m, c]), 4), round(float(r["Tmax"][0, m, c]), 4),
                                 round(float(r["Tsurf"][0, m, c]), 4), round(float(r["Tair"][0, m, c]), 4), round(float(q[m, c]), 4),
                                 round(float(r["Qair"][0, m, c]), 4), round(float(r["Qnb"][0, m, c]), 4), round(float(r["Qsup"][0, m, c]), 4),
                                 round(float(I if act[m, c] else 0.0), 3), round(float(Vt[m, c]), 4), round(float(soc[m, c]), 5), int(byp[m, c])])
    hh = np.array(heat_hist) if heat_hist else np.array([0.0])
    return dict(case_id=cid, peak_interior_C=peak, peak_time_s=t_peak, peak_cell=cell_peak, below_60=bool(peak < 60), runtime_h=n.t / 3600,
                energy_kWh=E_out / 3.6e6, stop=stop_reason, heat_mean_W=float(hh.mean()), heat_first_W=float(hh[0]), heat_last_W=float(hh[-1]),
                I_last_A=float(I), soc_min_end=float(soc.min()), energy_closure_pct=float(n.energy_error()[0]) * 100, R_ref_mOhm=R_ref * 1e3, dUdT_mV_K=dUdT * 1e3)

if __name__ == "__main__":
    # 1. calibrate R_ref: mean heat over a 30 kW discharge at 25 C (passive, start 25 C) = 6.1 W (the brief's value)
    Rr = 1.07e-3
    for _ in range(3):
        r = run("cal", "passive", 25.0, R_ref=Rr)
        Rr *= 6.1 / r["heat_mean_W"]
    print(f"R_ref (brief-matched, 25 C, 50 % SOC) = {Rr*1e3:.3f} mOhm; capacity {CAP:.1f} Ah; check heat {run('cal', 'passive', 25.0, R_ref=Rr)['heat_mean_W']:.2f} W")
    hot13 = json.load(open(os.path.join(R, "network_cases.json")))["hot13_basis"]["ids"]
    p_old = os.path.join(R, "cells.csv"); p_keep = os.path.join(R, "cells_prescribed_heat.csv")
    if os.path.exists(p_old) and not os.path.exists(p_keep): shutil.copy(p_old, p_keep)
    f = open(p_old, "w", newline=""); w = csv.writer(f)
    w.writerow(["case_id", "time_s", "module_id", "cell_id", "T_volume_mean_C", "T_internal_max_C", "T_surface_mean_C", "T_air_reference_C",
                "heat_generation_W", "heat_to_air_W", "heat_to_neighbours_W", "heat_to_supports_W", "current_A", "voltage_V", "SOC", "bypass_state"])
    out = dict(R_ref_mOhm=Rr * 1e3, capacity_Ah=CAP, R_pulse18650_scaled_mOhm=L.R_PULSE_150AH * 1e3, cases={})
    specs = [
        ("A_EC_forced25", dict(mode="forced", T_amb=25.0)), ("B_EC_passive25", dict(T_amb=25.0)), ("C_EC_passive40", dict()),
        ("D_EC_13bypassed", dict(bypass=hot13)), ("H_EC_hotstart55", dict(T_init=55.0)),
        ("E_EC_aged", dict(aged=(6, 7))), ("E_EC_aged_bypassed", dict(aged=(6, 7), bypass=["M07_C08"])),
        ("E_EC_aged_hotstart", dict(aged=(6, 7), T_init=55.0)), ("E_EC_aged_hotstart_bypassed", dict(aged=(6, 7), T_init=55.0, bypass=["M07_C08"])),
    ]
    for cid, kw in specs:
        r = run(cid, R_ref=Rr, writer=w, **kw); out["cases"][cid] = r
        print(f"{cid:30s} peak {r['peak_interior_C']:6.2f} C {r['peak_cell']} @{r['peak_time_s']:5.0f}s  runtime {r['runtime_h']:.2f} h ({r['stop']})  "
              f"E {r['energy_kWh']:5.1f} kWh  heat {r['heat_first_W']:.1f}->{r['heat_last_W']:.1f} W (mean {r['heat_mean_W']:.1f})  closure {r['energy_closure_pct']:+.4f}%")
    f.close()
    # 2. sensitivities on C and the hot start: reversible heat, polarisation share, published-pulse resistance
    sens = {}
    for nm, kw in (("dUdT +0.2 mV/K", dict(dUdT=2e-4)), ("dUdT -0.2 mV/K", dict(dUdT=-2e-4)), ("polarisation share 0.05", dict(w_pol=0.05)),
                   ("polarisation share 0.9", dict(w_pol=0.9)), ("published 18650 pulse resistance scaled", dict(R_ref=L.R_PULSE_150AH))):
        a = dict(R_ref=Rr); a.update(kw)
        sens[nm] = dict(C=run("s", **a), hot_start=run("s", T_init=55.0, **a))
        print(f"{nm:42s} C peak {sens[nm]['C']['peak_interior_C']:.2f} (heat {sens[nm]['C']['heat_mean_W']:.1f} W), hot start {sens[nm]['hot_start']['peak_interior_C']:.2f}")
    out["sensitivity"] = sens
    json.dump(out, open(os.path.join(R, "ec_cases.json"), "w"), indent=1)
