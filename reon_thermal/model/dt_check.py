import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_cases import run_case
out = {}
for nm, kw in (("H_hotstart", dict(T_init=55.0)), ("E_aged_hot", dict(T_init=55.0, aged=(6, 7)))):
    a = run_case(nm, "passive", 40.0, 5.0, dt=10.0, **kw)["peak_interior_C"]
    b = run_case(nm, "passive", 40.0, 5.0, dt=5.0, **kw)["peak_interior_C"]
    out[nm] = dict(dt10=a, dt5=b, change_K=b - a, passed=abs(b - a) < 0.2)
    print(nm, out[nm])
json.dump(out, open(os.path.join(os.path.dirname(__file__), "..", "results", "network_dt_check.json"), "w"), indent=1)
