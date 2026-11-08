"""Lifetime, economic and environmental model: fixed series string vs REON cell-level control.

Chain (every link stated, every number an input-register entry):
  heat_i = I^2 R_i  ->  cell temperature T_i = T_site + a*mean(heat) + b*(heat_i - mean heat)   [a, b from our network/Elmer runs]
  ageing rate_i  = r_ref * AF(T_i),  AF = exp(Ea/R (1/T_ref - 1/T))                             [Arrhenius; Na-ion Ea ASSUMED]
  resistance     R_i = R0_i * (1 + g * fade_i / 0.30)                                          [feedback: older -> hotter]
  end of service = usable energy < 70 % of beginning of life (stationary threshold, brief)
     fixed string : usable = 128 * min(capacity)         (weakest cell stops the string)
     cell control : usable = sum min(cap_i, c*), c* = capacity of the N_min-th best cell (string needs N_min cells for voltage)
                    + thermal/health-aware participation: the k hottest-ageing cells sit out a share phi of each discharge
Monte Carlo over manufacturing spread. Reported as ranges (uniform inputs), not probabilities.
"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import params as P
RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
Rgas = 8.314

BASE = dict(
    Ea=35e3,              # J/mol, Na-ion ageing activation energy (AA; sweep 20-50 kJ/mol)
    fade_per_fec_25=4.0e-5,   # capacity fraction lost per full cycle at 25 C (AA: ~7500 FEC to 70 %; Na-ion vendor claims 3000-8000)
    cal_per_year_25=0.010,    # calendar fade per year at 25 C (AA)
    g=1.5,                # resistance growth: R = R0 (1 + g * fade/0.30)  -> 2.5x at 70 % (AA)
    a_K_per_W=6.0 / 6.1,  # daily-average cell temperature rise per W of average cell heat (network daily cycle: ~6 K at 6.1 W/cell)
    b_K_per_W=0.62 * 0.35,# local self-heating above pack mean per W of excess heat, daily-averaged (Elmer 0.62 K/W x 35 % duty)
    T_site_mean=27.0, T_site_amp=9.0,   # hot C&I site daily-mean ambient: mean and seasonal amplitude (AA, Phoenix-like)
    cap_sigma=0.015, r_sigma=0.06,      # manufacturing spread (AA)
    n_defect=1, defect_r=2.0,           # one weak/high-resistance cell per pack (AA; typical field outlier)
    fec_per_day=1.0, days_per_year=365,
    N_min=115,            # minimum active cells for the inverter voltage window (AA; 13 bypass slots, brief)
    k_rot=4, phi=0.25,    # control: 4 hottest-ageing cells sit out 25 % of each discharge (rotating)
    eol=0.70,
    # economics (AA, USD 2026)
    capex_per_kwh=350.0, value_per_kwh=0.12, demand_value_per_kw_month=12.0, discount=0.07, opex_per_year=300.0,
    grid_kgco2_per_kwh=0.37, embodied_kgco2_per_kwh=65.0, ac_cop=3.0,
)

def AF(Tc, Ea):
    return np.exp(Ea / Rgas * (1 / 298.15 - 1 / (Tc + 273.15)))

def cabinet_faults():
    """The five faults injected in the one-year backtest (model/backtest.py FAULTS), on the same cells and months.
    Each fault reaches its no-bypass year-1 state by month 12 (resistance steps at injection, contact growth ramps
    linearly) and is held there afterwards: the backtest says nothing about year 2 on, so faults neither heal nor keep
    growing. Under REON, the safety faults (tab, damage, plating) are retired in the month the backtest flags them;
    corrosion is left to the heat-aware rotation; the cooling fault stays in, because REON missed it."""
    import backtest as B
    tr = json.load(open(os.path.join(RES, "backtest_trace.json")))["cells"]
    out = []
    for cid, f in B.FAULTS.items():
        m, c = B.ix(cid); k = f["kind"]; left = B.WEEKS - 1 - f["week"]
        step = {"tab": f.get("contact", 0), "damage": f.get("ohm", 0) * (1 - B.W_POL), "plating": f.get("pol", 0) * B.W_POL}.get(k, 0.0)
        ramp = {"tab": f.get("grow_in_service", 0) * left, "corrosion": f.get("rate", 0) * left}.get(k, 0.0)
        flag = tr[cid]["flag"]
        out.append(dict(cell=m * 16 + c, kind=k, month=int(f["week"] * 12 / 52), cap=1 + f.get("cap", 0.0), r_step=step, r_ramp=ramp,
                        extra_W=f.get("extra_W", 0.0), retire_month=int(flag * 12 / 52) if k in B.SAFETY and flag is not None else None))
    return out

def simulate(p, control, n_packs=300, years=30, seed=0, faults=()):
    rng = np.random.default_rng(seed)
    N = 128
    cap0 = 1 + p["cap_sigma"] * rng.standard_normal((n_packs, N))
    R0 = np.exp(p["r_sigma"] * rng.standard_normal((n_packs, N)))
    for d in range(p["n_defect"]):
        R0[:, d] *= p["defect_r"]
    fade = np.zeros((n_packs, N))
    life = np.full(n_packs, np.nan)
    usable_hist = []; Tmax_hist = []
    steps_per_year = 12
    rmul = np.ones(N); extra = np.zeros(N); alive = np.ones(N, bool)
    for y in range(years * steps_per_year):
        month = y % steps_per_year
        for f in faults:                          # optional injected faults (see cabinet_faults)
            i = f["cell"]
            if y == f["month"]: cap0[:, i] *= f["cap"]; extra[i] = f["extra_W"]
            if y >= f["month"]: rmul[i] = 1 + f["r_step"] + f["r_ramp"] * min(1.0, (y - f["month"]) / max(1, 12 - f["month"]))
            if control and f["retire_month"] is not None and y == f["retire_month"]: alive[i] = False
        Tsite = p["T_site_mean"] + p["T_site_amp"] * np.sin(2 * np.pi * (month - 3) / 12)
        R = R0 * rmul * (1 + p["g"] * fade / 0.30)
        heat = P.Q_NORMAL * R                     # W per cell during discharge (same current: series string)
        part = np.ones((n_packs, N))
        if control:
            # health/thermal-aware rotation: k cells with the highest predicted ageing rate sit out phi of each discharge
            score = np.where(alive, heat, -np.inf)
            idx = np.argsort(score, axis=1)[:, ::-1][:, :p["k_rot"]]
            np.put_along_axis(part, idx, 1 - p["phi"], axis=1)
            part[:, ~alive] = 0.0                 # retired cells carry no current
        q_eff = heat * part + extra
        T = Tsite + p["a_K_per_W"] * q_eff.mean(1, keepdims=True) + p["b_K_per_W"] * (q_eff - q_eff.mean(1, keepdims=True))
        Tmax_hist.append(float(np.median(T.max(1))))
        af = AF(T, p["Ea"])
        dt_y = 1 / steps_per_year
        fade += af * (p["fade_per_fec_25"] * p["fec_per_day"] * p["days_per_year"] * dt_y * part + p["cal_per_year_25"] * dt_y)
        cap = cap0 * (1 - fade)
        if control:
            s = np.sort(np.where(alive, cap, -np.inf), axis=1)[:, ::-1]
            cstar = s[:, p["N_min"] - 1:p["N_min"]]
            usable = (np.minimum(cap, cstar) * alive).sum(1) / N
        else:
            usable = cap.min(1)
        usable_hist.append(usable)
        newly = np.isnan(life) & (usable < p["eol"])
        life[newly] = (y + 1) / steps_per_year
    life = np.where(np.isnan(life), years, life)
    return life, np.array(usable_hist), np.array(Tmax_hist)

def npv(annual, years, r):
    yrs = np.arange(1, int(np.floor(years)) + 1)
    v = (annual / (1 + r) ** yrs).sum()
    frac = years - np.floor(years)
    return v + frac * annual / (1 + r) ** (np.floor(years) + 1)

def economics(p, life_b, life_c, energy_loss_frac=0.0):
    E = P.E_RATED_WH / 1e3
    annual = E * p["fec_per_day"] * p["days_per_year"] * p["value_per_kwh"] + 30 * p["demand_value_per_kw_month"] * 12 - p["opex_per_year"]
    capex = E * p["capex_per_kwh"]
    v_b = npv(annual, life_b, p["discount"]) - capex
    v_c = npv(annual * (1 - energy_loss_frac), life_c, p["discount"]) - capex
    # levelised cost of storage (capex only, per delivered kWh)
    lcos_b = capex / (E * p["fec_per_day"] * p["days_per_year"] * life_b * 0.85)
    lcos_c = capex / (E * p["fec_per_day"] * p["days_per_year"] * life_c * 0.85 * (1 - energy_loss_frac))
    co2_embodied = E * p["embodied_kgco2_per_kwh"]
    # embodied CO2 per year of service (replacement avoided)
    return dict(annual_value_usd=annual, capex_usd=capex, npv_fixed_usd=float(v_b), npv_control_usd=float(v_c),
                npv_gain_usd=float(v_c - v_b), lcos_fixed=float(lcos_b), lcos_control=float(lcos_c),
                embodied_tco2=co2_embodied / 1e3,
                embodied_tco2_per_service_year_fixed=co2_embodied / 1e3 / life_b,
                embodied_tco2_per_service_year_control=co2_embodied / 1e3 / life_c,
                avoided_embodied_tco2_over_30y=co2_embodied / 1e3 * (30 / life_b - 30 / life_c))

def hvac(p):
    """Air conditioning alternative: keep the cabinet interior at 25 C at the hot site (CoolProp-free Carnot-fraction COP)."""
    UA = P.WALL_AREA * 5.0
    days = np.arange(365)
    Tsite = p["T_site_mean"] + p["T_site_amp"] * np.sin(2 * np.pi * (days / 30.4 - 3) / 12)
    Tday = Tsite + 6.0      # daytime ambient above the daily mean (AA)
    gain_env = np.clip(UA * (Tday - 25.0), 0, None) * 12 * 3600 + np.clip(UA * (Tsite - 25.0), 0, None) * 12 * 3600
    gain_batt = (128 * P.Q_NORMAL) * (7200 + 8640 * 0.83 ** 2)
    Q = (gain_env + gain_batt).sum() / 3.6e6       # kWh thermal / year
    cp_file = os.path.join(RES, "coolprop_pvlib.json")
    if os.path.exists(cp_file):                    # CoolProp R-32 cycle COP at each day's daytime ambient
        c = json.load(open(cp_file))["ac_cop_R32"]; Ta_ = np.array([float(x) for x in c]); cop_ = np.array([c[x] for x in c])
        cop_d = np.interp(Tday, Ta_, cop_)
        kwh_e = float(((gain_env + gain_batt) / 3.6e6 / cop_d).sum()); cop = float(Q / kwh_e)
    else:
        Th = (Tday.mean() + 10) + 273.15; Tc = 15 + 273.15
        cop = min(0.45 * Tc / (Th - Tc), 4.5); kwh_e = Q / cop
    return dict(cooling_kwh_th=float(Q), cop=float(cop), electricity_kwh=float(kwh_e), cost_usd=float(kwh_e * 0.15),
                co2_t=float(kwh_e * p["grid_kgco2_per_kwh"] / 1e3), share_of_throughput_pct=float(100 * kwh_e / (60 * 365)))

if __name__ == "__main__":
    p = dict(BASE)
    lb, ub, Tb = simulate(p, False)
    lc, uc, Tcm = simulate(p, True)
    # cost of control: k_rot cells sit out phi of the discharge at constant current -> delivered energy loss
    loss = p["k_rot"] * p["phi"] / 128
    eco = economics(p, float(np.median(lb)), float(np.median(lc)), loss)
    ac = hvac(p)
    out = dict(params=p, life_fixed_years=dict(p10=float(np.percentile(lb, 10)), p50=float(np.median(lb)), p90=float(np.percentile(lb, 90))),
               life_control_years=dict(p10=float(np.percentile(lc, 10)), p50=float(np.median(lc)), p90=float(np.percentile(lc, 90))),
               energy_cost_of_rotation_pct=100 * loss, economics=eco, hvac_alternative=ac,
               usable_median_fixed=np.median(ub, 1)[::12].tolist(), usable_median_control=np.median(uc, 1)[::12].tolist(),
               Tmax_median_fixed=Tb[::12].tolist(), Tmax_median_control=Tcm[::12].tolist())
    # this cabinet: the same model with the backtest's five faults on their cells (see cabinet_faults)
    fl = cabinet_faults()
    lbf, _, _ = simulate(p, False, faults=fl); lcf, _, _ = simulate(p, True, faults=fl)
    n_ret = sum(f["retire_month"] is not None for f in fl)
    loss_f = loss + n_ret / 128                      # rotation plus the retired cells' share of the string
    out["cabinet_faults"] = dict(faults=fl, life_fixed_years=dict(p10=float(np.percentile(lbf, 10)), p50=float(np.median(lbf)), p90=float(np.percentile(lbf, 90))),
                                 life_control_years=dict(p10=float(np.percentile(lcf, 10)), p50=float(np.median(lcf)), p90=float(np.percentile(lcf, 90))),
                                 energy_cost_pct=100 * loss_f, economics=economics(p, float(np.median(lbf)), float(np.median(lcf)), loss_f))
    print("with this cabinet's faults: life fixed", out["cabinet_faults"]["life_fixed_years"], "control", out["cabinet_faults"]["life_control_years"],
          "npv gain", round(out["cabinet_faults"]["economics"]["npv_gain_usd"]))
    # sensitivity: one-at-a-time on the controlling assumptions
    sens = {}
    for k, vals in (("Ea", [20e3, 50e3]), ("fade_per_fec_25", [2.5e-5, 6e-5]), ("defect_r", [1.0, 3.0]), ("n_defect", [0, 3]),
                    ("cap_sigma", [0.005, 0.03]), ("T_site_mean", [18.0, 32.0]), ("g", [0.5, 3.0]), ("phi", [0.1, 0.5])):
        row = []
        for v in vals:
            q = dict(p); q[k] = v
            a_, _, _ = simulate(q, False, n_packs=150); b_, _, _ = simulate(q, True, n_packs=150)
            row.append(dict(value=v, life_fixed=float(np.median(a_)), life_control=float(np.median(b_)),
                            gain_years=float(np.median(b_) - np.median(a_))))
        sens[k] = row
    out["sensitivity"] = sens
    json.dump(out, open(os.path.join(RES, "econ.json"), "w"), indent=1)
    print("life fixed  :", out["life_fixed_years"]); print("life control:", out["life_control_years"])
    print("econ:", {k: round(v, 3) if isinstance(v, float) else v for k, v in eco.items()})
    print("HVAC:", {k: round(v, 2) for k, v in ac.items()})
    for k, r in sens.items():
        print(f"  {k:16s}", [(x['value'], round(x['life_fixed'], 1), round(x['life_control'], 1)) for x in r])
