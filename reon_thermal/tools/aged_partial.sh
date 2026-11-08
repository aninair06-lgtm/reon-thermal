. ~/reon_venv/bin/activate
for c in Et_aged Et_aged_byp; do python /mnt/c/Users/anina/Downloads/MITEC/reon_thermal/openfoam/of_post_transient.py ~/reon_runs/$c; done
cd /mnt/c/Users/anina/Downloads/MITEC/reon_thermal/results/openfoam
python - <<'EOF'
import json, numpy as np
a=json.load(open('Et_aged_cells.json')); b=json.load(open('Et_aged_byp_cells.json')); c=json.load(open('Ct_lam_m1_cells.json'))
n=min(len(a['t_s']),len(b['t_s']))-1; t=a['t_s'][n]
ids=[f'M{m:02d}_C{k:02d}' for m in range(1,9) for k in range(1,17)]; j=ids.index('M07_C08')
A=np.array(a['T_max'])[:n+1]; B=np.array(b['T_max'])[:n+1]; C=np.array(c['T_max'])[:n+1]
out=dict(t_s=t, aged_peak=float(A.max()), aged_cell_peak=float(A[:,j].max()), byp_peak=float(B.max()), byp_cell_peak=float(B[:,j].max()),
         C_peak_same_time=float(C.max()), aged_peak_cell=ids[int(A.max(0).argmax())], byp_peak_cell=ids[int(B.max(0).argmax())])
json.dump(out, open('E_aged_3D_partial.json','w'), indent=1); print(out)
EOF
