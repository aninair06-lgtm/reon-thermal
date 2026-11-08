# quick 30 s tests of the new options (2 ranks)
cd ~/reon_runs
for spec in "tR --radiation" "tI --inverter 750"; do
  set -- $spec; name=$1; shift
  rm -rf $name
  python3 /mnt/c/Users/anina/Downloads/MITEC/reon_thermal/openfoam/gen_of_case.py $name --mode passive --turb laminar --Ta 40 --hext 5 --np 2 --transient --endtime 30 --maxco 5 "$@" > /dev/null || { echo "$name GEN FAIL"; continue; }
  (cd $name && ./Allrun > log.Allrun 2>&1; echo "$name $(tail -1 log.Allrun) fatal=$(grep -c -E 'FOAM FATAL' log.foamMultiRun 2>/dev/null) $(grep -E 'ExecutionTime' log.foamMultiRun | tail -1)"; grep -A3 "FOAM FATAL" log.foamMultiRun | head -6; grep -E "Solving for Ii" log.foamMultiRun | tail -1)
done
# solar sign check: roof temperature vs other walls after the tS run
cd ~/reon_runs/tS 2>/dev/null && python3 - <<'EOF'
import re, os
t = sorted([d for d in os.listdir('.') if re.fullmatch(r'[0-9.]+', d) and d != '0'], key=float)
print('tS times', t)
EOF
