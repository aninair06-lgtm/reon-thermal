#!/bin/bash
. /opt/openfoam13/etc/bashrc
f=$(grep -rl "createPatchDict" $FOAM_TUTORIALS --include=createPatchDict | head -1)
echo "== $f"; sed '1,/^}/d' "$f" | grep -v '^\s*$' | head -50
foamInfo box 2>&1 | grep -A30 "Usage" | head -35
