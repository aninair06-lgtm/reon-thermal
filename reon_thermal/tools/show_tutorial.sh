#!/bin/bash
# Print the key dictionaries of the OpenFOAM-13 heatedDuct CHT tutorial (reference for our case setup)
cd /opt/openfoam13/tutorials/multiRegion/CHT/heatedDuct || exit 1
for f in Allrun system/controlDict constant/heater/fvModels constant/heater/physicalProperties \
         constant/fluid/physicalProperties constant/fluid/momentumTransport system/fvSolution \
         system/fluid/fvSolution system/heater/fvSolution system/heater/fvSchemes system/fluid/fvSchemes \
         0/fluid/T 0/fluid/U 0/fluid/p_rgh 0/fluid/p 0/heater/T 0/metal/T; do
  echo "#### $f"
  sed '1,/^}/d' "$f" | grep -v '^//' | grep -v '^\s*$'
done
