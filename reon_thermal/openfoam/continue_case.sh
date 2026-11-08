#!/bin/bash
# continue_case.sh NAME NEW_END NP : continue a decomposed steady run to NEW_END iterations
cd ~/reon_runs/$1 || exit 1
. /opt/openfoam13/etc/bashrc
foamDictionary -entry endTime -set $2 system/controlDict > /dev/null
for p in processor*; do foamDictionary -entry endTime -set $2 $p/../system/controlDict > /dev/null 2>&1; done
mpirun -np $3 foamMultiRun -parallel > log.foamMultiRun.cont 2>&1
reconstructPar -allRegions -latestTime > log.reconstructPar.cont 2>&1
echo "$1 CONT EXIT=$?"
