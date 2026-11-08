. /opt/openfoam13/etc/bashrc
for c in Ct_lam_m1 Dt_lam_m1; do
  foamDictionary -entry maxCo -set ${1:-5} ~/reon_runs/$c/system/controlDict > /dev/null
  grep maxCo ~/reon_runs/$c/system/controlDict
done
