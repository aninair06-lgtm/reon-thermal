# REON EBS cabinet: electrical-thermal study

Open, reproducible study of REON's 30 kW / 60 kWh sodium-ion cabinet (128 cells): what heats each cell, whether selective bypass keeps every cell below 60 °C, what it costs, and what that is worth.

- `report/reon_cabinet_heat.html`: the 2-page plain-language report with three interactive figures (published as an Artifact).
- `answer.md`: decision table and numbers.
- `input_register.md`, `run_manifest.md`, `environment.md`.
- `results/`: every computed number (`cells.csv` every 60 s, network cases, OpenFOAM and Elmer extracts, GPU studies, economics).

## Layout
| Folder | What |
|---|---|
| `model/` | `params.py` (all inputs), `network.py` (cell-resolved network, CPU or GPU), `hand_checks.py`, `run_cases.py` (all cases + adaptive controller, writes cells.csv), `calibrate.py`, `gpu_studies.py` (Shapley, Sobol, bypass sets), `feasibility.py`, `hotspot_tax.py`, `econ.py`, `pick_hottest.py` |
| `openfoam/` | `gen_of_case.py` (case generator: mesh, regions, 128 heat sources, steady or transient), `run_case.sh`, `continue_case.sh`, `post_case.sh`, `of_post.py`, `of_post_transient.py` |
| `elmer/` | `gen_module.py` (structured hex mesh + SIF for one module with resolved interface layers), `run_elmer.sh`, `read_vtu.py`, `check_bench.py`, `compare.py` |
| `figures/` | Anatomy-kit figure builders (`fig_cabinet.mjs`, `fig_module.mjs`, `fig_blocks.mjs`, `heat.mjs`) |
| `report/` | `build.mjs` (assembles the report from results + figures) |

## Reproduce (WSL Ubuntu 24.04, OpenFOAM 13, Elmer 26.2; GPU optional)
```bash
python3 -m venv ~/reon_venv && . ~/reon_venv/bin/activate && pip install numpy scipy matplotlib SALib "cupy-cuda12x[ctk]" numba pandas
cd reon_thermal/model && python hand_checks.py                       # Stage 0 checks
bash ../openfoam/run_case.sh A_sst_m1 --mode forced --turb kOmegaSST --iters 4000 --np 10
bash ../openfoam/run_case.sh A_lam_m1 --mode forced --turb laminar --iters 4000 --np 10 && bash ../openfoam/continue_case.sh A_lam_m1 14000 10
bash ../openfoam/run_case.sh Ct_lam_m1 --mode passive --Ta 40 --hext 5 --np 12 --transient --endtime 7200 --maxco 3
python pick_hottest.py && bash ../openfoam/run_case.sh Dt_lam_m1 --mode passive --Ta 40 --hext 5 --np 12 --transient --endtime 7200 --maxco 3 --heat ../results/D_heatmap_network13.json
bash ../openfoam/post_case.sh A_sst_m1; bash ../openfoam/post_case.sh A_lam_m1
python ../openfoam/of_post_transient.py ~/reon_runs/Ct_lam_m1; python ../openfoam/of_post_transient.py ~/reon_runs/Dt_lam_m1
bash ../elmer/run_elmer.sh bench_x_r1 --case bench; bash ../elmer/run_elmer.sh bench_y_r1 --case bench_y
for r in 1 1.5 2; do bash ../elmer/run_elmer.sh mod_aged_r$r --case module --ref $r --h 3 --Tair 40 --T0 40 --aged 8 --qaged 18.3; done
bash ../elmer/run_elmer.sh mod_aged_r1_dt30 --case module --dt 30 --aged 8 --qaged 18.3; bash ../elmer/run_elmer.sh mod_byp_r1 --case module --aged 8 --qaged 0
python ../elmer/check_bench.py && python ../elmer/compare.py
python calibrate.py forced A_sst_m1 && python calibrate.py passive_t Ct_lam_m1
python run_cases.py && python gpu_studies.py && python feasibility.py && python hotspot_tax.py && python econ.py
cd ../report && node build.mjs
```
Rename the `mod_aged_r1.5` run to `mod_aged_r15` (as used by `compare.py`).
