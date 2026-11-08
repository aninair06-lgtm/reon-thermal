for c in Ct_rad Ct_inv; do
  echo "== $c"; cd ~/reon_runs/$c
  grep -E '^\s*Time =' log.foamMultiRun | tail -1
  grep -m1 -B2 -A6 -E 'FOAM FATAL|not enough slots|There are not enough' log.foamMultiRun | head -12
done
