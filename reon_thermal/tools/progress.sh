for c in Ct_lam_m1 Dt_lam_m1; do
  cd ~/reon_runs/$c && echo "$c $(grep -E '^\s*Time =' log.foamMultiRun | tail -1) $(grep -E '^\s*deltaT =' log.foamMultiRun | tail -1)"
done
date
