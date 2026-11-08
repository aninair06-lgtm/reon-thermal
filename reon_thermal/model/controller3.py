"""Latching and resistance-based selection: (a) the excess controller that never releases a cell it has identified,
(b) selection from a per-cell resistance estimate (REON monitors resistance per cell, brief) with estimate error."""
import sys, os, json, itertools
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_cases import run_case, Controller
from controller2 import Excess
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
base = dict(mode="passive", T_amb=40.0, h_ext=5.0, T_init=55.0, aged=(6, 7), elec="current")

class Latch(Excess):
    def update(self, t, Ts):
        keep = self.state.copy(); s = super().update(t, Ts); self.state = s | keep; return self.state

class ByResistance(Controller):
    """Bypass the k cells with the highest ESTIMATED resistance at t = 0 (estimate error sigma, relative)."""
    def __init__(self, k=1, sigma=0.1, seed=0, **kw):
        super().__init__(n_max=k, **kw); rng = np.random.default_rng(seed)
        r = np.ones((8, 16)); r[6, 7] = 3.0; est = r * (1 + sigma * rng.standard_normal((8, 16)))
        self.state = np.zeros((8, 16), bool); self.state.ravel()[np.argsort(est.ravel())[::-1][:k]] = True
    def update(self, t, Ts): return self.state

res = {}
for noise, delay in itertools.product((0.0, 0.5, 2.0), (0.0, 120.0)):
    res[f"latch_noise{noise}_delay{int(delay)}"] = run_case("l", controller=Latch(k=4, noise=noise, delay=delay, dwell=60.0), **base)["peak_interior_C"]
for sigma in (0.05, 0.2, 0.5):
    vals = [run_case("r", controller=ByResistance(k=1, sigma=sigma, seed=s), **base)["peak_interior_C"] for s in range(6)]
    res[f"resistance_sigma{sigma}"] = dict(worst=float(max(vals)), best=float(min(vals)), hit_rate=float(np.mean([v < 62 for v in vals])))
ex = json.load(open(os.path.join(R, "extras.json"))); ex["controller_latch_resistance"] = res
json.dump(ex, open(os.path.join(R, "extras.json"), "w"), indent=1)
print(json.dumps(res, indent=1))
