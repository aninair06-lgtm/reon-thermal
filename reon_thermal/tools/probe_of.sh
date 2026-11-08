#!/bin/bash
. /opt/openfoam13/etc/bashrc
echo "--- steadyState in CHT tutorials"
grep -rl "steadyState" $FOAM_TUTORIALS/multiRegion/CHT | head
echo "--- anisotropic solid usage"
grep -rli "aniso" $FOAM_TUTORIALS | head
grep -rli "aniso" $FOAM_SRC/thermophysicalModels/solidThermo 2>/dev/null | head
ls $FOAM_SRC/ThermophysicalTransportModels 2>/dev/null
ls $FOAM_SRC/ThermophysicalTransportModels/solid 2>/dev/null
echo "--- shellAndTube controlDict/fvSolution"
sed '1,/^}/d' $FOAM_TUTORIALS/multiRegion/CHT/shellAndTubeHeatExchanger/system/fluid/fvSolution 2>/dev/null | head -60
ls $FOAM_TUTORIALS/multiRegion/CHT/shellAndTubeHeatExchanger/constant/*
cat $FOAM_TUTORIALS/multiRegion/CHT/shellAndTubeHeatExchanger/constant/solid/thermophysicalTransport 2>/dev/null
ls $FOAM_TUTORIALS/multiRegion/CHT/shellAndTubeHeatExchanger/system
