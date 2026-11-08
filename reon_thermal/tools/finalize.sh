#!/bin/bash
# Run after the 3D transients finish: post-process, calibrate, re-run every network/GPU study, rebuild docs.
set -e
. ~/reon_venv/bin/activate
B=/mnt/c/Users/anina/Downloads/MITEC/reon_thermal
cd $B/model
python $B/openfoam/of_post_transient.py ~/reon_runs/Ct_lam_m1
python $B/openfoam/of_post_transient.py ~/reon_runs/Dt_lam_m1
python calibrate.py passive_t Ct_lam_m1 2>&1 | grep -v Warn
python run_cases.py 2>&1 | grep -v -E "Warning|return Tw" | tail -40
python gpu_studies.py shapley bypass sobol 2>&1 | grep -v Warn | grep -E "Shapley|Sobol|peak range|t="
python feasibility.py 2>&1 | grep -v -E "Warning|return Tw" | tail -4
python hotspot_tax.py 2>&1 | grep -v -E "Warning|return Tw"
python econ.py | head -4
python dt_check.py 2>&1 | grep -v -E "Warning|return Tw"
python make_figs.py
python make_answer.py
echo FINALIZE_DONE
