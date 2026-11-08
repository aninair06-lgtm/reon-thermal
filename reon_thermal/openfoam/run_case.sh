#!/bin/bash
# run_case.sh NAME [gen_of_case args...]  -> builds and runs ~/reon_runs/NAME
NAME=$1; shift
cd ~/reon_runs && rm -rf "$NAME"
python3 /mnt/c/Users/anina/Downloads/MITEC/reon_thermal/openfoam/gen_of_case.py "$NAME" "$@" > /dev/null || exit 1
cd "$NAME" && ./Allrun > log.Allrun 2>&1
echo "$NAME EXIT=$?"
grep -E "continuity" log.foamMultiRun | tail -1
tail -2 postProcessing/cellsTmax/*/volFieldValue.dat 2>/dev/null | tail -1
