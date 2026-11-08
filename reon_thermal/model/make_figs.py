"""Brief deliverable 3: technical figures on a fixed 20-70 C scale (values outside annotated)."""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
O = os.path.join(R, "figs"); os.makedirs(O, exist_ok=True)
J = lambda f: json.load(open(os.path.join(R, f)))
H = J("network_histories.json"); TM = J("network_Tmax_cell.json"); G = J("gpu_studies.json")
VMIN, VMAX = 20, 70
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})

def heat(ax, T, title):
    T = np.array(T).reshape(8, 16)
    im = ax.imshow(T, origin="lower", cmap="inferno", vmin=VMIN, vmax=VMAX, aspect="auto")
    ax.set_title(title, fontsize=9); ax.set_xticks(range(0, 16, 3)); ax.set_xticklabels([f"C{i+1:02d}" for i in range(0, 16, 3)])
    ax.set_yticks(range(8)); ax.set_yticklabels([f"M{i+1:02d}" for i in range(8)])
    i = np.unravel_index(T.argmax(), T.shape); ax.plot(i[1], i[0], "wo", ms=4, mfc="none")
    out = (T < VMIN).sum() + (T > VMAX).sum()
    ax.text(0.99, -0.16, f"max {T.max():.1f} C ({'M%02d_C%02d' % (i[0]+1, i[1]+1)}), min {T.min():.1f} C" + (f", {out} cells off-scale" if out else ""),
            transform=ax.transAxes, ha="right", fontsize=7)
    return im

# 1. heatmaps: A (3D steady) vs C (network & 3D), C vs D
A = J("openfoam/A_sst_m1.json"); AT = [c["T_volume_mean_C"] for c in A["cells"]]
panels = [(AT, "A forced, 3D SST steady (mean)"), (TM["C_passive40"], "C sealed 40 C, network, peak over 2 h")]
for nm, lab in (("Ct_lam_m1", "C sealed 40 C, 3D transient, end (max)"), ("Dt_lam_m1", "D = C + 13 bypassed, 3D, end (max)")):
    p = os.path.join(R, "openfoam", f"{nm}_cells.json")
    if os.path.exists(p): panels.append((json.load(open(p))["T_end_max"], lab))
panels.append((TM["D_fixed13_power"], "D network, 13 bypassed, constant power"))
panels.append((TM["E_aged_C"], "C + one aged cell (3x R), network"))
fig, axs = plt.subplots(len(panels) // 2 + len(panels) % 2, 2, figsize=(9, 2.9 * (len(panels) // 2 + len(panels) % 2)))
fig.subplots_adjust(hspace=0.7, wspace=0.25)
for ax, (T, t) in zip(axs.ravel(), panels): im = heat(ax, T, t)
for ax in axs.ravel()[len(panels):]: ax.axis("off")
fig.colorbar(im, ax=axs, shrink=0.6, label="cell interior T, C (fixed 20-70)")
fig.savefig(os.path.join(O, "heatmaps_8x16.png"), dpi=160, bbox_inches="tight"); plt.close(fig)

# 2. peak and spread histories + bypass timeline
fig, (a1, a2, a3) = plt.subplots(3, 1, figsize=(8, 7.5), sharex=True)
for k in ("B_passive25", "C_passive40", "D_fixed13_power", "H_hotstart", "H_adaptive_power", "H_derate_90", "E_aged_C", "E_aged_C_bypass1_current"):
    h = np.array(H[k]); a1.plot(h[:, 0] / 60, h[:, 1], label=k); a2.plot(h[:, 0] / 60, h[:, 2], label=k)
a1.axhline(60, color="r", lw=0.8, ls="--"); a1.set_ylim(VMIN, VMAX); a1.set_ylabel("peak interior T, C"); a1.legend(fontsize=6, ncol=2)
a2.set_ylabel("cell spread (max-min mean T), K")
for k in ("D_adaptive_power", "H_adaptive_power", "H_adaptive_current", "E_aged_hot_adaptive"):
    h = np.array(H[k]); a3.step(h[:, 0] / 60, h[:, 4], where="post", label=k)
a3.set_ylabel("cells bypassed"); a3.set_xlabel("time, min"); a3.legend(fontsize=7)
fig.savefig(os.path.join(O, "histories_and_bypass_timeline.png"), dpi=160, bbox_inches="tight"); plt.close(fig)

# 3. peak temperature vs delivered energy and power
C = J("network_cases.json"); fe = J("feasibility.json")
fig, ax = plt.subplots(figsize=(6.5, 4))
for k, v in C.items():
    if isinstance(v, dict) and "peak_interior_C" in v and k.startswith(("H_", "C_", "D_", "E_")) and "DAY" not in k:
        ax.scatter(v["energy_delivered_kWh"], v["peak_interior_C"], s=14); ax.annotate(k, (v["energy_delivered_kWh"], v["peak_interior_C"]), fontsize=5)
ax.axhline(60, color="r", lw=0.8, ls="--"); ax.set_xlabel("energy delivered in the 2 h window, kWh (prescribed-heat bookkeeping)"); ax.set_ylabel("peak interior T, C")
fig.savefig(os.path.join(O, "temperature_vs_energy.png"), dpi=160, bbox_inches="tight"); plt.close(fig)

# 4. sensitivity ranking + Shapley
sb = G["sobol"]; order = np.argsort(sb["peak"]["ST"])
fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.6))
a1.barh(np.array(sb["names"])[order], np.array(sb["peak"]["ST"])[order], xerr=np.array(sb["peak"]["ST_conf"])[order], color="#d97a2b")
a1.set_xlabel("Sobol total index, peak interior T (hot start)"); a1.set_title(f"{sb['n_runs']} GPU runs; ranges not probabilities", fontsize=8)
sh = G["shapley"]; o2 = np.argsort(sh["shapley_K"])
a2.barh(np.array(sh["names"])[o2], np.array(sh["shapley_K"])[o2], color="#7a5cff"); a2.set_xlabel("Shapley share of the rise at M07_C08, K")
a2.set_title(f"total {sh['total_rise_K']:.1f} K above 25 C (256 combinations)", fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(O, "sensitivity_and_attribution.png"), dpi=160, bbox_inches="tight"); plt.close(fig)
print("figures in", O, os.listdir(O))
