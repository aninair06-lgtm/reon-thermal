"""Pick the N hottest cells by each cell's MAXIMUM interior temperature over the whole baseline discharge
(time basis: 0-7200 s, sampled every 10 s). Writes the heat map with those cells bypassed (0 W, ideal)."""
import sys, json, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from network import Network
import params as P

def hottest(N=13, **kw):
    n = Network(B=1, **kw)
    Tmax = np.full((8, 16), -1e9)
    while n.t < 7200 - 1e-9:
        n.step(10.0, record=True)
        Tmax = np.maximum(Tmax, np.asarray(n.rec["Tmax"][0]))
    idx = np.argsort(Tmax.ravel())[::-1][:N]
    ids = [P.cell_id(i // 16 + 1, i % 16 + 1) for i in idx]
    return ids, Tmax

if __name__ == "__main__":
    ids, Tmax = hottest(13, mode="passive", T_amb=40.0, h_ext=5.0)
    print("13 hottest (network, case C basis):", ids)
    print("their peak interior T:", np.round(np.sort(Tmax.ravel())[::-1][:13], 2))
    heat = {P.cell_id(m, c): P.Q_NORMAL for m in range(1, 9) for c in range(1, 17)}
    # constant delivered power: 115 active cells at 7.6 W (all-series assumption), bypassed ideal 0 W
    for k in heat: heat[k] = 7.6
    for k in ids: heat[k] = 0.0
    out = os.path.join(os.path.dirname(__file__), "..", "results", "D_heatmap_network13.json")
    json.dump(heat, open(out, "w"), indent=0)
    json.dump(dict(ids=ids, basis="network case C, max interior T over 0-7200 s"), open(out.replace(".json", "_ids.json"), "w"), indent=1)
    print("total heat", sum(heat.values()))
