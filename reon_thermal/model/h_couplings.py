"""Deliverable 2: per-cell cell-to-air couplings H_i = Q_cell_to_air / (T_exposed_surface_mean - T_air_reference) [W/K].

3D (OpenFOAM case A, k-omega SST, steady, full power):
  numerator   Q_cell_to_air  = air-side wallHeatFlux integrated over the cell's exposed faces (convection only: no radiation in 3D)
  denominator T_surface_mean = area-weighted face temperature of the exposed faces
              T_air_reference = CHANNEL BULK: mean of all air cells in the adjacent gap / bottom / top space over the cell's
                                footprint (top and bottom faces), across the plenum depth over the face (front and rear),
                                and the side clearance (end cells), each weighted by the face area it serves
  paths       heat_to_neighbours = generation - heat_to_air (steady state; there are no supports or radiation in the 3D model)
  flag        |dT| < 0.3 K -> H unreliable
Network (same case, calibrated, pseudo-steady): the same definition from its own conductances, plus its radiation and
support paths, so the two can be compared cell by cell.
"""
import json, os, sys, csv
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from network import Network
from run_cases import CAL
import params as P
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
L = lambda f: json.loads(open(os.path.join(R, f)).read().replace("NaN", "null"))

out_rows = []
for case in ("A_sst_m1", "A_sst_m15"):
    p = os.path.join(R, "openfoam", f"{case}.json")
    if not os.path.exists(p): continue
    d = L(f"openfoam/{case}.json")
    for c in d["cells"]:
        dT = c["T_surface_mean_C"] - c["T_air_reference_C"]
        out_rows.append(dict(source=f"OpenFOAM {case}", cell_id=c["cell_id"], module_id=c["module_id"], Q_cell_to_air_W=c["heat_to_air_W"],
                             T_surface_mean_C=c["T_surface_mean_C"], T_air_reference_C=c["T_air_reference_C"], dT_K=dT,
                             H_W_per_K=c["heat_to_air_W"] / dT if abs(dT) > 0.05 else None, flag_small_dT=abs(dT) < 0.3,
                             Q_convection_W=c["heat_to_air_W"], Q_radiation_W=0.0, Q_neighbours_W=c["heat_to_neighbours_W"], Q_supports_W=0.0,
                             exposed_area_m2=c["exposed_area_m2"]))
# network, same boundary conditions, calibrated, pseudo-steady (capacity scaled), radiation on
A = L("openfoam/A_sst_m1.json")
net = Network(B=1, mode="forced", T_amb=25.0, T_supply=20.0, h_ext=5.0, flow=0.15, cap_scale=0.03, T_init=40.0, **CAL["forced"])
while net.t < 9000: net.step(4.0, record=True)
r = {k: np.asarray(v[0]) for k, v in net.rec.items()}
for m in range(8):
    for c in range(16):
        dT = r["Tsurf"][m, c] - r["Tair"][m, c]
        out_rows.append(dict(source="network (calibrated)", cell_id=P.cell_id(m + 1, c + 1), module_id=m + 1, Q_cell_to_air_W=float(r["Qair"][m, c]),
                             T_surface_mean_C=float(r["Tsurf"][m, c]), T_air_reference_C=float(r["Tair"][m, c]), dT_K=float(dT),
                             H_W_per_K=float(r["Qair"][m, c] / dT) if abs(dT) > 0.05 else None, flag_small_dT=bool(abs(dT) < 0.3),
                             Q_convection_W=float(r["Qair"][m, c]), Q_radiation_W=float(r["Qrad_out"][m, c]), Q_neighbours_W=float(r["Qnb"][m, c]),
                             Q_supports_W=float(r["Qsup"][m, c]), exposed_area_m2=None))
with open(os.path.join(R, "H_couplings_A.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys())); w.writeheader(); w.writerows(out_rows)
summ = {}
for src in sorted(set(x["source"] for x in out_rows)):
    rows = [x for x in out_rows if x["source"] == src]
    H = np.array([x["H_W_per_K"] for x in rows if x["H_W_per_K"] is not None and not x["flag_small_dT"]])
    byM = {m: float(np.median([x["H_W_per_K"] for x in rows if x["module_id"] == m and x["H_W_per_K"] is not None and not x["flag_small_dT"]] or [np.nan])) for m in range(1, 9)}
    summ[src] = dict(H_median=float(np.median(H)), H_p10=float(np.percentile(H, 10)), H_p90=float(np.percentile(H, 90)), n_flagged=int(sum(x["flag_small_dT"] for x in rows)),
                     H_median_by_module=byM, Q_air_total_W=float(sum(x["Q_cell_to_air_W"] for x in rows)),
                     Q_rad_total_W=float(sum(x["Q_radiation_W"] for x in rows)), Q_sup_total_W=float(sum(x["Q_supports_W"] for x in rows)))
json.dump(summ, open(os.path.join(R, "H_couplings_summary.json"), "w"), indent=1)
for k, v in summ.items():
    print(k, {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in v.items() if kk != "H_median_by_module"})
    print("   by module:", {m: round(h, 3) for m, h in v["H_median_by_module"].items()})
