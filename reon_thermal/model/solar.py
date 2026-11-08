"""Absorbed solar flux on the roof and the west wall from pvlib clear-sky irradiance (Phoenix, 21 June).
The discharge starts at START_HOUR local time (14:00, the hottest window); absorptance ALPHA (dark-grey paint, AA)."""
import json, os
import numpy as np
_d = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "coolprop_pvlib.json")))["solar"]
_h, _roof, _west = np.array(_d["hours"]), np.array(_d["roof"]), np.array(_d["west"])
START_HOUR = 14.0
ALPHA = 0.6
def _at(arr, t, start):
    return float(np.interp(((start + t / 3600.0) % 24.0), _h, arr))
def roof(t, start=START_HOUR, alpha=ALPHA): return alpha * _at(_roof, t, start)
def west(t, start=START_HOUR, alpha=ALPHA): return alpha * _at(_west, t, start)
def window_mean(start=START_HOUR, hours=2.0, alpha=ALPHA):
    ts = np.linspace(0, hours * 3600, 121)
    return float(np.mean([roof(t, start, alpha) for t in ts])), float(np.mean([west(t, start, alpha) for t in ts]))
if __name__ == "__main__":
    print("absorbed mean over 14-16 h: roof %.0f, west %.0f W/m2" % window_mean())
    for s in (10, 12, 14, 16):
        print(s, "h start: roof %.0f west %.0f" % window_mean(s))
