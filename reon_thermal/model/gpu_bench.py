import sys, time
sys.path.insert(0, "/mnt/c/Users/anina/Downloads/MITEC/reon_thermal/model")
import numpy as np
from network import Network
for B, gpu in ((1, False), (4096, True), (16384, True)):
    n = Network(B=B, gpu=gpu, mode="passive", T_amb=40.0)
    t0 = time.time()
    for _ in range(720): n.step(10.0)
    xp = n.xp
    if gpu: xp.cuda.Stream.null.synchronize()
    dt = time.time() - t0
    print(f"B={B:6d} gpu={gpu}: {dt:.2f}s for a 2 h discharge -> {B/dt:.0f} cabinet-discharges/s; Tmax {float(n.Tc.max()):.2f}; err {float(abs(n.energy_error()).max()):.2e}")
