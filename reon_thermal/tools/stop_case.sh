#!/bin/bash
# stop_case.sh NAME : stop the MPI run whose working directory is ~/reon_runs/NAME
D=$(readlink -f ~/reon_runs/$1)
for p in /proc/[0-9]*; do
  cwd=$(readlink "$p/cwd" 2>/dev/null) || continue
  if [ "$cwd" = "$D" ]; then
    cmd=$(tr '\0' ' ' < "$p/cmdline" 2>/dev/null | cut -c1-60)
    echo "stopping ${p#/proc/} $cmd"
    kill -INT "${p#/proc/}" 2>/dev/null
  fi
done
