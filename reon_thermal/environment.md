# Environment

| Item | Version / setting |
|---|---|
| Host | Windows 11 Home 10.0.26300, 24 logical CPUs, NVIDIA GeForce RTX 5070 Ti Laptop GPU (12 GB), driver 616.92 |
| WSL | WSL 2.7.3, kernel 6.6.114.1, Ubuntu 24.04.4 LTS, 15 GB RAM |
| OpenFOAM | OpenFOAM 13 (openfoam.org), package 20260624, `foamMultiRun` with `fluid` + `solid` region solvers |
| Elmer FEM | ElmerSolver 26.2 (PPA package elmerfem-csc-eg 9.0-0ppa0-202611021648), HeatSolver, BDF2 |
| Python (WSL venv `~/reon_venv`) | 3.12.3, numpy 2.5.4, scipy 1.18.1, matplotlib 3.11.2, cupy-cuda12x 14.2.0 (CUDA runtime 12.9), SALib 1.6.0, numba 0.68.1, pandas 3.1.1 |
| Python (Windows) | 3.13.7, numpy 2.2.4, scipy 1.15.2, matplotlib 3.10.7 (CPU network runs) |
| Node | 24.13.0 (figure and report builds, Anatomy kit) |

GPU note: CuPy is blocked on the Windows side by the Application Control policy, so all GPU work runs in WSL (same GPU through WSLg/DirectX).

## OpenFOAM settings (all cases)
- Mesh: structured blockMesh with grid lines on every interface; base mesh 56 x 18 x 98 = 98,784 cells (air 74,208, cells 24,576); `--mesh` scales it.
- Air: Boussinesq (rho0 1.19 kg/m3, beta = 1/T0), Cp 1006, mu 1.83e-5, Pr 0.71; gauge pressure, gravity on.
- Cells: one solid region (`constAnisoSolid`, `anisotropic` transport), kappa = (k_x,eff, 25, 25) with k_x,eff = 0.985 W/m K (k_through = 1 plus 0.0013 m2K/W per pitch, series rule), rho 1768, Cv 1050; each of the 128 cells is a cellZone with its own `heatSource`.
- Walls: `externalTemperature` (h, Ta, 1.5 mm steel layer). Internal radiation is NOT modelled in 3D (the network includes it).
- Steady: SIMPLE (steadyState ddt), upwind, relaxation p_rgh 0.7, U 0.2, h 0.6, solid e 0.9.
- Transient: PIMPLE, Euler, 1 outer / 2 correctors, maxCo 3 (raised to 5 at t ~ 2,000 s to speed up; no instability seen).
