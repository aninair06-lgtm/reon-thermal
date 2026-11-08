. ~/reon_venv/bin/activate
python - <<'EOF'
import numpy, scipy, matplotlib, cupy, SALib, numba, pandas, sys
from importlib.metadata import version
print("python", sys.version.split()[0])
for m in ("numpy", "scipy", "matplotlib", "cupy-cuda12x", "SALib", "numba", "pandas"):
    try: print(m, version(m))
    except Exception as e: print(m, "?")
print("CUDA runtime", cupy.cuda.runtime.runtimeGetVersion())
EOF
. /opt/openfoam13/etc/bashrc
echo "OpenFOAM $WM_PROJECT_VERSION package $(dpkg-query -W -f='${Version}' openfoam13)"
echo "Elmer $(dpkg-query -W -f='${Version}' elmerfem-csc-eg)"
lsb_release -ds
uname -r
