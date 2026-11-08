#!/bin/bash
. /opt/openfoam13/etc/bashrc
echo "#### heatSource.H"
sed -n '/Description/,/SourceFiles/p' $FOAM_SRC/fvModels/general/heatSource/heatSource.H
echo "#### aniso typeName"
grep -n "typeName\|kappa" $FOAM_SRC/thermophysicalModels/solidThermo/solidSpecie/transport/constAniso/constAnisoSolidTransport*.{H,C} | head -20
grep -rn "constAnIso\|constAniso" $FOAM_SRC/thermophysicalModels/solidThermo/solidThermo/*.C | head
echo "#### anisotropic.H usage tail"
sed -n '/Usage/,/SourceFiles/p' $FOAM_SRC/ThermophysicalTransportModels/solid/anisotropic/anisotropic.H | tail -25
grep -rln "anisotropic" $FOAM_TUTORIALS | head -5
echo "#### buoyancy/radiation tutorial check"
ls $FOAM_TUTORIALS/multiRegion/CHT/circuitBoardCooling/constant/*
