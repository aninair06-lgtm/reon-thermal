#!/usr/bin/env python3
"""Per-cell mean and max temperature histories (every 60 s) from a transient REON case -> results/openfoam/<case>_cells.json"""
import os, sys, json, glob
import numpy as np
sys.path.insert(0, "/mnt/c/Users/anina/Downloads/MITEC/reon_thermal/model")
import params as P
case = os.path.expanduser(sys.argv[1]); name = os.path.basename(case)
ids = [P.cell_id(m, c) for m in range(1, 9) for c in range(1, 17)]

def series(tag, cid):
    fs = sorted(glob.glob(f"{case}/postProcessing/cells/{tag}_{cid}/*/volFieldValue.dat"))
    rows = []
    for f in fs:
        for line in open(f):
            if line.startswith("#") or not line.strip(): continue
            a = line.split(); rows.append((float(a[0]), float(a[1]) - 273.15))
    rows.sort()
    t = np.array([r[0] for r in rows]); v = np.array([r[1] for r in rows])
    return t, v

grid = np.arange(0, 7200 + 1, 60.0)
Tm = np.zeros((len(grid), 128)); Tx = np.zeros((len(grid), 128))
tmax = 0
for j, cid in enumerate(ids):
    t, v = series("avg", cid); Tm[:, j] = np.interp(grid, np.r_[0, t], np.r_[v[0], v])
    t2, v2 = series("max", cid); Tx[:, j] = np.interp(grid, np.r_[0, t2], np.r_[v2[0], v2])
    tmax = max(tmax, t.max() if len(t) else 0)
last = int(np.searchsorted(grid, tmax, side="right") - 1)
Tm, Tx, grid = Tm[:last + 1], Tx[:last + 1], grid[:last + 1]
pk = Tx.max(0); i = int(pk.argmax())
heat = json.load(open(f"{case}/heat_map.json"))
out = dict(case=name, src="OpenFOAM 3D transient", t_s=grid.tolist(), T_mean=Tm.round(3).tolist(), T_max=Tx.round(3).tolist(),
           T_end_mean=Tm[-1].tolist(), T_end_max=Tx[-1].tolist(), peak=float(pk.max()), peakCell=ids[i],
           peak_time_s=float(grid[Tx[:, i].argmax()]), spread_end=float(Tm[-1].max() - Tm[-1].min()), t_end=float(grid[-1]),
           total_heat_W=float(sum(heat.values())), bypassed=[k for k, v in heat.items() if v == 0.0])
json.dump(out, open(f"/mnt/c/Users/anina/Downloads/MITEC/reon_thermal/results/openfoam/{name}_cells.json", "w"))
print(name, "t_end", grid[-1], "peak", round(out["peak"], 2), out["peakCell"], "spread_end", round(out["spread_end"], 2),
      "mean_end", round(float(Tm[-1].mean()), 2))
