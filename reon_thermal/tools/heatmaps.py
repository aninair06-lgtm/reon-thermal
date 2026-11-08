import json
ids = [f"M{m:02d}_C{c:02d}" for m in range(1, 9) for c in range(1, 17)]
base = {i: 6.1 for i in ids}
aged = dict(base); aged["M07_C08"] = 18.3
byp = dict(base); byp["M07_C08"] = 0.0          # bypassed at constant current: the other cells stay at 6.1 W
d = "/mnt/c/Users/anina/Downloads/MITEC/reon_thermal/results/"
json.dump(aged, open(d + "heat_aged.json", "w")); json.dump(byp, open(d + "heat_aged_bypassed.json", "w"))
print(sum(aged.values()), sum(byp.values()))
