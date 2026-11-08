"""Improved bypass controller: rank cells by EXCESS over their module's median (a cell-specific signal, like a
resistance estimate), not by absolute temperature; a cell that is clearly hotter (margin) takes a slot over the
current holder. Same sensor noise / delay / dwell sweep as the threshold controller."""
import sys, os, json, itertools
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_cases import run_case, Controller
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")

class Excess(Controller):
    def __init__(self, k=4, trip=1.5, margin=0.7, **kw):
        super().__init__(n_max=k, **kw); self.k, self.trip, self.margin = k, trip, margin
    def update(self, t, Ts):
        self.buf.append((t, Ts + self.rng.normal(0, self.noise, Ts.shape)))
        old = [b for b in self.buf if b[0] <= t - self.delay]
        if not old: return self.state
        meas = old[-1][1]; self.buf = [b for b in self.buf if b[0] > t - self.delay - 60]
        ex = meas - np.median(meas, axis=1, keepdims=True)           # excess over own module
        can = (t - self.since) >= self.dwell
        # release cells whose excess has gone (after dwell)
        rel = self.state & (ex < self.trip - 1.0) & can; self.state[rel] = False; self.since[rel] = t
        # candidates over the trip, hottest-excess first; pre-empt a holder if a candidate beats it by `margin`
        cand = np.argsort(ex.ravel())[::-1]
        for i in cand:
            if ex.ravel()[i] < self.trip: break
            if self.state.ravel()[i]: continue
            if self.state.sum() < self.k:
                self.state.ravel()[i] = True; self.since.ravel()[i] = t
            else:
                held = np.flatnonzero(self.state.ravel() & can.ravel())
                if len(held) and ex.ravel()[i] > ex.ravel()[held].min() + self.margin:
                    j = held[np.argmin(ex.ravel()[held])]
                    self.state.ravel()[j] = False; self.state.ravel()[i] = True; self.since.ravel()[[i, j]] = t
        self.events.append((t, int(self.state.sum())))
        return self.state

base = dict(mode="passive", T_amb=40.0, h_ext=5.0, T_init=55.0, aged=(6, 7), elec="current")
rows = []
for noise, delay, dwell in itertools.product((0.0, 0.5, 2.0), (0.0, 30.0, 120.0), (60.0, 300.0, 900.0)):
    ctl = Excess(k=4, noise=noise, delay=delay, dwell=dwell)
    r = run_case("x", controller=ctl, **base)
    rows.append(dict(noise_K=noise, delay_s=delay, dwell_s=dwell, peak_C=r["peak_interior_C"], energy_kWh=r["energy_delivered_kWh"],
                     mean_bypassed=float(np.mean([e[1] for e in ctl.events])) if ctl.events else 0.0))
pk = np.array([x["peak_C"] for x in rows])
res = dict(case="hot start 55 C, aged cell M07_C08, constant current, up to 4 slots", n_runs=len(rows), peak_min=float(pk.min()), peak_max=float(pk.max()),
           peak_by_noise={str(n): float(max(x["peak_C"] for x in rows if x["noise_K"] == n)) for n in (0.0, 0.5, 2.0)}, runs=rows)
ex = json.load(open(os.path.join(R, "extras.json"))); ex["controller_excess"] = res
json.dump(ex, open(os.path.join(R, "extras.json"), "w"), indent=1)
print("excess controller: peak %.2f-%.2f C over %d runs; worst by noise:" % (pk.min(), pk.max(), len(rows)), res["peak_by_noise"])
