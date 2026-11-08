#!/bin/bash
. /opt/openfoam13/etc/bashrc
T=$FOAM_TUTORIALS/multiRegion/CHT/circuitBoardCooling
for f in 0/fluid/p.orig 0/fluid/p_rgh.orig 0/fluid/U.orig 0/fluid/T.orig; do
  echo "#### $f"; sed '1,/^}/d' $T/$f | grep -v '^//' | grep -v '^\s*$' | head -50
done
echo "#### createZonesDict example"
find $FOAM_TUTORIALS -name createZonesDict | head -3
f=$(find $FOAM_TUTORIALS -name createZonesDict | head -1); sed '1,/^}/d' $f | head -40
find $FOAM_ETC -name "createZonesDict*" | head
