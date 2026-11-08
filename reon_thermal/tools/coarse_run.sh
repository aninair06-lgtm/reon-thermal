#!/bin/bash
# Third mesh for the grid study: 0.667x the base resolution, forced k-omega SST steady, 2 ranks
cd ~/reon_runs && rm -rf A_sst_m067
python3 /mnt/c/Users/anina/Downloads/MITEC/reon_thermal/openfoam/gen_of_case.py A_sst_m067 --mode forced --turb kOmegaSST --iters 5000 --np 2 --mesh 0.667 | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print('cells', d['ncells'], d['counts'])"
cd A_sst_m067 && ./Allrun > log.Allrun 2>&1
tail -1 log.Allrun
grep -E "continuity" log.foamMultiRun | tail -1
echo COARSE_DONE
