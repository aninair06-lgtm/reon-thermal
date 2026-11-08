cd ~/reon_runs && rm -rf A_sst_m15
python3 /mnt/c/Users/anina/Downloads/MITEC/reon_thermal/openfoam/gen_of_case.py A_sst_m15 --mode forced --turb kOmegaSST --iters 5000 --np 20 --mesh 1.5
cd A_sst_m15
sed -e 's/^mpirun.*//' -e 's/^reconstructPar.*//' -e 's/^touch case.foam//' Allrun > Allmesh && chmod +x Allmesh
./Allmesh > log.Allmesh 2>&1; tail -1 log.Allmesh
grep -E "cells:" log.checkMesh.air
cat > Asolve <<'EOF'
#!/bin/bash
cd "$(dirname "$0")"; . /opt/openfoam13/etc/bashrc
mpirun -np 20 foamMultiRun -parallel > log.foamMultiRun 2>&1
reconstructPar -allRegions -latestTime > log.reconstructPar 2>&1
echo SOLVE_DONE
EOF
chmod +x Asolve
