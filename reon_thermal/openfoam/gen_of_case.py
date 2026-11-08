#!/usr/bin/env python3
"""Generate an OpenFOAM-13 (foamMultiRun: fluid + solid) conjugate-heat-transfer case of the
REON EBS cabinet: one air region + one anisotropic solid region holding 8 modules x 16 cells,
each cell its own cellZone and heat source.

Usage: python3 gen_of_case.py CASE_DIR --mode forced|passive --turb laminar|kOmegaSST
       [--mesh 1.0] [--heat heat.json] [--Ta 25] [--Tsupply 20] [--hext 5] [--flow 0.15]
       [--kx 1.0] [--iters 3000] [--np 12] [--inverter 0]
Steady-state (SIMPLE-like) in both regions: gives the long-duration thermal state, the flow field
and the cell-to-air couplings used to calibrate the network model.
"""
import argparse, json, os, sys, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "model"))
import params as P

HDR = """FoamFile
{{
    format      ascii;
    class       {cls};
    location    "{loc}";
    object      {obj};
}}
"""

def write(case, rel, body, cls="dictionary"):
    path = os.path.join(case, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    loc, obj = os.path.dirname(rel), os.path.basename(rel)
    with open(path, "w") as f:
        f.write(HDR.format(cls=cls, loc=loc, obj=obj) + body + "\n")

def mesh_counts(f):
    r = lambda n: max(1, int(round(n * f)))
    return dict(nxc=r(4), ncx=max(2, r(3)), ny_pl=r(5), ny_c=r(8), nz_b=r(5), nz_m=r(8), nz_g=max(2, r(3)), nz_t=r(8))

def main():
    a = argparse.ArgumentParser()
    a.add_argument("case"); a.add_argument("--mode", default="forced"); a.add_argument("--turb", default="laminar")
    a.add_argument("--mesh", type=float, default=1.0); a.add_argument("--heat", default=None)
    a.add_argument("--Ta", type=float, default=25.0); a.add_argument("--Tsupply", type=float, default=20.0)
    a.add_argument("--hext", type=float, default=5.0); a.add_argument("--flow", type=float, default=P.Q_FORCED)
    a.add_argument("--kx", type=float, default=P.K_THROUGH_BASE); a.add_argument("--iters", type=int, default=3000)
    a.add_argument("--np", type=int, default=12); a.add_argument("--inverter", type=float, default=0.0)
    a.add_argument("--transient", action="store_true"); a.add_argument("--endtime", type=float, default=7200.0)
    a.add_argument("--maxco", type=float, default=2.0); a.add_argument("--T0", type=float, default=None)
    a.add_argument("--radiation", action="store_true"); a.add_argument("--emissivity", type=float, default=P.EPS_CELL)
    a.add_argument("--radfreq", type=int, default=10)
    a.add_argument("--solar", action="store_true"); a.add_argument("--solar_roof", type=float, default=600.0)
    a.add_argument("--solar_side", type=float, default=360.0)
    o = a.parse_args()
    case = os.path.abspath(o.case); os.makedirs(case, exist_ok=True)
    n = mesh_counts(o.mesh)
    Lx, Ly, Lz = P.CAB_W, P.CAB_D, P.CAB_H
    forced = o.mode == "forced"
    TaK, TsK = o.Ta + 273.15, o.Tsupply + 273.15
    T0K = (TsK if forced else TaK)
    if o.T0 is not None:
        T0K = o.T0 + 273.15

    # ---------- heat map ----------
    heat = {P.cell_id(m, c): P.Q_NORMAL for m in range(1, 9) for c in range(1, 17)}
    if o.heat:
        heat.update(json.load(open(o.heat)))

    # ---------- blockMesh with multi-grading (grid lines on every interface) ----------
    xs = [(P.X0, n["nxc"]), (P.MOD_LEN, 16 * n["ncx"]), (P.X0, n["nxc"])]
    ys = [(P.Y0, n["ny_pl"]), (P.CELL_Y, n["ny_c"]), (P.Y0, n["ny_pl"])]
    zs = [(P.Z_BOTTOM, n["nz_b"])]
    for m in range(1, 9):
        zs.append((P.CELL_Z, n["nz_m"]))
        if m < 8: zs.append((P.GAP_Z, n["nz_g"]))
    zs.append((P.TOP_SPACE, n["nz_t"]))
    def grading(secs):
        return "( " + " ".join(f"({L:.6f} {c} 1)" for L, c in secs) + " )"
    N = [sum(c for _, c in s) for s in (xs, ys, zs)]
    write(case, "system/blockMeshDict", f"""
convertToMeters 1;
vertices ( (0 0 0) ({Lx} 0 0) ({Lx} {Ly} 0) (0 {Ly} 0) (0 0 {Lz}) ({Lx} 0 {Lz}) ({Lx} {Ly} {Lz}) (0 {Ly} {Lz}) );
blocks ( hex (0 1 2 3 4 5 6 7) ({N[0]} {N[1]} {N[2]}) simpleGrading ( {grading(xs)} {grading(ys)} {grading(zs)} ) );
boundary
(
    walls {{ type wall; faces ( (0 3 2 1) (4 5 6 7) (0 1 5 4) (3 7 6 2) (0 4 7 3) (1 2 6 5) ); }}
);
""")
    eps = 1e-5
    if forced:
        write(case, "system/createPatchDict", f"""
patches
{{
    inlet
    {{
        patchInfo {{ type patch; }}
        constructFrom zone;
        zone {{ type box; zoneType face; box ({-eps} {-eps} {-eps}) ({Lx+eps} {eps} {P.INLET['z1']+eps}); }}
    }}
    outlet
    {{
        patchInfo {{ type patch; }}
        constructFrom zone;
        zone {{ type box; zoneType face; box ({-eps} {P.OUTLET['y0']-eps} {Lz-eps}) ({Lx+eps} {Ly+eps} {Lz+eps}); }}
    }}
}}
""")
    boxes = []
    for m in range(1, 9):
        z0 = P.module_z0(m)
        boxes.append(f"    m{m} {{ type box; zoneType cell; box ({P.X0-eps} {P.Y0-eps} {z0-eps}) ({P.X0+P.MOD_LEN+eps} {P.Y0+P.CELL_Y+eps} {z0+P.CELL_Z+eps}); }}")
    write(case, "system/createZonesDict", f"""
cells
{{
    type union;
    zoneType cell;
{chr(10).join(boxes)}
}}
air
{{
    type invert;
    zoneType cell;
    cells {{ type lookup; zoneType cell; }}
}}
""")
    # per-cell zones in the solid region
    cz = []
    for m in range(1, 9):
        z0 = P.module_z0(m)
        for c in range(1, 17):
            x0 = P.X0 + (c - 1) * P.PITCH_X
            cz.append(f"{P.cell_id(m,c)} {{ type box; zoneType cell; box ({x0+eps} {P.Y0-eps} {z0-eps}) ({x0+P.PITCH_X-eps} {P.Y0+P.CELL_Y+eps} {z0+P.CELL_Z+eps}); }}")
    write(case, "system/cells/createZonesDict", "\n".join(cz))

    # ---------- control ----------
    funcs = """
functions
{
    wallHeatFluxAir
    {
        type            wallHeatFlux;
        libs            ("libfieldFunctionObjects.so");
        region          air;
        writeControl    writeTime;
    }
    cellsTmax { type volFieldValue; libs ("libfieldFunctionObjects.so"); region cells; cellZone all; operation max; fields (T); writeControl timeStep; writeInterval 20; writeFields false; }
    cellsTavg { type volFieldValue; libs ("libfieldFunctionObjects.so"); region cells; cellZone all; operation volAverage; fields (T); writeControl timeStep; writeInterval 20; writeFields false; }
    airTavg { type volFieldValue; libs ("libfieldFunctionObjects.so"); region air; cellZone all; operation volAverage; fields (T); writeControl timeStep; writeInterval 20; writeFields false; }
}
"""
    write(case, "system/controlDict", f"""
regionSolvers {{ air fluid; cells solid; }}
startFrom latestTime; startTime 0; stopAt endTime; endTime {o.iters}; deltaT 1;
writeControl timeStep; writeInterval {max(500, o.iters//3)}; purgeWrite 2;
writeFormat ascii; writePrecision 7; writeCompression off; timeFormat general; timePrecision 6;
runTimeModifiable true;
{funcs}
""")
    write(case, "system/fvSolution", "PIMPLE { nOuterCorrectors 1; }")
    write(case, "system/decomposeParDict", f"numberOfSubdomains {o.np};\nmethod scotch;")
    write(case, "system/fvSchemes", "ddtSchemes{default steadyState;} gradSchemes{default Gauss linear;} divSchemes{default none;} laplacianSchemes{default Gauss linear corrected;} interpolationSchemes{default linear;} snGradSchemes{default corrected;}")

    # ---------- air region ----------
    turb = o.turb
    div_turb = "div(phi,k) bounded Gauss upwind; div(phi,omega) bounded Gauss upwind;" if turb != "laminar" else ""
    write(case, "system/air/fvSchemes", f"""
ddtSchemes {{ default steadyState; }}
gradSchemes {{ default Gauss linear; }}
divSchemes
{{
    default none;
    div(phi,U) bounded Gauss upwind;
    div(phi,h) bounded Gauss upwind;
    div(phi,K) bounded Gauss upwind;
    {div_turb}
    div(((rho*nuEff)*dev2(T(grad(U))))) Gauss linear;
}}
laplacianSchemes {{ default Gauss linear corrected; }}
interpolationSchemes {{ default linear; }}
snGradSchemes {{ default corrected; }}
wallDist {{ method meshWave; }}
""")
    pref = "" if forced else "pRefCell 0; pRefValue 0;"
    write(case, "system/air/fvSolution", f"""
solvers
{{
    "rho.*" {{ solver diagonal; }}
    p_rgh {{ solver PCG; preconditioner DIC; tolerance 1e-7; relTol 0.01; }}
    "(U|h|k|omega)" {{ solver PBiCGStab; preconditioner DILU; tolerance 1e-7; relTol 0.05; }}
}}
PIMPLE
{{
    momentumPredictor yes;
    nNonOrthogonalCorrectors 0;
    {pref}
}}
relaxationFactors
{{
    fields {{ p_rgh 0.7; }}
    equations {{ U 0.2; h 0.6; "(k|omega)" 0.5; }}
}}
""")
    write(case, "constant/air/fvConstraints", "limitT { type limitTemperature; cellZone all; min 270; max 380; }")
    write(case, "constant/cells/fvConstraints", "limitT { type limitTemperature; cellZone all; min 270; max 400; }")
    write(case, "constant/air/physicalProperties", f"""
thermoType {{ type heRhoThermo; mixture pureMixture; transport const; thermo hConst; equationOfState Boussinesq; specie specie; energy sensibleEnthalpy; }}
mixture
{{
    specie {{ molWeight 28.96; }}
    equationOfState {{ rho0 {P.RHO_AIR}; T0 {T0K}; beta {1.0/T0K:.6g}; }}
    thermodynamics {{ Cp {P.CP_AIR}; hf 0; }}
    transport {{ mu {P.MU_AIR}; Pr {P.PR_AIR}; }}
}}
""")
    if turb == "laminar":
        write(case, "constant/air/momentumTransport", "simulationType laminar;")
        write(case, "constant/air/thermophysicalTransport", "laminar { model Fourier; }")
    else:
        write(case, "constant/air/momentumTransport", f"simulationType RAS;\nRAS {{ model {turb}; turbulence on; }}")
        write(case, "constant/air/thermophysicalTransport", "RAS { model eddyDiffusivity; Prt 0.85; }")
    write(case, "constant/air/g", "dimensions [0 1 -2 0 0 0 0];\nvalue (0 0 -9.81);", cls="uniformDimensionedVectorField")
    # Boussinesq air: gauge pressure, no pRef (pRef=1e5 makes p/rho swamp the enthalpy)

    io = "inlet|outlet" if forced else "NONE"
    ext = f"""    walls
    {{
        type externalTemperature; Ta constant {TaK}; h uniform {o.hext};
        thicknessLayers ({P.WALL_T}); kappaLayers ({P.WALL_K}); value $internalField;
    }}"""
    inT = f"    inlet {{ type fixedValue; value uniform {TsK}; }}\n    outlet {{ type inletOutlet; inletValue uniform {TsK}; value $internalField; }}" if forced else ""
    write(case, "0/air/T", f"""dimensions [0 0 0 1 0 0 0];
internalField uniform {T0K};
boundaryField
{{
    #includeEtc "caseDicts/setConstraintTypes"
{ext}
{inT}
    air_to_cells {{ type coupledTemperature; value $internalField; }}
}}""", cls="volScalarField")
    inU = f"    inlet {{ type flowRateInletVelocity; volumetricFlowRate constant {o.flow}; value uniform (0 0 0); }}\n    outlet {{ type pressureInletOutletVelocity; value uniform (0 0 0); }}" if forced else ""
    write(case, "0/air/U", f"""dimensions [0 1 -1 0 0 0 0];
internalField uniform (0 0 0);
boundaryField
{{
    #includeEtc "caseDicts/setConstraintTypes"
    "(walls|air_to_cells)" {{ type noSlip; }}
{inU}
}}""", cls="volVectorField")
    write(case, "0/air/p", """dimensions [1 -1 -2 0 0 0 0];
internalField uniform 0;
boundaryField { #includeEtc "caseDicts/setConstraintTypes" ".*" { type calculated; value $internalField; } }""", cls="volScalarField")
    outP = "    outlet { type fixedValue; value uniform 0; }" if forced else ""
    write(case, "0/air/p_rgh", f"""dimensions [1 -1 -2 0 0 0 0];
internalField uniform 0;
boundaryField
{{
    #includeEtc "caseDicts/setConstraintTypes"
    ".*" {{ type fixedFluxPressure; value $internalField; }}
{outP}
}}""", cls="volScalarField")
    if turb != "laminar":
        Uin = o.flow / (Lx * P.INLET["z1"])
        k0 = 1.5 * (0.05 * Uin) ** 2
        om0 = math.sqrt(k0) / (0.09 ** 0.25 * 0.01)
        write(case, "0/air/k", f"""dimensions [0 2 -2 0 0 0 0];
internalField uniform {k0:.5g};
boundaryField
{{
    #includeEtc "caseDicts/setConstraintTypes"
    "(walls|air_to_cells)" {{ type kqRWallFunction; value $internalField; }}
    inlet {{ type turbulentIntensityKineticEnergyInlet; intensity 0.05; value $internalField; }}
    outlet {{ type inletOutlet; inletValue $internalField; value $internalField; }}
}}""", cls="volScalarField")
        write(case, "0/air/omega", f"""dimensions [0 0 -1 0 0 0 0];
internalField uniform {om0:.5g};
boundaryField
{{
    #includeEtc "caseDicts/setConstraintTypes"
    "(walls|air_to_cells)" {{ type omegaWallFunction; value $internalField; }}
    inlet {{ type turbulentMixingLengthFrequencyInlet; mixingLength 0.01; value $internalField; }}
    outlet {{ type inletOutlet; inletValue $internalField; value $internalField; }}
}}""", cls="volScalarField")
        write(case, "0/air/nut", """dimensions [0 2 -1 0 0 0 0];
internalField uniform 0;
boundaryField
{
    #includeEtc "caseDicts/setConstraintTypes"
    "(walls|air_to_cells)" { type nutkWallFunction; value $internalField; }
    "(inlet|outlet)" { type calculated; value $internalField; }
}""", cls="volScalarField")
        write(case, "0/air/alphat", """dimensions [1 -1 -1 0 0 0 0];
internalField uniform 0;
boundaryField { #includeEtc "caseDicts/setConstraintTypes" ".*" { type calculated; value $internalField; } }""", cls="volScalarField")

    # ---------- solid region (anisotropic, homogenised cell + pad stack) ----------
    kx_eff = P.PITCH_X / (P.CELL_X / o.kx + P.R_CONTACT)   # series rule incl. 0.0013 m2K/W once per pitch
    rho_h = P.N_PER_MOD * P.CELL_MASS / (P.MOD_LEN * P.CELL_Y * P.CELL_Z)
    write(case, "constant/cells/physicalProperties", f"""
thermoType {{ type heSolidThermo; mixture pureMixture; transport constAnisoSolid; thermo eConst; equationOfState rhoConst; specie specie; energy sensibleInternalEnergy; }}
mixture
{{
    specie {{ molWeight 50; }}
    equationOfState {{ rho {rho_h:.2f}; }}
    transport {{ kappa ({kx_eff:.5f} {P.K_INPLANE} {P.K_INPLANE}); }}
    thermodynamics {{ hf 0; Cv {P.CP_CELL}; }}
}}
""")
    write(case, "constant/cells/thermophysicalTransport", """
model anisotropic;
boundaryAligned true;
coordinateSystem { type cartesian; origin (0 0 0); coordinateRotation { type axesRotation; e1 (1 0 0); e3 (0 0 1); } }
""")
    src = [f"{cid} {{ type heatSource; cellZone {cid}; Q {q:.6g}; }}" for cid, q in heat.items()]
    write(case, "constant/cells/fvModels", "\n".join(src))
    write(case, "system/cells/fvSchemes", "ddtSchemes{default steadyState;} gradSchemes{default Gauss linear;} divSchemes{default none;} laplacianSchemes{default Gauss linear corrected;} interpolationSchemes{default linear;} snGradSchemes{default corrected;}")
    write(case, "system/cells/fvSolution", """
solvers { "e.*" { solver GAMG; smoother symGaussSeidel; tolerance 1e-8; relTol 0.05; } }
PIMPLE { nNonOrthogonalCorrectors 0; }
relaxationFactors { equations { e 0.9; } }
""")
    write(case, "0/cells/T", f"""dimensions [0 0 0 1 0 0 0];
internalField uniform {T0K};
boundaryField
{{
    #includeEtc "caseDicts/setConstraintTypes"
    cells_to_air {{ type coupledTemperature; value $internalField; }}
}}""", cls="volScalarField")

    if o.transient:
        # ---------- transient (PIMPLE) variant: 2 h physical discharge ----------
        for reg in ("air", "cells"):
            p = os.path.join(case, f"system/{reg}/fvSchemes")
            s = open(p).read().replace("default steadyState;", "default Euler;")
            open(p, "w").write(s)
        p = os.path.join(case, "system/fvSchemes"); open(p, "w").write(open(p).read().replace("default steadyState;", "default Euler;"))
        write(case, "system/air/fvSolution", f"""
solvers
{{
    "rho.*" {{ solver diagonal; }}
    p_rgh {{ solver PCG; preconditioner DIC; tolerance 1e-7; relTol 0.01; }}
    p_rghFinal {{ $p_rgh; relTol 0; }}
    "(U|h|k|omega)" {{ solver PBiCGStab; preconditioner DILU; tolerance 1e-7; relTol 0.1; }}
    "(U|h|k|omega)Final" {{ $U; relTol 0; }}
}}
PIMPLE {{ momentumPredictor yes; nCorrectors 2; nNonOrthogonalCorrectors 0; {pref} }}
""")
        write(case, "system/cells/fvSolution", """
solvers { "e.*" { solver GAMG; smoother symGaussSeidel; tolerance 1e-8; relTol 0; } }
PIMPLE { nNonOrthogonalCorrectors 0; }
""")
        write(case, "system/fvSolution", "PIMPLE { nOuterCorrectors 1; }")
        cellfos = []
        for cid in heat:
            for op, tag in (("max", "max"), ("volAverage", "avg")):
                cellfos.append(f"    {tag}_{cid} {{ type volFieldValue; libs (\"libfieldFunctionObjects.so\"); region cells; cellZone {cid}; operation {op}; fields (T); writeControl adjustableRunTime; writeInterval 60; writeFields false; log false; }}")
        write(case, "system/controlDict", f"""
regionSolvers {{ air fluid; cells solid; }}
startFrom latestTime; startTime 0; stopAt endTime; endTime {o.endtime}; deltaT 0.05;
writeControl adjustableRunTime; writeInterval 900; purgeWrite 0;
writeFormat ascii; writePrecision 7; writeCompression off; timeFormat general; timePrecision 6;
runTimeModifiable true; adjustTimeStep yes; maxCo {o.maxco}; maxDi 1e6;
functions
{{
    wallHeatFluxAir {{ type wallHeatFlux; libs ("libfieldFunctionObjects.so"); region air; writeControl writeTime; }}
    cellsTmax {{ type volFieldValue; libs ("libfieldFunctionObjects.so"); region cells; cellZone all; operation max; fields (T); writeControl adjustableRunTime; writeInterval 30; writeFields false; }}
    cellsTavg {{ type volFieldValue; libs ("libfieldFunctionObjects.so"); region cells; cellZone all; operation volAverage; fields (T); writeControl adjustableRunTime; writeInterval 30; writeFields false; }}
    airTavg {{ type volFieldValue; libs ("libfieldFunctionObjects.so"); region air; cellZone all; operation volAverage; fields (T); writeControl adjustableRunTime; writeInterval 30; writeFields false; }}
{chr(10).join(cellfos)}
}}
""")
    # ---------- optional physics: surface radiation, inverter heat in the top space, absorbed sun on roof + east wall ----------
    def edit(rel, old, new):
        p = os.path.join(case, rel); s = open(p).read()
        assert old in s, (rel, old)
        open(p, "w").write(s.replace(old, new, 1))
    air_models = []
    if o.radiation:
        air_models.append('radiation { type radiation; libs ("libradiationModels.so"); }')
        write(case, "constant/air/radiationProperties", f"""
radiationModel  fvDOM;
fvDOMCoeffs {{ nPhi 2; nTheta 4; tolerance 1e-3; maxIter 5; }}
solverFreq {o.radfreq};
absorptionEmissionModel constant;
constantCoeffs {{ absorptivity 1e-4; emissivity 1e-4; E 0; }}
scatterModel none;
sootModel none;
""")
        write(case, "0/air/IDefault", f"""dimensions [1 0 -3 0 0 0 0];
internalField uniform 0;
boundaryField
{{
    #includeEtc "caseDicts/setConstraintTypes"
    ".*" {{ type greyDiffusiveRadiation; emissivityMode lookup; emissivity uniform {o.emissivity}; value uniform 0; }}
}}""", cls="volScalarField")
        edit("system/air/fvSchemes", "div(phi,K)", "div(Ji,Ii_h) bounded Gauss upwind;\n    div(phi,K)")
        edit("system/air/fvSolution", '"rho.*" { solver diagonal; }', '"rho.*" { solver diagonal; }\n    "Ii.*" { solver GAMG; smoother symGaussSeidel; tolerance 1e-4; relTol 0; maxIter 5; }')
        edit("0/air/T", "thicknessLayers", "qr qr; thicknessLayers")
        edit("0/air/T", "air_to_cells { type coupledTemperature;", "air_to_cells { type coupledTemperature; qr qr;")
        edit("0/cells/T", "cells_to_air { type coupledTemperature;", "cells_to_air { type coupledTemperature; qrNbr qr;")
    if o.inverter > 0:
        zt = P.Z_TOP_OF_STACK
        # the whole top-space air (0.17 m3); heat ramps in over 600 s like a box with thermal mass warming up
        write(case, "system/air/createZonesDict", f"inverter {{ type box; zoneType cell; box (0 0 {zt + 0.005}) ({Lx} {Ly} {Lz}); }}")
        air_models.append(f"inverter {{ type heatSource; cellZone inverter; Q table ((0 0) (600 {o.inverter}) (1e6 {o.inverter})); }}")
    if air_models:
        write(case, "constant/air/fvModels", "\n".join(air_models))
    if o.solar:
        write(case, "system/createPatchDict", f"""
patches
{{
    roof {{ patchInfo {{ type wall; }} constructFrom zone; zone {{ type box; zoneType face; box ({-eps} {-eps} {Lz-eps}) ({Lx+eps} {Ly+eps} {Lz+eps}); }} }}
    sideE {{ patchInfo {{ type wall; }} constructFrom zone; zone {{ type box; zoneType face; box ({Lx-eps} {-eps} {-eps}) ({Lx+eps} {Ly+eps} {Lz+eps}); }} }}
}}
""")
        rad = "qr qr; " if o.radiation else ""
        sol = lambda nm, q: f"    {nm}\n    {{\n        type externalTemperature; Ta constant {TaK}; h uniform {o.hext}; q uniform {q}; {rad}\n        thicknessLayers ({P.WALL_T}); kappaLayers ({P.WALL_K}); value $internalField;\n    }}"
        edit("0/air/T", "    air_to_cells", sol("roof", o.solar_roof) + "\n" + sol("sideE", o.solar_side) + "\n    air_to_cells")
        edit("0/air/U", '"(walls|air_to_cells)"', '"(walls|roof|sideE|air_to_cells)"')
        if os.path.exists(os.path.join(case, "0/air/IDefault")):
            pass  # regex ".*" already covers the new patches
    meta = dict(case=case, mode=o.mode, turb=turb, mesh=o.mesh, counts=n, N=N, ncells=N[0]*N[1]*N[2], transient=o.transient,
                radiation=o.radiation, emissivity=o.emissivity, inverter_W=o.inverter, solar=o.solar, solar_roof=o.solar_roof, solar_side=o.solar_side,
                Ta_C=o.Ta, Tsupply_C=o.Tsupply, hext=o.hext, flow=o.flow if forced else 0.0, kx=o.kx,
                kx_eff=kx_eff, rho_h=rho_h, total_heat_W=sum(heat.values()), iters=o.iters, np=o.np)
    json.dump(meta, open(os.path.join(case, "case_meta.json"), "w"), indent=1)
    json.dump(heat, open(os.path.join(case, "heat_map.json"), "w"), indent=0)

    with open(os.path.join(case, "Allrun"), "w") as f:
        f.write(f"""#!/bin/bash
cd "$(dirname "$0")"
. /opt/openfoam13/etc/bashrc
set -e
blockMesh > log.blockMesh 2>&1
{"createPatch -overwrite > log.createPatch 2>&1" if (forced or o.solar) else ""}
createZones > log.createZones 2>&1
splitMeshRegions -cellZonesOnly -overwrite > log.splitMeshRegions 2>&1
createZones -region cells > log.createZones.cells 2>&1
{"createZones -region air > log.createZones.air 2>&1" if o.inverter > 0 else ""}
rm -rf constant/polyMesh
checkMesh -region air > log.checkMesh.air 2>&1 || true
decomposePar -allRegions -force > log.decomposePar 2>&1
mpirun -np {o.np} foamMultiRun -parallel > log.foamMultiRun 2>&1
reconstructPar -allRegions -latestTime > log.reconstructPar 2>&1
touch case.foam
echo DONE
""")
    os.chmod(os.path.join(case, "Allrun"), 0o755)
    print(json.dumps(meta))

if __name__ == "__main__":
    main()
