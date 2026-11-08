"""Analytic benchmark: steady conduction through the 16-cell stack with 15 resolved contact layers.
Analytic: series resistance per unit area  R = 16*L/kx + 15*R''  ->  q'' = dT/R; piecewise-linear T(x)."""
import sys, os, glob, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from read_vtu import read_vtu
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "model"))
import params as P

def analytic_x(x, kx=1.0, TL=50.0, TR=30.0):
    R = 16 * P.CELL_X / kx + 15 * P.R_CONTACT
    q = (TL - TR) / R
    T = np.empty_like(x)
    for i, xi in enumerate(x):
        c = min(int(xi // (P.CELL_X + P.PAD_X)), 15)
        xc = xi - c * (P.CELL_X + P.PAD_X)
        r = c * (P.CELL_X / kx + P.R_CONTACT)
        if xc <= P.CELL_X:
            r += xc / kx
        else:
            r += P.CELL_X / kx + (xc - P.CELL_X) / (P.PAD_X / P.R_CONTACT) * 1.0 * (P.PAD_X / P.PAD_X)
        T[i] = TL - q * r
    return T, q

res = {}
for name, kx in (("bench_x_r1", 1.0),):
    d = os.path.expanduser(f"~/reon_runs/elmer/{name}")
    f = sorted(glob.glob(os.path.join(d, "results", "case_t*.vtu")))[-1]
    xyz, T = read_vtu(f); T = T - 273.15
    Ta, q = analytic_x(xyz[:, 0], kx)
    err = np.abs(T - Ta)
    res[name] = dict(max_abs_err_K=float(err.max()), q_analytic_W_m2=float(q), n_nodes=int(len(T)),
                     T_at_cell_centres=[float(np.interp(c * (P.CELL_X + P.PAD_X) + P.CELL_X / 2, np.sort(xyz[:, 0]), T[np.argsort(xyz[:, 0])])) for c in range(16)])
    print(name, "max |T_elmer - T_analytic| =", f"{err.max():.2e} K", "q'' =", f"{q:.3f} W/m2")
d = os.path.expanduser("~/reon_runs/elmer/bench_y_r1")
if os.path.isdir(d):
    f = sorted(glob.glob(os.path.join(d, "results", "case_t*.vtu")))[-1]
    xyz, T = read_vtu(f); T = T - 273.15
    Ta = 50.0 - 20.0 * xyz[:, 1] / P.CELL_Y
    res["bench_y_r1"] = dict(max_abs_err_K=float(np.abs(T - Ta).max()))
    print("bench_y_r1 max err", f"{np.abs(T - Ta).max():.2e} K")
json.dump(res, open("/mnt/c/Users/anina/Downloads/MITEC/reon_thermal/results/elmer_benchmark.json", "w"), indent=1)
