for c in "$@"; do
  f=~/reon_runs/$c/log.foamMultiRun
  [ -f $f ] && echo "$c $(grep -E '^\s*Time =' $f | tail -1 | tr -s ' ') $(test -f ~/reon_runs/$c/log.reconstructPar && echo DONE)"
done
date
