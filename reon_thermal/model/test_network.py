import sys, time, numpy as np
sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0])
from network import Network
import params as P

def run(mode, T_amb, h_ext=5.0, T_init=None, tend=7200, dt=10.0, **kw):
    n = Network(B=1, mode=mode, T_amb=T_amb, h_ext=h_ext, T_init=T_init, **kw)
    t0 = time.time(); peak = -1e9; tpk = 0
    while n.t < tend - 1e-9:
        n.step(dt, record=True)
        m = float(n.rec["Tmax"].max())
        if m > peak: peak, tpk = m, n.t
    Tm = n.rec["Tmean"][0]
    print(f"{mode:8s} Ta={T_amb} h={h_ext}: peak Tint {peak:.2f} C at {tpk:.0f}s; mean {Tm.mean():.2f}; spread {Tm.max()-Tm.min():.2f} K; "
          f"hot {np.unravel_index(Tm.argmax(), Tm.shape)}; energy err {float(n.energy_error()[0])*100:.4f}%; Tout {float(n.T_out[0]):.2f}; {time.time()-t0:.1f}s")
    return n

if __name__ == "__main__":
    # zero-generation equilibrium check
    n = Network(B=1, mode="passive", T_amb=30.0, heat_scale=0.0)
    for _ in range(200): n.step(10.0)
    print("zero-gen passive: max |T-30| =", float(np.abs(n.Tc - 30).max()))
    n = Network(B=1, mode="forced", T_amb=20.0, T_supply=20.0, heat_scale=0.0)
    for _ in range(200): n.step(10.0)
    print("zero-gen forced: max |T-20| =", float(np.abs(n.Tc - 20).max()))
    run("forced", 25.0)
    run("passive", 25.0, 5.0)
    run("passive", 40.0, 5.0)
    run("passive", 40.0, 10.0)
    run("passive", 40.0, 5.0, T_init=55.0)
    # adiabatic check: no external loss, passive -> rise should approach 780.8*7200/(618e3 + walls)
    n = run("passive", 25.0, 0.0)
