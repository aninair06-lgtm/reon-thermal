"""Remaining brief items: flow-regime numbers, cell-numbering figure, k_through sweep + layer-stack bound,
controller robustness (sensor noise/delay, hysteresis, dwell) + rotating / duty-cycle bypass, cell-balancing energy
recovery, Stage 4 on energy per year."""
import sys, os, json, itertools
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_cases import run_case, Controller
import params as P
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
J = lambda f: json.loads(open(os.path.join(R, f)).read().replace("NaN", "null"))
out = {}
# ---------------- 1. flow regime (justifies laminar vs k-omega SST) ----------------
nu, alpha, g = P.MU_AIR / P.RHO_AIR, 2.25e-5, 9.81
A = J("openfoam/A_sst_m1.json"); ch = np.array(A["channel_flow_m3s"])
def Re(Q, area, Dh): return (Q / area) * Dh / nu
fr = {}
fr["inlet grille"] = Re(0.15, P.CAB_W * 0.15, 2 * 0.15)
fr["bottom space under M01"] = Re(ch[0], P.CAB_W * P.Z_BOTTOM, 2 * P.Z_BOTTOM)
fr["rear plenum (top)"] = Re(ch[0] + ch[8] * 0 + ch[1:8].sum(), P.CAB_W * P.Y0, 2 * P.Y0)
fr["front plenum (to top space)"] = Re(ch[8], P.CAB_W * P.Y0, 2 * P.Y0)
fr["30 mm gap (largest |flow|)"] = Re(abs(ch[1:8]).max(), P.MOD_LEN * P.GAP_Z, 2 * P.GAP_Z)
dT = 5.0; beta = 1 / 313.0
Ra_H = g * beta * dT * P.CAB_H ** 3 / (nu * alpha); Ra_mod = g * beta * dT * P.CELL_Z ** 3 / (nu * alpha)
U_pl = ch[8] / (P.CAB_W * P.Y0)
Ri = g * beta * dT * P.CAB_H / U_pl ** 2
out["flow_regime"] = dict(Re={k: float(v) for k, v in fr.items()}, Ra_cabinet_height=float(Ra_H), Ra_module_face=float(Ra_mod),
                          Richardson_front_plenum=float(Ri), dT_assumed_K=dT,
                          verdict="forced: plenums Re 3,000-9,000 (transitional), gaps Re < 100 (laminar, buoyancy-dominated), Ri ~ 1 (mixed convection) -> run both laminar and k-omega SST and report the spread; sealed: Ra_H ~ 5e9 (transitional over the full height) but Ra < 1e7 on each module face -> laminar with gravity on")
print("flow regime:", {k: round(v) for k, v in fr.items()}, "Ra_H %.2e Ra_mod %.2e Ri %.2f" % (Ra_H, Ra_mod, Ri))
# ---------------- 2. numbering figure ----------------
fig, ax = plt.subplots(figsize=(11, 5.2))
for m in range(8):
    for c in range(16):
        ax.add_patch(plt.Rectangle((c, m * 1.25), 0.94, 1.0, fc="#f3e3d0", ec="#6a5640", lw=0.6))
        ax.text(c + 0.47, m * 1.25 + 0.5, P.cell_id(m + 1, c + 1).replace("_", "\n"), ha="center", va="center", fontsize=6.3, family="monospace")
for m in range(8): ax.text(-0.3, m * 1.25 + 0.5, f"module {m+1}", ha="right", va="center", fontsize=8)
ax.annotate("x: C01 at the left wall -> C16 at the right wall (seen from the front)", (0, -0.55), fontsize=8)
ax.annotate("module 1 at the bottom (z = 0.15 m), 30 mm gaps between modules", (0, 10.15), fontsize=8)
ax.set_xlim(-2.2, 16.2); ax.set_ylim(-0.9, 10.5); ax.axis("off")
ax.set_title("Cell numbering M01_C01 ... M08_C16 (front view, front panel removed)", fontsize=10)
fig.savefig(os.path.join(R, "figs", "cell_numbering.png"), dpi=150, bbox_inches="tight"); plt.close(fig)
# ---------------- 3. k_through sweep + layer-stack bound ----------------
layers = [  # (name, thickness um, k_low, k_high) through one repeat unit of a stacked Na-ion electrode assembly (AA, literature ranges)
    ("Al collector (cathode)", 15, 205, 237), ("cathode coating x2", 140, 0.7, 1.6), ("separator x2 (wetted)", 40, 0.2, 0.5),
    ("hard-carbon anode x2", 160, 1.0, 1.9), ("Al collector (anode)", 12, 205, 237)]
tt = np.array([l[1] for l in layers], float)
k_lo = tt.sum() / (tt / np.array([l[2] for l in layers])).sum(); k_hi = tt.sum() / (tt / np.array([l[3] for l in layers])).sum()
kin_lo = (tt * np.array([l[2] for l in layers])).sum() / tt.sum(); kin_hi = (tt * np.array([l[3] for l in layers])).sum() / tt.sum()
ks = {}
for kx in (0.5, 1.0, 2.0, 3.0):
    ks[str(kx)] = dict(C=run_case("k", "passive", 40.0, 5.0, extra=dict(kx=kx))["peak_interior_C"],
                       hot_start=run_case("k", "passive", 40.0, 5.0, T_init=55.0, extra=dict(kx=kx))["peak_interior_C"],
                       aged=run_case("k", "passive", 40.0, 5.0, aged=(6, 7), extra=dict(kx=kx))["peak_interior_C"])
out["k_through"] = dict(series_bound_W_mK=[float(k_lo), float(k_hi)], inplane_parallel_bound_W_mK=[float(kin_lo), float(kin_hi)], layers=layers, sweep=ks,
                        note="series rule through one repeat unit, electrolyte-wetted values; case walls and winding gaps would lower it further")
print("k_through series bound %.2f-%.2f, in-plane %.1f-%.1f" % (k_lo, k_hi, kin_lo, kin_hi), ks)
# ---------------- 4. controller robustness + rotating / duty-cycle bypass ----------------
class Rotating(Controller):
    """Every period, bypass the k hottest cells by MEASURED surface temperature (rotation emerges as they cool)."""
    def __init__(self, k=1, rot=300.0, **kw):
        super().__init__(n_max=k, **kw); self.k, self.rot, self.next = k, rot, 0.0
    def update(self, t, Ts):
        self.buf.append((t, Ts + self.rng.normal(0, self.noise, Ts.shape)))
        old = [b for b in self.buf if b[0] <= t - self.delay]
        if not old or t < self.next: return self.state
        meas = old[-1][1]; self.buf = [b for b in self.buf if b[0] > t - self.delay - 60]
        self.state = np.zeros((8, 16), bool); self.state.ravel()[np.argsort(meas.ravel())[::-1][:self.k]] = True
        self.next = t + self.rot; self.events.append((t, int(self.state.sum()))); return self.state
class Duty(Controller):
    """Duty-cycle ('current allocation' by bypass): the aged cell sits out a share of every 120 s."""
    def __init__(self, share=0.5, cell=(6, 7), **kw):
        super().__init__(**kw); self.share, self.cell = share, cell
    def update(self, t, Ts):
        self.state = np.zeros((8, 16), bool); self.state[self.cell] = (t % 120.0) < 120.0 * self.share; return self.state
rob = []
base = dict(mode="passive", T_amb=40.0, h_ext=5.0, T_init=55.0, aged=(6, 7), elec="current")
for noise, delay, Ton, dwell in itertools.product((0.0, 0.5, 2.0), (0.0, 30.0, 120.0), (55.0, 57.0), (60.0, 300.0, 900.0)):
    ctl = Controller(T_on=Ton, T_off=Ton - 3.0, n_max=4, dwell=dwell, delay=delay, noise=noise)
    r = run_case("ctl", controller=ctl, **base)
    rob.append(dict(noise_K=noise, delay_s=delay, T_on=Ton, dwell_s=dwell, peak_C=r["peak_interior_C"], energy_kWh=r["energy_delivered_kWh"],
                    switch_events=sum(1 for a, b in zip(ctl.events, ctl.events[1:]) if a[1] != b[1]), max_bypassed=r["n_bypassed_max"]))
pk = np.array([x["peak_C"] for x in rob])
out["controller_robustness"] = dict(case="hot start 55 C, aged cell, constant current, max 4 bypassed", n_runs=len(rob),
                                    peak_min=float(pk.min()), peak_max=float(pk.max()), runs=rob)
print("controller robustness: peak %.2f-%.2f C over %d runs" % (pk.min(), pk.max(), len(rob)))
rot = {}
for k in (1, 2, 4):
    for period in (60.0, 300.0):
        rot[f"rotate_k{k}_every{int(period)}s"] = run_case("rot", controller=Rotating(k=k, rot=period), **base)["peak_interior_C"]
for share in (0.25, 0.5, 0.75, 1.0):
    rot[f"duty_aged_{int(share*100)}pct"] = run_case("duty", controller=Duty(share=share, period=10.0), **base)["peak_interior_C"]
rot["fixed_bypass_aged"] = run_case("fix", bypass_ids=[P.cell_id(7, 8)], **base)["peak_interior_C"]
rot["no_bypass"] = run_case("none", **{k: v for k, v in base.items()})["peak_interior_C"]
out["rotating_and_duty"] = rot
print("rotating/duty:", {k: round(v, 2) for k, v in rot.items()})
# ---------------- 5. cell balancing: energy recovered by letting each cell run to its own end ----------------
E = J("econ.json")
uf, uc = np.array(E["usable_median_fixed"]), np.array(E["usable_median_control"])
bal = {f"year_{y}": dict(fixed_kWh=60 * float(uf[y]), control_kWh=60 * float(uc[y]), recovered_kWh=60 * float(uc[y] - uf[y]))
       for y in (0, 1, 3, 5) if y < len(uf)}
brief16 = dict(fixed_Ah=70.0, average_Ah=(15 * 85 + 70) / 16, sum_limited_Ah=None)
out["balancing"] = dict(per_year=bal, brief_16_cell_example=brief16,
                        note="fixed string: 128 x weakest cell; cell control: each cell runs to its own end while >= 115 cells remain (inverter voltage, assumed)")
print("balancing:", {k: round(v["recovered_kWh"], 2) for k, v in bal.items()})
# ---------------- 6. Stage 4 on energy per year ----------------
s4 = J("stage4.json"); hv = E["hvac_alternative"]
HOT_DAYS = 120   # days a year a hot-site cabinet starts a discharge hot (AA)
out["stage4_per_year"] = dict(hot_days=HOT_DAYS, ac_year_round_kWh=hv["electricity_kwh"],
                              ideas={r["idea"]: dict(peak_C=r["peak_C"], below_60=r["below_60"], kWh_per_year=r["extra_kWh_per_day"] * HOT_DAYS) for r in s4["ideas"]})
json.dump(out, open(os.path.join(R, "extras.json"), "w"), indent=1)
print("done")
