#!/bin/bash
# post_case.sh NAME : convergence summary + per-cell extraction
cd ~/reon_runs/$1 || exit 1
. /opt/openfoam13/etc/bashrc
echo "=== $1"; tail -1 log.Allrun
grep -E "continuity" log.foamMultiRun | tail -1
for f in cells/cellsTmax cells/cellsTavg air/airTavg; do
  d=$(ls -d postProcessing/$f/*/ | head -1)
  awk -v n="$f" '!/^#/ {a[NR]=$0} END {printf "%s: ", n; for (i=NR-150;i<=NR;i+=50) {split(a[i],b," "); printf "it%s=%.3f ", b[1], b[2]-273.15}; print ""}' $d/volFieldValue.dat
done
foamPostProcess -region air -func writeCellCentres -latestTime > /dev/null 2>&1
foamPostProcess -region cells -func writeCellCentres -latestTime > /dev/null 2>&1
. ~/reon_venv/bin/activate
python /mnt/c/Users/anina/Downloads/MITEC/reon_thermal/openfoam/of_post.py ~/reon_runs/$1
