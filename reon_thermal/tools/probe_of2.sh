#!/bin/bash
. /opt/openfoam13/etc/bashrc
T=$FOAM_TUTORIALS/multiRegion/CHT/shellAndTubeHeatExchanger
for f in system/controlDict system/fvSolution system/shell/fvSolution system/shell/fvSchemes system/solid/fvSolution constant/shell/physicalProperties constant/shell/momentumTransport constant/shell/thermophysicalTransport 0/shell/k 0/shell/omega 0/shell/nut 0/shell/alphat 0/shell/T; do
  echo "#### $f"; [ -f $T/$f ] && sed '1,/^}/d' $T/$f | grep -v '^//' | grep -v '^\s*$'
done
ls $T/0 $T/0/shell 2>/dev/null
echo "#### anisotropic doc"
sed -n '1,120p' $FOAM_SRC/ThermophysicalTransportModels/solid/anisotropic/anisotropic.H | grep -A60 "Description"
