#!/bin/bash
# run_elmer.sh NAME [gen_module args]   -> ~/reon_runs/elmer/NAME
NAME=$1; shift
mkdir -p ~/reon_runs/elmer && cd ~/reon_runs/elmer && rm -rf "$NAME"
python3 /mnt/c/Users/anina/Downloads/MITEC/reon_thermal/elmer/gen_module.py "$NAME" "$@" || exit 1
cd "$NAME"
# Solver 2 ResultOutput needs the solver-2/3 registration in Equation; keep simple: run directly
ElmerSolver case.sif > log.elmer 2>&1
echo "$NAME EXIT=$?"
grep -i -E "error|warning" log.elmer | head -5
ls results | head
tail -3 log.elmer
