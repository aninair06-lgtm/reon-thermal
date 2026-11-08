#!/bin/bash
. /opt/openfoam13/etc/bashrc
echo "#### heatSource usage"
grep -B2 -A40 "^Usage" $FOAM_SRC/fvModels/derived/heatSource/heatSource.H 2>/dev/null | head -50 || find $FOAM_SRC -name "heatSource.H"
find $FOAM_SRC -name "heatSource.H"
echo "#### constAnisoSolidTransport"
grep -B2 -A30 "Description" $FOAM_SRC/thermophysicalModels/solidThermo/solidSpecie/transport/constAniso/constAnisoSolidTransport.H | head -40
echo "#### externalTemperature BC"
find $FOAM_SRC -name "externalTemperatureFvPatchScalarField.H" | head -1 | xargs grep -A40 "Usage" | head -50
echo "#### foamMultiRun / splitMeshRegions"
which foamMultiRun splitMeshRegions topoSet
nproc
