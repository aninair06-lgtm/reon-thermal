. ~/reon_venv/bin/activate
cd /mnt/c/Users/anina/Downloads/MITEC/reon_thermal/model
python run_cases.py 2>&1 | grep -E "C_solar|D_solar|C_passive40 |total"
python gpu_studies.py shapley 2>&1 | grep -E "Shapley"
python stage4.py 2>&1 | grep -E "sun|paint|Do nothing|Air cond"
python econ.py | grep -E "HVAC|life"
python make_figs.py | tail -1
echo RERUN_DONE
