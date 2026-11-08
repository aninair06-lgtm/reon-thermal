"""Three-grid convergence study (Celik et al. 2008, J. Fluids Eng. 130:078001) for the forced steady case A (k-omega SST).
Grids: A_sst_m15 (fine), A_sst_m1 (medium), A_sst_m067 (coarse). h = (V_total / N)^(1/3)."""
import json, math, os
R = "/mnt/c/Users/anina/Downloads/MITEC/reon_thermal/results/openfoam"
L = lambda n: json.loads(open(f"{R}/{n}.json").read().replace("NaN", "null"))
g = [L("A_sst_m15"), L("A_sst_m1"), L("A_sst_m067")]
V = 1.30 * 0.40 * 2.35
h = [(V / x["meta"]["ncells"]) ** (1 / 3) for x in g]
def gci(phi):
    f1, f2, f3 = phi
    r21, r32 = h[1] / h[0], h[2] / h[1]
    e21, e32 = f2 - f1, f3 - f2
    if e21 == 0 or e32 == 0:
        return dict(phi=phi, note="no change between grids")
    s = math.copysign(1, e32 / e21)
    p = 2.0
    for _ in range(200):
        q = math.log((r21 ** p - s) / (r32 ** p - s))
        p_new = abs(math.log(abs(e32 / e21)) + q) / math.log(r21)
        if abs(p_new - p) < 1e-9: break
        p = p_new
    ext = (r21 ** p * f1 - f2) / (r21 ** p - 1)
    ea = abs((f1 - f2) / f1)
    g21 = 1.25 * ea / (r21 ** p - 1)
    monotone = s > 0
    return dict(phi_fine=f1, phi_medium=f2, phi_coarse=f3, r21=r21, r32=r32, apparent_order=p, extrapolated=ext,
                gci_fine_pct=100 * g21, band=[f1 * (1 - g21), f1 * (1 + g21)], monotone=monotone,
                change_fine_medium=f1 - f2, change_medium_coarse=f2 - f3)
out = dict(cells=[x["meta"]["ncells"] for x in g], h_m=h,
           peak_interior_C=gci([x["summary"]["T_int_max"] for x in g]),
           mean_cell_C=gci([x["summary"]["T_mean_avg"] for x in g]),
           hottest=[x["summary"]["hottest"] for x in g],
           gap_share_pct=[100 * sum(x["summary"]["channel_share"][1:8]) for x in g],
           side_share=[x["summary"]["side_share"] for x in g])
json.dump(out, open(f"{R}/gci_A_sst.json", "w"), indent=1)
print(json.dumps(out, indent=1))
