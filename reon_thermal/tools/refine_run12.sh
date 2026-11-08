cd ~/reon_runs/A_sst_m15 || exit 1
. /opt/openfoam13/etc/bashrc
rm -rf processor*
foamDictionary -entry numberOfSubdomains -set 12 system/decomposeParDict > /dev/null
decomposePar -allRegions -force > log.decomposePar 2>&1
mpirun -np 12 foamMultiRun -parallel > log.foamMultiRun 2>&1
echo "solver exit $?"
reconstructPar -allRegions -latestTime > log.reconstructPar 2>&1
grep -E "continuity" log.foamMultiRun | tail -1
echo REFINE_DONE
