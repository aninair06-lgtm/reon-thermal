#!/usr/bin/env python3
"""Deliverable 3: streamlines and airflow by module for the forced case (OpenFOAM A, SST).
Left: side view (y-z plane at mid width) with streamlines coloured by speed, modules grey.
Right: volumetric flow through each of the 9 cross-channels (bottom space, 7 gaps, top space)."""
import sys, os, json, re
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from of_post import read_field
sys.path.insert(0, "/mnt/c/Users/anina/Downloads/MITEC/reon_thermal/model")
import params as P
case = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/reon_runs/A_sst_m1")
t = sorted([d for d in os.listdir(case) if re.fullmatch(r"[0-9.]+", d) and d != "0"], key=float)[-1]
Ca, _ = read_field(f"{case}/{t}/air/C", vec=True); Ua, _ = read_field(f"{case}/{t}/air/U", vec=True); Ta, _ = read_field(f"{case}/{t}/air/T")
Cs, _ = read_field(f"{case}/{t}/cells/C", vec=True); Ts, _ = read_field(f"{case}/{t}/cells/T")
xs = np.unique(np.round(np.r_[Ca[:, 0], Cs[:, 0]], 6)); ys = np.unique(np.round(np.r_[Ca[:, 1], Cs[:, 1]], 6)); zs = np.unique(np.round(np.r_[Ca[:, 2], Cs[:, 2]], 6))
ix = lambda v, g: np.searchsorted(g, np.round(v, 6))
U = np.full((len(xs), len(ys), len(zs), 3), np.nan); T = np.full((len(xs), len(ys), len(zs)), np.nan); solid = np.zeros((len(xs), len(ys), len(zs)), bool)
U[ix(Ca[:, 0], xs), ix(Ca[:, 1], ys), ix(Ca[:, 2], zs)] = Ua
T[ix(Ca[:, 0], xs), ix(Ca[:, 1], ys), ix(Ca[:, 2], zs)] = Ta - 273.15
solid[ix(Cs[:, 0], xs), ix(Cs[:, 1], ys), ix(Cs[:, 2], zs)] = True
i = int(np.argmin(np.abs(xs - P.CAB_W / 2)))
uy, uz = U[i, :, :, 1].T, U[i, :, :, 2].T
yy = np.linspace(ys[0], ys[-1], 120); zz = np.linspace(zs[0], zs[-1], 400)
from scipy.interpolate import RegularGridInterpolator
def resamp(F):
    F = np.nan_to_num(F, nan=0.0)
    f = RegularGridInterpolator((zs, ys), F, bounds_error=False, fill_value=0.0)
    Z, Y = np.meshgrid(zz, yy, indexing="ij"); return f(np.c_[Z.ravel(), Y.ravel()]).reshape(Z.shape)
UY, UZ = resamp(uy), resamp(uz); SP = np.hypot(UY, UZ)
fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 8), gridspec_kw=dict(width_ratios=[1, 1.3]))
a1.streamplot(yy, zz, UY, UZ, color=SP, cmap="viridis", density=2.2, linewidth=0.7, arrowsize=0.6)
for m in range(1, 9):
    z0 = P.module_z0(m); a1.add_patch(plt.Rectangle((P.Y0, z0), P.CELL_Y, P.CELL_Z, color="0.55", zorder=3))
a1.set_aspect("equal"); a1.set_xlim(0, P.CAB_D); a1.set_ylim(0, P.CAB_H)
a1.set_xlabel("depth y, m (0 = front, inlet at bottom front)"); a1.set_ylabel("height z, m")
a1.set_title(f"Streamlines, mid-width section (x = {xs[i]:.2f} m)\ncolour = in-plane speed, grey = modules", fontsize=9)
sm = plt.cm.ScalarMappable(cmap="viridis", norm=plt.Normalize(0, SP.max())); fig.colorbar(sm, ax=a1, shrink=0.5, label="speed, m/s")
d = json.loads(open(f"/mnt/c/Users/anina/Downloads/MITEC/reon_thermal/results/openfoam/{os.path.basename(case)}.json").read().replace("NaN", "null"))
ch = np.array(d["channel_flow_m3s"]) * 1000
labels = ["under M01"] + [f"gap M{j:02d}-M{j+1:02d}" for j in range(1, 8)] + ["over M08"]
a2.barh(labels, ch, color=["#4c9be8" if v > 0 else "#e8704c" for v in ch]); a2.axvline(0, color="k", lw=0.6)
a2.set_xlabel("air through the channel, litres/s (front to back; negative = back to front)")
a2.set_title(f"Airflow by module, total supply {d['meta']['flow']*1000:.0f} L/s\nseven gaps together: {ch[1:8].sum():+.1f} L/s", fontsize=9)
for y, v in enumerate(ch): a2.text(v + (2 if v >= 0 else -2), y, f"{v:+.1f}", va="center", ha="left" if v >= 0 else "right", fontsize=7)
a2.invert_yaxis(); a2.set_xlim(min(-10, ch.min() * 1.3), ch.max() * 1.25)
fig.tight_layout()
out = f"/mnt/c/Users/anina/Downloads/MITEC/reon_thermal/results/figs/streamlines_airflow_{os.path.basename(case)}.png"
fig.savefig(out, dpi=150); print("wrote", out, "gap total L/s", ch[1:8].sum().round(2), "channels", ch.round(1))
