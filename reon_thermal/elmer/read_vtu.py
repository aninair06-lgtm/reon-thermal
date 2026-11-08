"""Minimal ASCII .vtu reader for Elmer output (points + point-data 'temperature'), per-cell statistics."""
import re, sys, os, json, glob
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "model"))
import params as P

def read_vtu(path):
    s = open(path).read()
    def arr(name):
        m = re.search(r'<DataArray[^>]*Name="%s"[^>]*>(.*?)</DataArray>' % name, s, re.S | re.I)
        return np.array(m.group(1).split(), float) if m else None
    pts = re.search(r'<Points>.*?<DataArray[^>]*>(.*?)</DataArray>', s, re.S).group(1)
    xyz = np.array(pts.split(), float).reshape(-1, 3)
    T = arr("temperature")
    return xyz, T

def cell_stats(xyz, T):
    """Per-cell mean (node average) and max, K -> C. Cell c spans its own 71.7 mm, pads excluded."""
    out = []
    for c in range(16):
        x0 = c * (P.CELL_X + P.PAD_X); x1 = x0 + P.CELL_X
        m = (xyz[:, 0] >= x0 - 1e-9) & (xyz[:, 0] <= x1 + 1e-9)
        out.append((T[m].mean() - 273.15, T[m].max() - 273.15))
    return np.array(out)

if __name__ == "__main__":
    d = sys.argv[1]
    files = sorted(glob.glob(os.path.join(d, "results", "case_t*.vtu")))
    xyz, T = read_vtu(files[-1])
    print(len(files), "files; last", files[-1], "nodes", len(T), "Tmin/max C", T.min() - 273.15, T.max() - 273.15)
