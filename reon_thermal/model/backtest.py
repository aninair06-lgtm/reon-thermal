"""Backtest of the per-cell diagnostic bypass algorithm (flowchart supplied by the team) on the calibrated electro-thermal
cabinet model, over one simulated year at a hot site, against: no bypass (fixed string), 'bypass the hottest' and an
oracle that knows the true faults. Everything is synthetic: faults, ageing and BMS sensor noise are injected with known
ground truth so detection and outcomes can be scored. Sodium-ion cell, so the 'lithium plating' branch = sodium plating.

Physics per weekly representative 2 h discharge (30 kW constant power, sealed cabinet), coupled each 20 s step:
  R_ohm,i(T) = R0o,i * f_SOC * r_T(T, Ea_ohm) + contact_i            (contact part: tab / corrosion, ~no T dependence)
  R_pol,i(T) = R0p,i * (1 + sei_i + plating_i) * f_SOC * r_T(T, Ea_pol)
  heat_i = I^2 (R_ohm,i + R_pol,i) + extra_i (cooling fault);  OCV_i = OCV(SOC_i) + offset_i;  Q_i = capacity_i
Ageing per day (x7 per week): SEI ~ sqrt(t_eff) with t_eff += AF(T_cell) (Arrhenius 35 kJ/mol, assumed); capacity fade
tied to SEI; faults progress as stated in FAULTS.
"""
import sys, os, json, math, copy
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from network import Network
from run_cases import CAL
import params as P
import lit_params as L
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
RG = 8.314
NM, NC, N = 8, 16, 128
IDS = [P.cell_id(m + 1, c + 1) for m in range(NM) for c in range(NC)]
ix = lambda cid: (int(cid[1:3]) - 1, int(cid[5:7]) - 1)
EC = json.load(open(os.path.join(R, "ec_cases.json")))
R_REF = EC["R_ref_mOhm"] * 1e-3                    # total at 25 C, 50 % SOC (brief-matched)
CAP0 = EC["capacity_Ah"]
W_POL = L.W_POL
EA_OHM, EA_POL = L.EA_OHM, L.EA_POL
B_LOCAL = 0.62                                     # K per W of excess heat at end of 2 h (Elmer-calibrated)
K_MAX = 4                                          # simultaneous bypass slots at 30 kW (feasibility study)
N_MIN = 115
WEEKS = 52
DT = 20.0

# ---------------- injected faults (ground truth) ----------------
FAULTS = {
    "M03_C05": dict(kind="tab", week=10, contact=0.40, grow_in_service=0.01),        # +40 % of R0 ohmic, +1 %/week while carrying current
    "M05_C12": dict(kind="corrosion", week=5, rate=0.02),                             # +2 % of R0 per week, no T dependence
    "M02_C09": dict(kind="damage", week=20, ohm=0.30, cap=-0.10, ocv=-0.025),        # cracked electrode: ohmic step + capacity/OCV jump
    "M06_C03": dict(kind="plating", week=4, pol=0.35, cap=-0.04),                     # after the cold fast charge in week 4
    "M07_C08": dict(kind="cooling", week=26, extra_W=4.0),                            # blocked cooling: heat not explained by I^2 R
}
COLD_CHARGE_WEEK = 4                               # pack-wide cold (2 C) fast (1 C) charge logged that week
SAFETY = {"tab", "damage", "plating"}

def ambient(week):                                  # hot inland site, weekly mean daytime ambient
    return 24.0 + 12.0 * math.sin(2 * math.pi * (week - 13) / 52)

def r_T(T, ea):
    return np.exp(ea / RG * (1 / (np.asarray(T) + 273.15) - 1 / 298.15))

class Cabinet:
    def __init__(self, seed=0):
        rng = np.random.default_rng(seed)
        self.R0o = R_REF * (1 - W_POL) * np.exp(0.05 * rng.standard_normal((NM, NC)))
        self.R0p = R_REF * W_POL * np.exp(0.05 * rng.standard_normal((NM, NC)))
        self.cap = CAP0 * (1 + 0.015 * rng.standard_normal((NM, NC)))
        self.cap0 = self.cap.copy()
        self.contact = np.zeros((NM, NC)); self.plat = np.zeros((NM, NC)); self.ocv_off = np.zeros((NM, NC))
        self.ohm_x = np.zeros((NM, NC)); self.extra = np.zeros((NM, NC))
        self.t_eff = np.zeros((NM, NC)); self.sei = np.zeros((NM, NC))
        self.retired = np.zeros((NM, NC), bool)
        self.active_faults = {}
    def inject(self, week, in_service):
        for cid, f in FAULTS.items():
            m, c = ix(cid)
            if week == f["week"]:
                self.active_faults[cid] = f["kind"]
                if f["kind"] == "tab": self.contact[m, c] += f["contact"] * (self.R0o[m, c] + self.R0p[m, c])
                if f["kind"] == "damage":
                    self.ohm_x[m, c] += f["ohm"]; self.cap[m, c] *= 1 + f["cap"]; self.ocv_off[m, c] += f["ocv"]
                if f["kind"] == "plating": self.plat[m, c] += f["pol"]; self.cap[m, c] *= 1 + f["cap"]
                if f["kind"] == "cooling": self.extra[m, c] = f["extra_W"]
            if week > f["week"]:
                if f["kind"] == "tab" and in_service[m, c]: self.contact[m, c] += f["grow_in_service"] * (self.R0o[m, c] + self.R0p[m, c])
                if f["kind"] == "corrosion": self.contact[m, c] += f["rate"] * (self.R0o[m, c] + self.R0p[m, c])
    def resistances(self, T, soc):
        f = L.r_shape(soc)
        Ro = self.R0o * (1 + self.ohm_x) * f * r_T(T, EA_OHM) + self.contact
        Rp = self.R0p * (1 + self.sei + self.plat) * f * r_T(T, EA_POL)
        return Ro, Rp
    def age(self, T_mean_week, in_service_frac):
        # SEI: sqrt of Arrhenius-weighted time; cycling doubles the rate while in service (assumed)
        af = np.exp(35e3 / RG * (1 / 298.15 - 1 / (T_mean_week + 273.15)))
        self.t_eff += 7 * af * (0.5 + 0.5 * in_service_frac)
        sei_new = 0.022 * np.sqrt(self.t_eff)               # ~ +42 % on R_pol (+21 % total) after a year at 25 C
        dsei = sei_new - self.sei; self.sei = sei_new
        self.cap *= (1 - 0.25 * dsei)                       # capacity fade tied to SEI growth (assumed)
        self.ocv_off -= 0.02 * dsei                         # slow OCV-curve shift with SEI (assumed)

def discharge(cab, T_amb, bypass_fixed, allow_empty_bypass, hot_rule=None):
    """One 30 kW, 2 h discharge on the calibrated network. Returns per-cell traces for the BMS and outcome metrics."""
    T0 = T_amb + 3.0
    n = Network(B=1, mode="passive", T_amb=T_amb, h_ext=5.0, T_init=T0, **CAL["passive"])
    soc = np.ones((NM, NC)); byp = bypass_fixed.copy() | cab.retired
    E_out = 0.0; E_loss = 0.0; Tmax = np.full((NM, NC), -1e9); I = 0.0; stop = "2 h"; q_sum = np.zeros((NM, NC)); nq = 0
    Ro, Rp = cab.resistances(np.full((NM, NC), T0), soc)
    act = ~byp
    Voc = (L.ocv(soc) + cab.ocv_off)[act].sum(); Rpath = (Ro + Rp)[act].sum() + P.R_SWITCH * byp.sum()
    I0 = (Voc - math.sqrt(max(Voc ** 2 - 4 * Rpath * P.P_RATED_W, 0))) / (2 * Rpath)
    pulse = dict(T=np.full((NM, NC), T0), Ro=Ro.copy(), Rp=Rp.copy(), I=I0, ocv=L.ocv(np.ones((NM, NC))) + cab.ocv_off)
    while n.t < 7200 - 1e-9:
        T = np.asarray(n.Tc[0])
        if hot_rule is not None and abs(n.t % 600) < 1e-6:
            byp = byp | hot_rule(T, byp)
        Ro, Rp = cab.resistances(T, soc); Ri = Ro + Rp
        act = ~byp & (soc > 0)
        U = L.ocv(soc) + cab.ocv_off
        Voc = U[act].sum(); Rpath = Ri[act].sum() + P.R_SWITCH * (~act).sum()
        disc = Voc ** 2 - 4 * Rpath * P.P_RATED_W
        if disc <= 0 or act.sum() < N_MIN: stop = "power limit"; break
        I = (Voc - math.sqrt(disc)) / (2 * Rpath)
        Vt = U - I * Ri
        low = act & (Vt < L.V_MIN)
        if low.any():
            if allow_empty_bypass and act.sum() - low.sum() >= N_MIN:
                byp = byp | low; continue
            stop = "cell at cut-off"; break
        q = np.where(act, I ** 2 * Ri, I ** 2 * P.R_SWITCH) + cab.extra
        soc = soc - np.where(act, I, 0.0) * DT / (cab.cap * 3600)
        q_sum += q; nq += 1
        n.q_presc = q[None]; n.step(DT, record=True)
        E_out += P.P_RATED_W * DT; E_loss += float((I ** 2 * Ri)[act].sum() + I ** 2 * P.R_SWITCH * (~act).sum()) * DT
        Tmax = np.maximum(Tmax, np.asarray(n.rec["Tmax"][0]))
    T_end = np.asarray(n.Tc[0]); q_last = q_sum / max(nq, 1)      # discharge-average heat per cell (explains I^2R heating)
    return dict(E_kWh=E_out / 3.6e6, loss_kWh=E_loss / 3.6e6, runtime_h=n.t / 3600, stop=stop, Tmax=Tmax, T_end=T_end, q_last=q_last,
                T_mean=0.5 * (T0 + T_end), pulse=pulse, bypassed=byp)

# ---------------- BMS measurements (with sensor noise) ----------------
def measure(cab, d, rng):
    p = d["pulse"]
    Ro_m = p["Ro"] * (1 + 0.02 * rng.standard_normal((NM, NC)) / math.sqrt(10))     # 10 pulses averaged, 2 % each
    Rp_m = p["Rp"] * (1 + 0.04 * rng.standard_normal((NM, NC)) / math.sqrt(10))
    T_m = p["T"] + 0.5 * rng.standard_normal((NM, NC))
    return dict(Ro=Ro_m, Rp=Rp_m, T=T_m, T_end=d["T_end"] + 0.5 * rng.standard_normal((NM, NC)), q_last=d["q_last"],
                ocv_res=(p["ocv"] - L.ocv(np.ones((NM, NC)))) + 0.003 * rng.standard_normal((NM, NC)),
                soh=cab.cap / cab.cap0 * (1 + 0.01 * rng.standard_normal((NM, NC))))

# ---------------- the team's diagnostic flowchart ----------------
TH_EXCESS, TH_EA, TH_R2, TH_T = 0.15, 0.40, 0.8, 2.0
class Diagnoser:
    def __init__(self, base_Ro, base_Rp):
        self.bo, self.bp = base_Ro, base_Rp           # each cell's own early-life R at 25 C, 50 % SOC  [BASELINE]
        self.hist = []                                 # weekly measurements
    def correct(self, meas):                           # step 2  [BASELINE: Ea and R-SOC map]
        f = L.r_shape(1.0)
        return meas["Ro"] / (f * r_T(meas["T"], EA_OHM)), meas["Rp"] / (f * r_T(meas["T"], EA_POL))
    def classify(self, week, meas, charge_log):
        Ro_c, Rp_c = self.correct(meas)
        base = self.bo + self.bp
        raw = (meas["Ro"] + meas["Rp"]) / base - 1                          # step 3  [BASELINE: own R0]
        cor = (Ro_c + Rp_c) / base - 1
        self.hist.append(dict(week=week, Ro_c=Ro_c, Rp_c=Rp_c, raw=raw, cor=cor, T=meas["T"], Ro=meas["Ro"], Rp=meas["Rp"],
                              ocv=meas["ocv_res"], soh=meas["soh"]))
        Tpack = np.median(meas["T_end"])
        dT_expl = B_LOCAL * (meas["q_last"] - np.median(meas["q_last"]))
        out = np.empty((NM, NC), dtype=object); info = {}
        H = self.hist
        for m in range(NM):
            for c in range(NC):
                cid = IDS[m * NC + c]
                r_, c_ = raw[m, c], cor[m, c]
                if abs(r_) < TH_EXCESS and abs(c_) < TH_EXCESS: out[m, c] = "healthy"; continue
                tracks = abs(meas["T_end"][m, c] - Tpack - dT_expl[m, c]) < TH_T
                if abs(c_) < TH_EXCESS and tracks: out[m, c] = "temp_effect"; continue
                if meas["T_end"][m, c] - Tpack - dT_expl[m, c] > TH_T: out[m, c] = "cooling"; continue
                # rise after a cold fast charge (charge log within the last 2 weeks) and a rise vs before it
                cold = any(w >= week - 2 and e["T_min"] < 5 and e["C_rate"] > 0.5 for w, e in charge_log)
                prev = [h for h in H if h["week"] < week - 2]
                rose = prev and (Rp_c[m, c] - prev[-1]["Rp_c"][m, c]) / self.bp[m, c] > 0.10
                if cold and rose: out[m, c] = "plating"; continue
                if len(H) >= 2:
                    dRo = (H[-1]["Ro_c"][m, c] - H[-2]["Ro_c"][m, c]) / self.bo[m, c]
                    nb = [H[-1]["Ro_c"][m, k] - H[-2]["Ro_c"][m, k] for k in range(NC) if k != c]
                    nb_step = np.median(np.abs(nb)) / self.bo[m, c]
                    d_ocv = abs(H[-1]["ocv"][m, c] - H[-2]["ocv"][m, c]); d_soh = H[-2]["soh"][m, c] - H[-1]["soh"][m, c]
                    if dRo > 0.10 and nb_step < 0.05:
                        out[m, c] = "damage" if (d_ocv > 0.015 or d_soh > 0.03) else "tab"; continue
                # weak temperature dependence of the excess (Ea of the excess < 40 % of baseline), OCV normal
                if len(H) >= 6:
                    Ts = np.array([h["T"][m, c] for h in H[-12:]]); ex = np.array([h["Ro"][m, c] + h["Rp"][m, c] for h in H[-12:]])
                    base_T = (self.bo[m, c] * r_T(Ts, EA_OHM) + self.bp[m, c] * r_T(Ts, EA_POL)) * L.r_shape(1.0)
                    exc = ex - base_T
                    if (exc > 0).all() and np.ptp(Ts) > 3:
                        x = 1 / (Ts + 273.15); A = np.c_[np.ones_like(x), x]
                        slope = np.linalg.lstsq(A, np.log(exc), rcond=None)[0][1]
                        ea_ex = slope * RG
                        ea_base = (W_POL * EA_POL + (1 - W_POL) * EA_OHM)
                        info[cid] = ea_ex
                        if ea_ex < TH_EA * ea_base and abs(H[-1]["ocv"][m, c]) < 0.015: out[m, c] = "corrosion"; continue
                # slow component grows with sqrt(time), across all cells, OCV shifts
                if len(H) >= 8:
                    wk = np.array([h["week"] for h in H]); y = np.array([h["Rp_c"][m, c] / self.bp[m, c] - 1 for h in H])
                    A = np.c_[np.ones_like(wk), np.sqrt(wk)]; coef, *_ = np.linalg.lstsq(A, y, rcond=None)
                    pred = A @ coef; r2 = 1 - ((y - pred) ** 2).sum() / max(((y - y.mean()) ** 2).sum(), 1e-12)
                    pack = np.array([np.median(h["Rp_c"] / self.bp - 1) for h in H])
                    pack_up = pack[-1] - pack[0] > 0.05
                    if coef[1] > 0 and r2 > TH_R2 and pack_up: out[m, c] = "sei"; continue
                out[m, c] = "ambiguous"
        return out, raw, cor

# ---------------- bypass policy from the diagnosis ----------------
PRIORITY = {"damage": 6, "plating": 5, "tab": 4, "cooling": 3, "corrosion": 2, "sei": 1}
def policy(labels, cor, T_amb):
    """Safety faults out permanently (retire); cooling and corrosion out while slots allow; SEI cells with the largest
    excess rest in hot weeks (ageing equalisation). Max K_MAX simultaneous bypasses."""
    cand = []
    for m in range(NM):
        for c in range(NC):
            lab = labels[m, c]
            if lab in ("damage", "plating", "tab"): cand.append((PRIORITY[lab], cor[m, c], (m, c), True))
            elif lab == "cooling": cand.append((PRIORITY[lab], cor[m, c], (m, c), False))
            elif lab == "corrosion" and cor[m, c] > 0.30: cand.append((PRIORITY[lab], cor[m, c], (m, c), False))
            elif lab == "sei" and cor[m, c] > 0.25 and T_amb > 28: cand.append((PRIORITY[lab], cor[m, c], (m, c), False))
    cand.sort(key=lambda x: (-x[0], -x[1]))
    byp = np.zeros((NM, NC), bool); retire = []
    for pr, _, mc, perm in cand[:K_MAX]:
        byp[mc] = True
        if perm: retire.append(mc)
    return byp, retire

def truth_labels(cab, week, raw_true, cor_true, T_end, q_last):
    lab = np.full((NM, NC), "healthy", dtype=object)
    sei_tot = cab.sei * W_POL
    for m in range(NM):
        for c in range(NC):
            if abs(raw_true[m, c]) >= TH_EXCESS and abs(cor_true[m, c]) < TH_EXCESS: lab[m, c] = "temp_effect"
            if sei_tot[m, c] >= TH_EXCESS: lab[m, c] = "sei"
    for cid, kind in cab.active_faults.items():
        lab[ix(cid)] = kind
    return lab

def run_strategy(name, seed=7):
    rng = np.random.default_rng(seed)
    cab = Cabinet(seed=1)
    dia = Diagnoser(cab.R0o.copy(), cab.R0p.copy())
    weekly = []; log = []; risk_days = 0.0; first_detect = {}; wrong_bypass_weeks = 0
    byp_plan = np.zeros((NM, NC), bool); charge_log = []
    conf = {}
    for week in range(WEEKS):
        T_amb = ambient(week)
        in_service = ~(byp_plan | cab.retired)
        cab.inject(week, in_service)
        if week == COLD_CHARGE_WEEK: charge_log.append((week, dict(T_min=2.0, C_rate=1.0)))
        hot_rule = None
        if name == "hottest":
            def hot_rule(T, byp_now):
                extra = np.zeros((NM, NC), bool); free = K_MAX - int(byp_now.sum())
                if free > 0:
                    order = np.argsort(np.where(byp_now, -1e9, T).ravel())[::-1][:free]
                    for i in order:
                        if T.ravel()[i] > 50.0: extra.ravel()[i] = True
                return extra
        d = discharge(cab, T_amb, byp_plan if name in ("algo", "oracle") else np.zeros((NM, NC), bool),
                      allow_empty_bypass=(name != "none"), hot_rule=hot_rule)
        meas = measure(cab, d, rng)
        labels, raw, cor = dia.classify(week, meas, charge_log)
        # ground truth with noise-free quantities
        base = dia.bo + dia.bp
        Ro_t, Rp_t = d["pulse"]["Ro"], d["pulse"]["Rp"]
        f = L.r_shape(1.0)
        raw_t = (Ro_t + Rp_t) / base - 1; cor_t = (Ro_t / (f * r_T(d["pulse"]["T"], EA_OHM)) + Rp_t / (f * r_T(d["pulse"]["T"], EA_POL))) / base - 1
        truth = truth_labels(cab, week, raw_t, cor_t, d["T_end"], d["q_last"])
        for m in range(NM):
            for c in range(NC):
                key = (truth[m, c], labels[m, c]); conf[key] = conf.get(key, 0) + 1
        for cid, kind in cab.active_faults.items():
            if cid not in first_detect and labels[ix(cid)] == kind: first_detect[cid] = week - FAULTS[cid]["week"]
        # decide next week's bypass set
        if name == "algo":
            byp_plan, retire = policy(labels, cor, ambient(week + 1))
        elif name == "oracle":
            byp_plan, retire = policy(truth, cor_t, ambient(week + 1))
        else:
            byp_plan, retire = np.zeros((NM, NC), bool), []
        for mc in retire: cab.retired[mc] = True
        # safety exposure: days a cell with a safety fault carried current
        for cid, kind in cab.active_faults.items():
            if kind in SAFETY and not d["bypassed"][ix(cid)]: risk_days += 7
        healthy_byp = sum(1 for m in range(NM) for c in range(NC) if d["bypassed"][m, c] and truth[m, c] in ("healthy", "temp_effect"))
        wrong_bypass_weeks += healthy_byp
        in_frac = (~d["bypassed"]).astype(float)
        cab.age(d["T_mean"], in_frac)
        weekly.append(dict(week=week, T_amb=T_amb, E_kWh=d["E_kWh"], loss_kWh=d["loss_kWh"], runtime_h=d["runtime_h"], stop=d["stop"],
                           Tmax=float(d["Tmax"].max()), n_bypassed=int(d["bypassed"].sum()),
                           labels={k: int((labels == k).sum()) for k in ("healthy", "temp_effect", "cooling", "plating", "damage", "tab", "corrosion", "sei", "ambiguous")}))
    # lifetime projection from end-of-year state
    soh = cab.cap / cab.cap0
    usable_fixed = float(soh.min())
    alive = ~cab.retired
    caps = np.sort(soh[alive])[::-1]
    cstar = caps[N_MIN - 1] if len(caps) >= N_MIN else 0.0
    usable_ctrl = float(np.minimum(soh[alive], cstar).sum() / N)
    E = np.array([w["E_kWh"] for w in weekly]); Lk = np.array([w["loss_kWh"] for w in weekly])
    return dict(strategy=name, energy_MWh_year=float(E.sum() * 7 / 1000), loss_kWh_year=float(Lk.sum() * 7),
                efficiency_pct=float(100 * E.sum() / (E.sum() + Lk.sum())), mean_runtime_h=float(np.mean([w["runtime_h"] for w in weekly])),
                Tmax_year=float(max(w["Tmax"] for w in weekly)), weeks_above_55=int(sum(w["Tmax"] > 55 for w in weekly)),
                weeks_above_60=int(sum(w["Tmax"] > 60 for w in weekly)), safety_risk_cell_days=risk_days,
                healthy_cell_bypass_weeks=wrong_bypass_weeks, detection_delay_weeks=first_detect,
                soh_min=float(soh.min()), soh_mean=float(soh.mean()), retired=[IDS[i] for i in np.flatnonzero(cab.retired.ravel())],
                usable_fixed_string=usable_fixed, usable_cell_control=usable_ctrl,
                confusion={f"{a}->{b}": v for (a, b), v in sorted(conf.items())}, weekly=weekly)

if __name__ == "__main__":
    import time
    t0 = time.time(); out = {}
    for s in ("none", "hottest", "algo", "oracle"):
        out[s] = run_strategy(s)
        r = out[s]
        print(f"{s:8s} E {r['energy_MWh_year']:.2f} MWh/yr  loss {r['loss_kWh_year']:.0f} kWh  eff {r['efficiency_pct']:.2f}%  Tmax {r['Tmax_year']:.1f} C  "
              f"wk>55 {r['weeks_above_55']}  risk {r['safety_risk_cell_days']:.0f} cell-days  healthy-bypass {r['healthy_cell_bypass_weeks']}  "
              f"SOHmin {r['soh_min']:.3f} usable fixed {r['usable_fixed_string']:.3f} ctrl {r['usable_cell_control']:.3f}  detect {r['detection_delay_weeks']}  ({time.time()-t0:.0f}s)")
    json.dump(out, open(os.path.join(R, "backtest.json"), "w"), indent=1, default=str)
