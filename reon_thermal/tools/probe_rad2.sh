. /opt/openfoam13/etc/bashrc
T=$FOAM_TUTORIALS/multiRegion/CHT/reverseBurner
echo "== gas radiationProperties"; sed '1,/^}/d' $T/constant/gas/radiationProperties | grep -v '^\s*$' | head -40
ls $T/0 $T/0/* 2>/dev/null | head -30
for f in $(ls $T/0/gas/T* $T/0/solid/T* 2>/dev/null); do echo "== $f"; sed '1,/^}/d' $f | grep -v '^\s*$' | head -40; done
for f in $(find $T -name "boundaryRadiationProperties*"); do echo "== $f"; sed '1,/^}/d' $f | grep -v '^\s*$' | head -30; done
F=$FOAM_TUTORIALS/fluid/hotRadiationRoomFvDOM
echo "== fvDOM radiationProperties"; sed '1,/^}/d' $F/constant/radiationProperties | grep -v '^\s*$' | head -30
ls $F/0; sed '1,/^}/d' $F/0/IDefault* 2>/dev/null | head -20; find $F -name "boundaryRadiationProperties*" -exec sed '1,/^}/d' {} \; | head -20
grep -rn "qr" $F/0/T* | head
