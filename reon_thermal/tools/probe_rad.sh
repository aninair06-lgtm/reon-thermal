. /opt/openfoam13/etc/bashrc
echo "== tutorials with radiationProperties"
grep -rl "radiationModel" $FOAM_TUTORIALS --include=radiationProperties | head -8
f=$(grep -rl "radiationModel" $FOAM_TUTORIALS/multiRegion --include=radiationProperties | head -1)
echo "== $f"; [ -n "$f" ] && sed '1,/^}/d' "$f" | grep -v '^\s*$' | head -40
d=$(dirname $(dirname "$f")) ; echo "case dir $d"
ls $d/constant/* 2>/dev/null | head -30
for x in $(find $d -name "boundaryRadiationProperties" -o -name "fvModels" | head -4); do echo "== $x"; sed '1,/^}/d' $x | grep -v '^\s*$' | head -30; done
grep -rn "qr" $d/0* 2>/dev/null | head -10
echo "== hotRadiationRoom"
h=$(find $FOAM_TUTORIALS -maxdepth 3 -type d -name "hotRadiationRoom" | head -1); echo $h
[ -n "$h" ] && { sed '1,/^}/d' $h/constant/radiationProperties | grep -v '^\s*$' | head -40; ls $h/constant; sed '1,/^}/d' $h/constant/fvModels 2>/dev/null | head; grep -A6 -E "floor|ceiling" $h/0/T* | head -20; }
