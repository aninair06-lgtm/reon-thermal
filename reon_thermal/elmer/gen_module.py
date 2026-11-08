#!/usr/bin/env python3
"""Elmer FEM 3D model of one REON module: 16 prismatic cells + 15 resolved 0.2 mm interface layers.

Cells: rho 1773, cp 1050, k = diag(k_through, 25, 25); layers: k = 0.2 mm / 0.0013 m2K/W (counted once).
Structured hex mesh written directly in Elmer format (mesh.header/nodes/elements/boundary).

Usage: python3 gen_module.py CASE_DIR --case bench|bench_y|module [--ref 1] [--kx 1] [--h 3] [--Tair 40]
       [--T0 40] [--aged 8] [--qaged 18.3] [--tend 7200] [--dt 60]
  bench   : steady, no generation, T=50 C at x=0 and 30 C at x=L, other faces adiabatic (analytic check)
  bench_y : same along y (in-plane k=25)
  module  : transient discharge; h on top/bottom/front/rear/ends to Tair; 6.1 W per cell, aged cell q_aged
"""
import argparse, os, sys, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "model"))
import params as P

def build_mesh(d, ref):
    nxc, nxp, ny, nz = int(6 * ref), 1, int(10 * ref), int(12 * ref)
    xs = [0.0]; body_of_xcell = []
    for c in range(16):
        x0 = xs[-1]
        xs += list(x0 + P.CELL_X * np.arange(1, nxc + 1) / nxc); body_of_xcell += [c + 1] * nxc
        if c < 15:
            xs.append(xs[-1] + P.PAD_X); body_of_xcell += [17] * nxp
    xs = np.array(xs); ys = np.linspace(0, P.CELL_Y, ny + 1); zs = np.linspace(0, P.CELL_Z, nz + 1)
    NX, NY, NZ = len(xs), len(ys), len(zs)
    nid = lambda i, j, k: 1 + i + NX * (j + NY * k)
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    os.makedirs(d, exist_ok=True)
    with open(f"{d}/mesh.nodes", "w") as f:
        for k in range(NZ):
            for j in range(NY):
                for i in range(NX):
                    f.write(f"{nid(i,j,k)} -1 {xs[i]:.8e} {ys[j]:.8e} {zs[k]:.8e}\n")
    elems = []
    eid = 0
    with open(f"{d}/mesh.elements", "w") as f:
        for k in range(NZ - 1):
            for j in range(NY - 1):
                for i in range(NX - 1):
                    eid += 1
                    n = [nid(i,j,k), nid(i+1,j,k), nid(i+1,j+1,k), nid(i,j+1,k),
                         nid(i,j,k+1), nid(i+1,j,k+1), nid(i+1,j+1,k+1), nid(i,j+1,k+1)]
                    f.write(f"{eid} {body_of_xcell[i]} 808 " + " ".join(map(str, n)) + "\n")
    ne = eid
    eidx = lambda i, j, k: 1 + i + (NX - 1) * (j + (NY - 1) * k)
    bid = 0
    with open(f"{d}/mesh.boundary", "w") as f:
        def bw(tag, parent, nodes):
            nonlocal bid
            bid += 1
            f.write(f"{bid} {tag} {parent} 0 404 " + " ".join(map(str, nodes)) + "\n")
        for j in range(NY - 1):
            for i in range(NX - 1):
                bw(2, eidx(i, j, 0), [nid(i,j,0), nid(i,j+1,0), nid(i+1,j+1,0), nid(i+1,j,0)])           # bottom
                bw(1, eidx(i, j, NZ-2), [nid(i,j,NZ-1), nid(i+1,j,NZ-1), nid(i+1,j+1,NZ-1), nid(i,j+1,NZ-1)])  # top
        for k in range(NZ - 1):
            for i in range(NX - 1):
                bw(3, eidx(i, 0, k), [nid(i,0,k), nid(i+1,0,k), nid(i+1,0,k+1), nid(i,0,k+1)])            # front y=0
                bw(4, eidx(i, NY-2, k), [nid(i,NY-1,k), nid(i,NY-1,k+1), nid(i+1,NY-1,k+1), nid(i+1,NY-1,k)])  # rear
            for j in range(NY - 1):
                bw(5, eidx(0, j, k), [nid(0,j,k), nid(0,j,k+1), nid(0,j+1,k+1), nid(0,j+1,k)])            # x=0 end
                bw(6, eidx(NX-2, j, k), [nid(NX-1,j,k), nid(NX-1,j+1,k), nid(NX-1,j+1,k+1), nid(NX-1,j,k+1)])  # x=L end
    with open(f"{d}/mesh.header", "w") as f:
        f.write(f"{NX*NY*NZ} {ne} {bid}\n2\n808 {ne}\n404 {bid}\n")
    return dict(NX=NX, NY=NY, NZ=NZ, ne=ne, nb=bid, L=float(xs[-1]))

def main():
    a = argparse.ArgumentParser()
    a.add_argument("case"); a.add_argument("--case", dest="kind", default="module")
    a.add_argument("--ref", type=float, default=1.0); a.add_argument("--kx", type=float, default=1.0)
    a.add_argument("--h", type=float, default=3.0); a.add_argument("--Tair", type=float, default=40.0)
    a.add_argument("--T0", type=float, default=40.0); a.add_argument("--aged", type=int, default=8)
    a.add_argument("--qaged", type=float, default=18.3); a.add_argument("--tend", type=float, default=7200.0)
    a.add_argument("--dt", type=float, default=60.0); a.add_argument("--qcell", type=float, default=P.Q_NORMAL)
    o = a.parse_args()
    d = os.path.abspath(o.case); os.makedirs(d, exist_ok=True)
    info = build_mesh(os.path.join(d, "mesh"), o.ref)
    k_pad = P.PAD_X / P.R_CONTACT
    K = 273.15
    steady = o.kind.startswith("bench")
    mats = f"""
Material 1
  Name = "NaIonCell"
  Density = {P.RHO_CELL}
  Heat Capacity = {P.CP_CELL}
  Heat Conductivity(3,3) = Real {o.kx} 0 0  0 {P.K_INPLANE} 0  0 0 {P.K_INPLANE}
End
Material 2
  Name = "InterfaceLayer"
  Density = 2000.0
  Heat Capacity = 1000.0
  Heat Conductivity = {k_pad:.6f}
End
"""
    bodies, bforces = [], []
    for c in range(1, 17):
        q = 0.0 if steady else (o.qaged if c == o.aged else o.qcell)
        bodies.append(f"Body {c}\n  Target Bodies(1) = {c}\n  Equation = 1\n  Material = 1\n  Body Force = {c}\n  Initial Condition = 1\nEnd")
        bforces.append(f"Body Force {c}\n  Heat Source = {q / P.CELL_MASS:.8f}\nEnd")
    bodies.append("Body 17\n  Target Bodies(1) = 17\n  Equation = 1\n  Material = 2\n  Initial Condition = 1\nEnd")
    if o.kind == "bench":
        bcs = f"Boundary Condition 1\n  Target Boundaries(1) = 5\n  Temperature = {50+K}\nEnd\nBoundary Condition 2\n  Target Boundaries(1) = 6\n  Temperature = {30+K}\nEnd\n"
    elif o.kind == "bench_y":
        bcs = f"Boundary Condition 1\n  Target Boundaries(1) = 3\n  Temperature = {50+K}\nEnd\nBoundary Condition 2\n  Target Boundaries(1) = 4\n  Temperature = {30+K}\nEnd\n"
    else:
        bcs = f"Boundary Condition 1\n  Target Boundaries(6) = 1 2 3 4 5 6\n  Heat Transfer Coefficient = {o.h}\n  External Temperature = {o.Tair+K}\nEnd\n"
    sim = ("Simulation\n  Max Output Level = 4\n  Coordinate System = Cartesian\n  Simulation Type = Steady state\n"
           "  Steady State Max Iterations = 1\n  Post File = case.vtu\nEnd\n") if steady else (
           f"Simulation\n  Max Output Level = 4\n  Coordinate System = Cartesian\n  Simulation Type = Transient\n"
           f"  Timestepping Method = BDF\n  BDF Order = 2\n  Timestep Sizes = {o.dt}\n  Timestep Intervals = {int(round(o.tend/o.dt))}\n"
           f"  Output Intervals = {max(1, int(round(600/o.dt)))}\n  Steady State Max Iterations = 1\nEnd\n")
    sif = f"""Header
  CHECK KEYWORDS Warn
  Mesh DB "." "mesh"
  Results Directory "results"
End
{sim}
Constants
  Stefan Boltzmann = 5.670374e-08
End
{chr(10).join(bodies)}
{mats}
{chr(10).join(bforces)}
Initial Condition 1
  Temperature = {o.T0 + K}
End
Equation 1
  Active Solvers(1) = 1
End
Solver 1
  Equation = Heat Equation
  Variable = Temperature
  Procedure = "HeatSolve" "HeatSolver"
  Linear System Solver = Iterative
  Linear System Iterative Method = BiCGStab
  Linear System Preconditioning = ILU0
  Linear System Max Iterations = 2000
  Linear System Convergence Tolerance = 1.0e-10
  Nonlinear System Max Iterations = 1
  Steady State Convergence Tolerance = 1.0e-8
End
Solver 2
  Exec Solver = After Timestep
  Equation = "ResultOutput"
  Procedure = "ResultOutputSolve" "ResultOutputSolver"
  Output File Name = "case"
  Output Format = vtu
  Ascii Output = True
  Vtu Format = Logical True
End
Solver 3
  Exec Solver = After Timestep
  Equation = "SaveScalars"
  Procedure = "SaveData" "SaveScalars"
  Filename = "scalars.dat"
  Variable 1 = Temperature
  Operator 1 = max
  Operator 2 = min
  Operator 3 = mean
End
{bcs}
"""
    with open(os.path.join(d, "case.sif"), "w") as f:
        f.write(sif)
    with open(os.path.join(d, "ELMERSOLVER_STARTINFO"), "w") as f:
        f.write("case.sif\n1\n")
    json.dump(dict(vars(o), **info, k_pad=k_pad), open(os.path.join(d, "meta.json"), "w"), indent=1)
    print(json.dumps(info))

if __name__ == "__main__":
    main()
