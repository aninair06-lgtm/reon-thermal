#!/bin/bash
. /opt/openfoam13/etc/bashrc
T=$FOAM_TUTORIALS/multiRegion/CHT/circuitBoardCooling
for f in system/controlDict system/fvSolution system/fluid/fvSolution system/fluid/fvSchemes constant/fluid/pRef constant/fluid/physicalProperties constant/fluid/momentumTransport 0/fluid/p 0/fluid/p_rgh 0/fluid/U 0/fluid/T 0/fluid/k 0/fluid/epsilon 0/fluid/nut 0/fluid/alphat; do
  echo "#### $f"; [ -f $T/$f ] && sed '1,/^}/d' $T/$f | grep -v '^//' | grep -v '^\s*$' | head -60
done
ls $T/0/fluid $T/system
ls $FOAM_APPBIN | grep -i -E "createZones|createPatch|splitMesh|foamPostProcess|checkMesh"
