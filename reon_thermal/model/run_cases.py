"""Run every network case of the study, write cells.csv (every 60 s) and a summary JSON.

Electrical bookkeeping under the ASSUMED all-series string (REON has not published topology):
  constant power  : 115 active cells carry I = 128/115 x rated -> 6.1*(128/115)^2 = 7.56 W each
  constant current: active cells stay at 6.1 W, delivered power drops to Nact/128 x 30 kW
  derating        : no bypass, all cells at 6.1*(P/30kW)^2 W
Bypassed cell: ideal 0 W (sensitivity: I^2 * R_switch at the cell).
"""
import sys, os, json, csv, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from network import Network
import params as P

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
CAL = {}
try:
    c = json.load(open(os.path.join(RES, "calibration_A_sst_m1.json")))
    CAL["forced"] = dict(h_mult=c["best"]["h_mult"], G_ex_forced=c["best"]["G_ex_forced"],
                         w_ch=c["flow_split"]["channel_share"], f_side=c["flow_split"]["side_share"])
except Exception:
    CAL["forced"] = {}
try:
    c = json.load(open(os.path.join(RES, "calibration_Ct_lam_m1.json")))
    CAL["passive"] = c["best"]
except Exception:
    CAL["passive"] = {}

def ids_to_mask(ids):
    m = np.zeros((8, 16), bool)
    for s in ids:
        mm, cc = int(s[1:3]) - 1, int(s[5:7]) - 1
        m[mm, cc] = True
    return m

class Controller:
    """Adaptive bypass using only present/past sensor readings (surface T + noise, delayed), hysteresis and dwell."""
    def __init__(self, T_on=57.0, T_off=54.0, n_max=13, dwell=300.0, delay=30.0, noise=0.5, period=10.0, seed=0, power_mode="power"):
        self.T_on, self.T_off, self.n_max, self.dwell, self.delay, self.noise = T_on, T_off, n_max, dwell, delay, noise
        self.period, self.rng, self.power_mode = period, np.random.default_rng(seed), power_mode
        self.buf = []; self.state = np.zeros((8, 16), bool); self.since = np.full((8, 16), -1e9); self.events = []
    def update(self, t, Tsurf):
        self.buf.append((t, Tsurf + self.rng.normal(0, self.noise, Tsurf.shape)))
        old = [b for b in self.buf if b[0] <= t - self.delay]
        if not old: return self.state
        meas = old[-1][1]
        self.buf = [b for b in self.buf if b[0] > t - self.delay - 60]
        can_change = (t - self.since) >= self.dwell
        rel = self.state & (meas < self.T_off) & can_change
        self.state[rel] = False; self.since[rel] = t
        cand = (~self.state) & (meas > self.T_on) & can_change
        free = self.n_max - self.state.sum()
        if free > 0 and cand.any():
            order = np.argsort(np.where(cand, meas, -1e9).ravel())[::-1][:free]
            for i in order:
                if cand.ravel()[i]:
                    self.state.ravel()[i] = True; self.since.ravel()[i] = t
        self.events.append((t, int(self.state.sum())))
        return self.state

def run_case(cid, mode="passive", T_amb=40.0, h_ext=5.0, T_init=None, tend=7200.0, dt=10.0, q_base=P.Q_NORMAL,
             bypass_ids=(), elec="power", controller=None, aged=None, aged_q=None, q_bypass=0.0, Q_inverter=0.0,
             flow=P.Q_FORCED, solar=None, schedule=None, record_every=60.0, writer=None, extra=None):
    kw = dict(mode=mode, T_amb=T_amb, h_ext=h_ext, T_init=T_init, Q_inverter=Q_inverter, flow=flow)
    kw.update(CAL.get(mode, {}))
    if solar is not None:
        kw.update(solar_roof=solar[0], solar_side=solar[1])
    if extra: kw.update(extra)
    n = Network(B=1, **kw)
    byp = ids_to_mask(bypass_ids)
    rmult = np.ones((8, 16))
    if aged is not None:
        rmult[aged] = 3.0
    peak = -1e9; t_peak = 0; cell_peak = None; hist = []
    E_del = 0.0; E_loss_extra = 0.0; Tmax_cell = np.full((8, 16), -1e9)
    while n.t < tend - 1e-9:
        t = n.t
        on = True; P_frac = 1.0
        if schedule is not None:
            on, P_frac, sign = schedule(t)
        if controller is not None and (abs(t % controller.period) < 1e-6):
            Ts = np.asarray(n.rec["Tsurf"][0]) if hasattr(n, "rec") else np.asarray(n.Tc[0])
            byp = controller.update(t, Ts).copy()
        nact = 128 - byp.sum()
        if elec == "power":            # constant delivered power -> higher string current
            I_rel = (128.0 / nact) * P_frac
        elif elec == "current":
            I_rel = 1.0 * P_frac
        else:                          # 'derate': P_frac already the derate, no bypass
            I_rel = P_frac
        q = q_base * I_rel ** 2 * rmult
        if aged_q is not None and aged is not None:
            q[aged] = aged_q * I_rel ** 2
        q = np.where(byp, q_bypass * I_rel ** 2, q)
        if not on: q = q * 0.0
        n.q_presc = q[None]
        n.bypass = np.zeros((1, 8, 16), bool)
        n.step(dt, record=True)
        Pdel = (P.P_RATED_W * (nact / 128.0) * I_rel if elec != "derate" else P.P_RATED_W * P_frac) if on else 0.0
        E_del += Pdel * dt
        Tint = np.asarray(n.rec["Tmax"][0])
        Tmax_cell = np.maximum(Tmax_cell, Tint)
        if Tint.max() > peak:
            peak, t_peak = float(Tint.max()), n.t; cell_peak = np.unravel_index(Tint.argmax(), Tint.shape)
        if writer is not None and abs(n.t % record_every) < 1e-6:
            r = n.rec
            for m in range(8):
                for c in range(16):
                    writer.writerow([cid, int(round(n.t)), m + 1, P.cell_id(m + 1, c + 1),
                                     round(float(r["Tmean"][0, m, c]), 4), round(float(r["Tmax"][0, m, c]), 4),
                                     round(float(r["Tsurf"][0, m, c]), 4), round(float(r["Tair"][0, m, c]), 4),
                                     round(float(r["q"][0, m, c]), 4), round(float(r["Qair"][0, m, c]), 4),
                                     round(float(r["Qnb"][0, m, c]), 4), round(float(r["Qsup"][0, m, c]), 4),
                                     "NA", "NA", "NA", int(byp[m, c])])
        hist.append((n.t, float(Tint.max()), float(np.asarray(n.rec["Tmean"][0]).max() - np.asarray(n.rec["Tmean"][0]).min()),
                     float(np.asarray(n.rec["Tmean"][0]).mean()), int(byp.sum()), Pdel))
    Tm = np.asarray(n.Tc[0])
    return dict(case_id=cid, mode=mode, T_amb=T_amb, h_ext=h_ext, T_init=T_init if T_init is not None else T_amb,
                peak_interior_C=peak, peak_time_s=t_peak, peak_cell=P.cell_id(cell_peak[0] + 1, cell_peak[1] + 1),
                below_60=bool(peak < 60.0), margin_K=60.0 - peak, spread_end_K=float(Tm.max() - Tm.min()),
                mean_end_C=float(Tm.mean()), energy_delivered_kWh=E_del / 3.6e6, avg_power_kW=E_del / tend / 1e3,
                total_heat_end_W=float(np.asarray(n.rec["q"][0]).sum()),
                energy_closure_pct=float(n.energy_error()[0]) * 100, n_bypassed_max=int(max(h[4] for h in hist)),
                history=hist, Tmax_cell=Tmax_cell.tolist(),
                E_air_kWh=float(n.E["enth"][0]) / 3.6e6, E_ext_kWh=float(n.E["ext"][0]) / 3.6e6,
                events=(controller.events if controller is not None else None))

def daily(t):
    """Discharge 2 h at rated power, rest 4 h, charge 2.4 h at 0.83x rated (energy-feasible incl. 4 % loss), rest."""
    tt = t % 86400.0
    if tt < 7200: return True, 1.0, -1
    if tt < 7200 + 14400: return False, 0.0, 0
    if tt < 7200 + 14400 + 8640: return True, 0.83, +1
    return False, 0.0, 0

if __name__ == "__main__":
    os.makedirs(RES, exist_ok=True)
    f = open(os.path.join(RES, "cells.csv"), "w", newline="")
    w = csv.writer(f)
    w.writerow(["case_id", "time_s", "module_id", "cell_id", "T_volume_mean_C", "T_internal_max_C", "T_surface_mean_C",
                "T_air_reference_C", "heat_generation_W", "heat_to_air_W", "heat_to_neighbours_W", "heat_to_supports_W",
                "current_A", "voltage_V", "SOC", "bypass_state"])
    out = {}
    t0 = time.time()
    # --- baselines
    out["A_forced25"] = run_case("A_forced25", "forced", 25.0, 5.0, writer=w)
    out["B_passive25"] = run_case("B_passive25", "passive", 25.0, 5.0, writer=w)
    out["B_passive25_h10"] = run_case("B_passive25_h10", "passive", 25.0, 10.0)
    out["C_passive40"] = run_case("C_passive40", "passive", 40.0, 5.0, writer=w)
    out["C_passive40_h10"] = run_case("C_passive40_h10", "passive", 40.0, 10.0)
    # 13 hottest of C by max interior T over the whole discharge
    Tc = np.array(out["C_passive40"]["Tmax_cell"])
    hot13 = [P.cell_id(i // 16 + 1, i % 16 + 1) for i in np.argsort(Tc.ravel())[::-1][:13]]
    out["hot13_basis"] = dict(ids=hot13, basis="network C_passive40, max interior T over 0-7200 s")
    out["D_fixed13_power"] = run_case("D_fixed13_power", "passive", 40.0, 5.0, bypass_ids=hot13, elec="power", writer=w)
    out["D_fixed13_current"] = run_case("D_fixed13_current", "passive", 40.0, 5.0, bypass_ids=hot13, elec="current")
    out["D_adaptive_power"] = run_case("D_adaptive_power", "passive", 40.0, 5.0, controller=Controller(), elec="power", writer=w)
    # --- hot start 55 C at 40 C ambient
    out["H_hotstart"] = run_case("H_hotstart", "passive", 40.0, 5.0, T_init=55.0, writer=w)
    Th = np.array(out["H_hotstart"]["Tmax_cell"])
    hot13h = [P.cell_id(i // 16 + 1, i % 16 + 1) for i in np.argsort(Th.ravel())[::-1][:13]]
    out["H_fixed13_power"] = run_case("H_fixed13_power", "passive", 40.0, 5.0, T_init=55.0, bypass_ids=hot13h, elec="power")
    out["H_fixed13_current"] = run_case("H_fixed13_current", "passive", 40.0, 5.0, T_init=55.0, bypass_ids=hot13h, elec="current")
    out["H_adaptive_power"] = run_case("H_adaptive_power", "passive", 40.0, 5.0, T_init=55.0, controller=Controller(), elec="power", writer=w)
    out["H_adaptive_current"] = run_case("H_adaptive_current", "passive", 40.0, 5.0, T_init=55.0, controller=Controller(power_mode="current"), elec="current")
    for frac in (0.95, 0.9, 0.85, 0.8, 0.7):
        out[f"H_derate_{int(frac*100)}"] = run_case(f"H_derate_{int(frac*100)}", "passive", 40.0, 5.0, T_init=55.0, elec="derate",
                                                     schedule=lambda t, fr=frac: (True, fr, -1))
    # --- one aged cell (3x R) in the hot zone
    hz = np.unravel_index(Tc.argmax(), Tc.shape)
    out["aged_info"] = dict(cell=P.cell_id(hz[0] + 1, hz[1] + 1))
    out["E_aged_C"] = run_case("E_aged_C", "passive", 40.0, 5.0, aged=hz, writer=w)
    out["E_aged_C_bypass1_current"] = run_case("E_aged_C_bypass1_current", "passive", 40.0, 5.0, aged=hz, bypass_ids=[P.cell_id(hz[0]+1, hz[1]+1)], elec="current")
    out["E_aged_C_bypass1_power"] = run_case("E_aged_C_bypass1_power", "passive", 40.0, 5.0, aged=hz, bypass_ids=[P.cell_id(hz[0]+1, hz[1]+1)], elec="power")
    out["E_aged_hot"] = run_case("E_aged_hot", "passive", 40.0, 5.0, T_init=55.0, aged=hz)
    out["E_aged_hot_adaptive"] = run_case("E_aged_hot_adaptive", "passive", 40.0, 5.0, T_init=55.0, aged=hz, controller=Controller(n_max=4), elec="power")
    out["E_aged_hot_bypass1_current"] = run_case("E_aged_hot_bypass1_current", "passive", 40.0, 5.0, T_init=55.0, aged=hz, bypass_ids=[P.cell_id(hz[0]+1, hz[1]+1)], elec="current")
    # --- variants
    out["A_halfflow"] = run_case("A_halfflow", "forced", 25.0, 5.0, flow=P.Q_FORCED / 2)
    out["C_inverter"] = run_case("C_inverter", "passive", 40.0, 5.0, Q_inverter=750.0)
    out["D_inverter"] = run_case("D_inverter", "passive", 40.0, 5.0, Q_inverter=750.0, bypass_ids=hot13, elec="power")
    out["C_bypass_switchloss"] = run_case("C_bypass_switchloss", "passive", 40.0, 5.0, bypass_ids=hot13, elec="power",
                                         q_bypass=(P.I_RATED ** 2) * P.R_SWITCH)
    # solar: hot-site clear-sky worst day (pvlib-equivalent clear-sky shape, peak 1000 W/m2 roof, 600 W/m2 west wall, absorptance 0.6)
    from solar import roof, west as side   # pvlib clear sky, Phoenix 21 June, discharge 14:00-16:00
    out["C_solar"] = run_case("C_solar", "passive", 40.0, 5.0, solar=(roof, side))
    out["D_solar"] = run_case("D_solar", "passive", 40.0, 5.0, solar=(roof, side), bypass_ids=hot13, elec="power")
    # --- daily cycle, third day reported (40 C ambient)
    dc = run_case("DAY_passive40", "passive", 40.0, 5.0, tend=3 * 86400.0, dt=20.0, schedule=daily, record_every=1e12)
    h = np.array(dc["history"]); d3 = h[h[:, 0] > 2 * 86400]
    dc["day3_peak_C"] = float(d3[:, 1].max()); dc["day3_min_C"] = float(d3[:, 3].min())
    dc["day3_start_meanT_C"] = float(d3[0, 3])
    out["DAY_passive40"] = dc
    f.close()
    summ = {k: {kk: vv for kk, vv in v.items() if kk not in ("history", "Tmax_cell", "events")} if isinstance(v, dict) and "history" in v else v
            for k, v in out.items()}
    json.dump(summ, open(os.path.join(RES, "network_cases.json"), "w"), indent=1)
    json.dump({k: v["history"] for k, v in out.items() if isinstance(v, dict) and "history" in v},
              open(os.path.join(RES, "network_histories.json"), "w"))
    json.dump({k: v["Tmax_cell"] for k, v in out.items() if isinstance(v, dict) and "Tmax_cell" in v},
              open(os.path.join(RES, "network_Tmax_cell.json"), "w"))
    json.dump({k: v["events"] for k, v in out.items() if isinstance(v, dict) and v.get("events")},
              open(os.path.join(RES, "network_bypass_events.json"), "w"))
    for k, v in summ.items():
        if isinstance(v, dict) and "peak_interior_C" in v:
            print(f"{k:28s} peak {v['peak_interior_C']:6.2f} C @ {v['peak_time_s']:6.0f}s {v['peak_cell']}  <60:{v['below_60']!s:5s} "
                  f"spread {v['spread_end_K']:5.2f}  E {v['energy_delivered_kWh']:6.2f} kWh  P {v['avg_power_kW']:5.2f} kW  "
                  f"heat {v['total_heat_end_W']:6.1f} W  byp {v['n_bypassed_max']:2d}  closure {v['energy_closure_pct']:+.4f}%")
    print("DAY3:", out["DAY_passive40"]["day3_peak_C"], out["DAY_passive40"]["day3_start_meanT_C"])
    print("hot13:", hot13, "aged at", out["aged_info"])
    print(f"total {time.time()-t0:.0f}s")
