#!/bin/bash
cd ~/reon_runs && rm -rf A_sst_half
python3 /mnt/c/Users/anina/Downloads/MITEC/reon_thermal/openfoam/gen_of_case.py A_sst_half --mode forced --turb kOmegaSST --iters 5000 --np 2 --flow 0.075 > /dev/null
cd A_sst_half && ./Allrun > log.Allrun 2>&1
tail -1 log.Allrun
bash /mnt/c/Users/anina/Downloads/MITEC/reon_thermal/openfoam/post_case.sh A_sst_half 2>&1 | grep -E "cellsTmax|T_int_max|T_mean_avg|hottest"
echo HALF_DONE
