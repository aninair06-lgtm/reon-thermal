"""Fit network couplings to a steady OpenFOAM case on the GPU (pseudo-transient to steady state).
usage: python calibrate.py forced A_sst_m1   |   python calibrate.py passive C_lam_m1
Writes results/calibration_<case>.json with the best parameters and the per-cell comparison."""
import sys, json, os, itertools, time
sys.path.insert(0, "/mnt/c/Users/anina/Downloads/MITEC/reon_thermal/model")
import numpy as np
from network import Network
import params as P
RES = "/mnt/c/Users/anina/Downloads/MITEC/reon_thermal/results"

def of_cells(case):
    d = json.load(open(f"{RES}/openfoam/{case}.json"))
    T = np.array([c["T_volume_mean_C"] for c in d["cells"]]).reshape(8, 16)
    Tx = np.array([c["T_internal_max_C"] for c in d["cells"]]).reshape(8, 16)
    return d, T, Tx

def steady(net, tsim=9000.0, dt=4.0):
    while net.t < tsim:
        net.step(dt)
    return net

def main(mode, case):
    d, Tof, Txof = of_cells(case)
    meta = d["meta"]
    grid = {}
    if mode == "forced":
        sh = np.clip(np.array(d["summary"]["channel_share"]), 0.0, None)
        sh[1:8] = np.maximum(sh[1:8], 1e-3)
        side = float(d["summary"]["side_share"])
        hm = np.linspace(0.4, 2.5, 22); gex = np.array([0.0, 0.02, 0.05, 0.1, 0.2, 0.35, 0.5, 0.8, 1.2, 2.0])
        combos = list(itertools.product(hm, gex))
        B = len(combos)
        kw = dict(mode="forced", T_amb=meta["Ta_C"], T_supply=meta["Tsupply_C"], h_ext=meta["hext"], flow=meta["flow"],
                  f_side=side, w_ch=sh, eps=0.0, eps_wall=0.0)   # 3D run has no radiation -> compare like with like
        hmv = np.array([c[0] for c in combos]); gxv = np.array([c[1] for c in combos])
        net = Network(B=B, gpu=True, h_mult=hmv, G_ex_forced=gxv, cap_scale=0.03, T_init=40.0, **kw)
        names = ("h_mult", "G_ex_forced")
    else:
        hm = np.array([0.6, 0.8, 1.0, 1.25, 1.6]); qc = np.array([0.005, 0.01, 0.02, 0.04, 0.08])
        gex = np.array([0.1, 0.3, 0.6, 1.2, 2.4]); hg = np.array([0.5, 1.0, 2.0, 3.0])
        combos = list(itertools.product(hm, qc, gex, hg)); B = len(combos)
        kw = dict(mode="passive", T_amb=meta["Ta_C"], h_ext=meta["hext"], eps=0.0, eps_wall=0.0)
        a = np.array(combos).T
        net = Network(B=B, gpu=True, h_mult=a[0], Q_circ=a[1], G_ex=a[2], h_gap_nat=a[3], cap_scale=0.03, T_init=meta["Ta_C"] + 20, **kw)
        names = ("h_mult", "Q_circ", "G_ex", "h_gap_nat")
    t0 = time.time()
    steady(net)
    Tn = net.xp.asnumpy(net.Tc)
    err = Tn - Tof[None]
    rms = np.sqrt((err ** 2).mean((1, 2))); mx = np.abs(err).max((1, 2))
    peak_err = Tn.max((1, 2)) - Tof.max()
    score = rms + 0.5 * np.abs(peak_err)
    i = int(score.argmin())
    best = dict(zip(names, [float(v) for v in combos[i]]))
    out = dict(case=case, mode=mode, best=best, rms_K=float(rms[i]), max_abs_K=float(mx[i]), peak_err_K=float(peak_err[i]),
               n_combos=B, gpu_seconds=time.time() - t0, energy_err=float(abs(net.xp.asnumpy(net.energy_error())[i])),
               network_T=Tn[i].tolist(), of_T=Tof.tolist(),
               module_mean_network=Tn[i].mean(1).tolist(), module_mean_of=Tof.mean(1).tolist())
    if mode == "forced":
        out["flow_split"] = dict(channel_share=sh.tolist(), side_share=side)
    json.dump(out, open(f"{RES}/calibration_{case}.json", "w"), indent=1)
    print(json.dumps({k: out[k] for k in ("best", "rms_K", "max_abs_K", "peak_err_K", "n_combos", "gpu_seconds", "energy_err")}, indent=1))
    print("module means OF     :", np.round(Tof.mean(1), 2))
    print("module means network:", np.round(Tn[i].mean(1), 2))
    print("column means OF     :", np.round(Tof.mean(0), 1))
    print("column means network:", np.round(Tn[i].mean(0), 1))

def transient_passive(case):
    """Fit the passive loop couplings to the 3D TRANSIENT sealed case (per-cell mean T every 600 s)."""
    d = json.load(open(f"{RES}/openfoam/{case}_cells.json"))
    meta = json.load(open(os.path.expanduser(f"~/reon_runs/{case}/case_meta.json")))
    tt = np.array(d["t_s"]); Tof = np.array(d["T_mean"]).reshape(len(tt), 8, 16)
    hm = np.array([0.5, 0.75, 1.0, 1.5, 2.0, 3.0]); qc = np.array([0.01, 0.03, 0.08, 0.15, 0.3])
    gex = np.array([0.3, 1.0, 2.4, 5.0, 10.0]); hg = np.array([1.0, 2.0, 3.0, 4.5, 6.0])
    combos = list(itertools.product(hm, qc, gex, hg)); B = len(combos); a = np.array(combos).T
    net = Network(B=B, gpu=True, mode="passive", T_amb=meta["Ta_C"], h_ext=meta["hext"], eps=0.0, eps_wall=0.0,
                  h_mult=a[0], Q_circ=a[1], G_ex=a[2], h_gap_nat=a[3])
    q = np.array(list(json.load(open(os.path.expanduser(f"~/reon_runs/{case}/heat_map.json"))).values())).reshape(8, 16)
    net.q_presc = net.xp.asarray(np.broadcast_to(q, (B, 8, 16)).copy())
    errs = []; t0 = time.time(); keep = []
    sample = [i for i, t in enumerate(tt) if t > 0 and abs(t % 600) < 1e-6]
    while net.t < tt[-1] - 1e-9:
        net.step(10.0)
        j = int(round(net.t / 60.0))
        if j in sample:
            Tn = net.xp.asnumpy(net.Tc)
            errs.append(((Tn - Tof[j][None]) ** 2).mean((1, 2)))
            keep.append((j, Tn))
    rms = np.sqrt(np.mean(errs, 0))
    jl, Tl = keep[-1]
    peak_err = Tl.max((1, 2)) - Tof[jl].max(); spread_err = (Tl.max((1, 2)) - Tl.min((1, 2))) - (Tof[jl].max() - Tof[jl].min())
    score = rms + 0.5 * np.abs(peak_err) + 0.25 * np.abs(spread_err)
    i = int(score.argmin())
    best = dict(zip(("h_mult", "Q_circ", "G_ex", "h_gap_nat"), [float(v) for v in combos[i]]))
    out = dict(case=case, mode="passive_transient", best=best, rms_K=float(rms[i]), peak_err_K=float(peak_err[i]), spread_err_K=float(spread_err[i]),
               t_end=float(tt[-1]), n_combos=B, gpu_seconds=time.time() - t0,
               default_rms_K=float(rms[[k for k, c in enumerate(combos) if c == (1.0, 0.04, 0.6, 1.5)][0]]) if (1.0, 0.04, 0.6, 1.5) in combos else None)
    json.dump(out, open(f"{RES}/calibration_{case}.json", "w"), indent=1)
    print(json.dumps(out, indent=1))

if __name__ == "__main__":
    if sys.argv[1] == "passive_t":
        transient_passive(sys.argv[2])
    else:
        main(sys.argv[1], sys.argv[2])
