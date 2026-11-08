"""Elmer module runs: grid convergence (3 meshes), time-step halving, aged vs bypassed, and the network's
16-node module model under identical boundary conditions (h=3 W/m2K to 40 C air, start 40 C, 7200 s)."""
import sys, os, glob, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from read_vtu import read_vtu, cell_stats
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "model"))
import params as P
E = os.path.expanduser("~/reon_runs/elmer")
OUT = "/mnt/c/Users/anina/Downloads/MITEC/reon_thermal/results"

def series(name):
    files = sorted(glob.glob(f"{E}/{name}/results/case_t*.vtu"), key=lambda f: int(f.split("_t")[-1].split(".")[0]))
    meta = json.load(open(f"{E}/{name}/meta.json"))
    every = max(1, int(round(600 / meta["dt"])))
    t = np.array([int(f.split("_t")[-1].split(".")[0]) for f in files]) * meta["dt"]
    st = np.array([cell_stats(*read_vtu(f)) for f in files])   # [nt,16,2]
    return t, st

def mini_network(q, h=3.0, Tair=40.0, T0=40.0, kx=1.0, tend=7200, dt=10.0, beta=1.0, gamma=0.5):
    A_tb, A_fr, A_sd = P.CELL_X * P.CELL_Y, P.CELL_X * P.CELL_Z, P.CELL_Y * P.CELL_Z
    Rz = (P.CELL_Z / 2) / (3 * 25 * A_tb); Ry = (P.CELL_Y / 2) / (3 * 25 * A_fr); Rx = (P.CELL_X / 2) / (3 * kx * A_sd)
    Gface = 2 / (1 / (h * A_tb) + Rz) + 2 / (1 / (h * A_fr) + Ry)
    Gend = 1 / (1 / (h * A_sd) + Rx + P.R_CONTACT / A_sd * 0)
    Gcc = A_sd / (beta * P.CELL_X / kx + P.R_CONTACT)
    T = np.full(16, T0); hist = []
    LYH, LZH = P.CELL_Y / 2, P.CELL_Z / 2
    for k in range(int(tend / dt)):
        Q = q - Gface * (T - Tair)
        Q[0] -= Gend * (T[0] - Tair); Q[-1] -= Gend * (T[-1] - Tair)
        f = Gcc * (T[1:] - T[:-1]); Q[:-1] += f; Q[1:] -= f
        T = T + Q * dt / P.C_CELL
        if (k + 1) * dt % 600 == 0:
            qv = q / P.CELL_VOL
            dTgen = qv / (6 * (25 / LZH ** 2 + 25 / LYH ** 2))
            Qnb = np.zeros(16); Qnb[:-1] -= f; Qnb[1:] += f
            hist.append(np.c_[T, T + dTgen + np.abs(Qnb) * (P.CELL_X / 2 / (kx * A_sd)) * gamma])
    return np.array(hist)

res = {}
runs = {}
for nm in ("mod_aged_r1", "mod_aged_r15", "mod_aged_r2", "mod_aged_r1_dt30", "mod_byp_r1"):
    if os.path.isdir(f"{E}/{nm}"):
        runs[nm] = series(nm)
        t, st = runs[nm]
        res[nm] = dict(t_s=t.tolist(), peak_internal_C=float(st[..., 1].max()), peak_time_s=float(t[st[..., 1].max(1).argmax()]),
                       aged_cell_mean_end_C=float(st[-1, 7, 0]), neighbour_mean_end_C=float(st[-1, 6, 0]),
                       far_cell_mean_end_C=float(st[-1, 2, 0]), cell_mean_end=st[-1, :, 0].tolist(), cell_max_end=st[-1, :, 1].tolist())
        print(f"{nm:18s} peak Tint {res[nm]['peak_internal_C']:.3f} C @ {res[nm]['peak_time_s']:.0f}s | aged {res[nm]['aged_cell_mean_end_C']:.2f}, "
              f"neighbour {res[nm]['neighbour_mean_end_C']:.2f}, far {res[nm]['far_cell_mean_end_C']:.2f}")
# grid convergence (three meshes, ratio 1.5 and 2 -> use r1, r15, r2 ; refinement factor not constant, use generalized Richardson on r15/r2 pair)
p1, p15, p2 = (res[k]["peak_internal_C"] for k in ("mod_aged_r1", "mod_aged_r15", "mod_aged_r2"))
res["grid"] = dict(peak_r1=p1, peak_r15=p15, peak_r2=p2, change_r1_to_r15=p15 - p1, change_r15_to_r2=p2 - p15,
                   change_r1_to_r2=p2 - p1, criterion_K=0.5, passed=abs(p2 - p15) < 0.5 and abs(p15 - p1) < 0.5)
pdt = res["mod_aged_r1_dt30"]["peak_internal_C"]
res["timestep"] = dict(peak_dt60=p1, peak_dt30=pdt, change=pdt - p1, criterion_K=0.2, passed=abs(pdt - p1) < 0.2)
# network vs elmer, same BCs
q = np.full(16, P.Q_NORMAL); q[7] = 18.3
mn = mini_network(q)
t, st = runs["mod_aged_r2"]
k = min(len(mn), len(st)) - 1
res["network_vs_elmer_r2"] = dict(network_cell_mean_end=mn[-1, :, 0].tolist(), elmer_cell_mean_end=st[-1, :, 0].tolist(),
    max_abs_diff_mean_K=float(np.abs(mn[-1, :, 0] - st[-1, :, 0]).max()),
    network_peak_int=float(mn[..., 1].max()), elmer_peak_int=float(st[..., 1].max()),
    peak_diff_K=float(mn[..., 1].max() - st[..., 1].max()))
# calibrate the lumped conduction factor beta and interior-peak factor gamma to Elmer (finest mesh)
best = None
for beta in np.linspace(0.3, 1.0, 29):
    m_ = mini_network(q, beta=beta, gamma=0.0)
    e = np.abs(m_[-1, :, 0] - st[-1, :, 0]).max()
    if best is None or e < best[1]: best = (beta, e)
beta = best[0]
m_ = mini_network(q, beta=beta, gamma=0.0)
gamma = float((st[..., 1].max() - m_[..., 0].max() - (m_[..., 1].max() - m_[..., 0].max())) /
              max(1e-9, np.abs(m_[-1, 7, 0] - m_[-1, 6, 0]) * 2 * P.CELL_Y * P.CELL_Z / (P.CELL_X / beta + P.R_CONTACT) * (P.CELL_X / 2 / (P.CELL_Y * P.CELL_Z))))
gs = np.linspace(0.0, 0.6, 61)
gamma = float(gs[np.argmin([abs(mini_network(q, beta=beta, gamma=g)[..., 1].max() - st[..., 1].max()) for g in gs])])
m_c = mini_network(q, beta=beta, gamma=max(gamma, 0.0))
res["network_calibrated"] = dict(beta=float(beta), gamma=max(gamma, 0.0), max_abs_diff_mean_K=float(np.abs(m_c[-1, :, 0] - st[-1, :, 0]).max()),
                                 network_peak_int=float(m_c[..., 1].max()), elmer_peak_int=float(st[..., 1].max()))
print("calibrated:", res["network_calibrated"])
qb = np.full(16, P.Q_NORMAL); qb[7] = 0.0
mb = mini_network(qb)
res["network_bypass"] = dict(network_peak=float(mb[..., 1].max()), elmer_peak=res["mod_byp_r1"]["peak_internal_C"])
print(json.dumps({k: res[k] for k in ("grid", "timestep", "network_bypass")}, indent=1))
print("network vs elmer: max |dTmean| %.3f K, peak network %.3f elmer %.3f" % (res["network_vs_elmer_r2"]["max_abs_diff_mean_K"],
      res["network_vs_elmer_r2"]["network_peak_int"], res["network_vs_elmer_r2"]["elmer_peak_int"]))
json.dump(res, open(f"{OUT}/elmer_module.json", "w"), indent=1)
