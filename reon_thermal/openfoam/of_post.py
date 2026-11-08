#!/usr/bin/env python3
"""Post-process a steady REON CHT case: per-cell temperatures, heat to air, H_i couplings, airflow split.

Air sampling region for T_air_reference (deliverable 2): the CHANNEL BULK next to each exposed face -
top/bottom faces: all air cells in the adjacent gap (or bottom/top space up to 0.15 m) over the cell footprint;
front/rear faces: all air cells across the plenum depth over the face span; end faces: the side clearance.
Run in WSL after: foamPostProcess -func writeCellCentres -region air|cells -latestTime
"""
import os, re, sys, json, glob
import numpy as np
sys.path.insert(0, "/mnt/c/Users/anina/Downloads/MITEC/reon_thermal/model")
import params as P

def _list(s, start, vec):
    m = re.compile(r"(\d+)\s*\(").search(s, start)
    n = int(m.group(1)); i = m.end()
    if not vec:
        j = s.index(")", i)
        return np.array(s[i:j].split(), float)[:n], j
    j = i; out = []
    body_end = s.index("\n)", i)
    txt = s[i:body_end]
    v = np.array(re.sub(r"[()]", " ", txt).split(), float).reshape(-1, 3)[:n]
    return v, body_end

def read_field(path, vec=False):
    s = open(path).read()
    k = s.index("internalField")
    seg = s[k:s.index("\n", k)]
    if "nonuniform" in seg:
        internal, end = _list(s, k, vec)
    else:
        val = re.search(r"uniform\s+(\([^)]*\)|[-\d.eE+]+)", seg).group(1)
        internal = np.array(val.strip("()").split(), float); end = k
    patches = {}
    bf = s.index("boundaryField", end)
    for m in re.finditer(r"\n    (\w+)\n    \{(.*?)\n    \}", s[bf:], re.S):
        name, body = m.group(1), m.group(2)
        vm = re.search(r"\bvalue\s+nonuniform", body)
        if vm:
            arr, _ = _list(body, vm.end(), vec)
            patches[name] = arr
    return internal, patches

def main(case):
    meta = json.load(open(os.path.join(case, "case_meta.json")))
    times = sorted([d for d in os.listdir(case) if re.fullmatch(r"[0-9.]+", d) and d != "0"], key=float)
    t = times[-1]
    Ca, Cap = read_field(f"{case}/{t}/air/C", vec=True)
    Ta, Tap = read_field(f"{case}/{t}/air/T")
    Ua, _ = read_field(f"{case}/{t}/air/U", vec=True)
    Cs, Csp = read_field(f"{case}/{t}/cells/C", vec=True)
    Ts, Tsp = read_field(f"{case}/{t}/cells/T")
    whf = None
    wp = f"{case}/{t}/air/wallHeatFlux"
    if os.path.exists(wp):
        _, whfp = read_field(wp)
        whf = whfp.get("air_to_cells")
    Ta -= 273.15; Ts -= 273.15
    Tsurf = Tsp["cells_to_air"] - 273.15
    Cf = Csp["cells_to_air"]
    n = meta["counts"]
    dx_c = P.PITCH_X / n["ncx"]; dy_c = P.CELL_Y / n["ny_c"]; dz_c = P.CELL_Z / n["nz_m"]
    # face orientation and area
    eps = 1e-6
    zt = np.array([P.module_z0(m) + P.CELL_Z for m in range(1, 9)]); zb = np.array([P.module_z0(m) for m in range(1, 9)])
    isz = np.isclose(Cf[:, 2][:, None], np.r_[zb, zt][None, :], atol=eps).any(1)
    isy = np.isclose(Cf[:, 1], P.Y0, atol=eps) | np.isclose(Cf[:, 1], P.Y0 + P.CELL_Y, atol=eps)
    isx = ~isz & ~isy
    area = np.where(isz, dx_c * dy_c, np.where(isy, dx_c * dz_c, dy_c * dz_c))
    # face -> cell id
    mod = np.clip(np.searchsorted(zb, Cf[:, 2] + eps, side="right") - 1, 0, 7)
    col = np.clip(((Cf[:, 0] - P.X0) / P.PITCH_X).astype(int), 0, 15)
    # cell centre -> cell id
    ms = np.clip(np.searchsorted(zb, Cs[:, 2], side="right") - 1, 0, 7)
    cs = np.clip(((Cs[:, 0] - P.X0) / P.PITCH_X).astype(int), 0, 15)
    rows = []
    heat = json.load(open(os.path.join(case, "heat_map.json")))
    for m in range(8):
        for c in range(16):
            cid = P.cell_id(m + 1, c + 1)
            sel = (ms == m) & (cs == c)
            fsel = (mod == m) & (col == c)
            A = area[fsel]
            Tsurf_m = float((Tsurf[fsel] * A).sum() / A.sum())
            Q_air = float(-(whf[fsel] * A).sum()) if whf is not None else float("nan")   # wallHeatFlux on air side: + into air? sign checked below
            # air reference: channel bulk adjacent to each exposed face
            x0 = P.X0 + c * P.PITCH_X; x1 = x0 + P.PITCH_X
            z0 = P.module_z0(m + 1); z1 = z0 + P.CELL_Z
            inx = (Ca[:, 0] > x0) & (Ca[:, 0] < x1)
            iny = (Ca[:, 1] > P.Y0) & (Ca[:, 1] < P.Y0 + P.CELL_Y)
            above = (Ca[:, 2] > z1) & (Ca[:, 2] < z1 + (P.GAP_Z if m < 7 else 0.15))
            below = (Ca[:, 2] < z0) & (Ca[:, 2] > z0 - (P.GAP_Z if m > 0 else 0.15))
            inz = (Ca[:, 2] > z0) & (Ca[:, 2] < z1)
            front = (Ca[:, 1] < P.Y0); rear = (Ca[:, 1] > P.Y0 + P.CELL_Y)
            regs = [(inx & iny & above, P.CELL_X * P.CELL_Y), (inx & iny & below, P.CELL_X * P.CELL_Y),
                    (inx & inz & front, P.CELL_X * P.CELL_Z), (inx & inz & rear, P.CELL_X * P.CELL_Z)]
            if c == 0: regs.append(((Ca[:, 0] < P.X0) & inz & iny, P.CELL_Y * P.CELL_Z))
            if c == 15: regs.append(((Ca[:, 0] > P.X0 + P.MOD_LEN) & inz & iny, P.CELL_Y * P.CELL_Z))
            Tref = sum(Ta[r].mean() * w for r, w in regs) / sum(w for _, w in regs)
            rows.append(dict(cell_id=cid, module_id=m + 1, T_volume_mean_C=float(Ts[sel].mean()), T_internal_max_C=float(Ts[sel].max()),
                             T_surface_mean_C=Tsurf_m, T_air_reference_C=float(Tref), heat_generation_W=float(heat[cid]),
                             heat_to_air_W=Q_air, exposed_area_m2=float(A.sum())))
    Qair = np.array([r["heat_to_air_W"] for r in rows])
    if np.nansum(Qair) < 0:
        for r in rows: r["heat_to_air_W"] *= -1
    for r in rows:
        r["heat_to_neighbours_W"] = r["heat_generation_W"] - r["heat_to_air_W"]   # steady: rest goes by conduction
        dT = r["T_surface_mean_C"] - r["T_air_reference_C"]
        r["H_W_per_K"] = r["heat_to_air_W"] / dT if abs(dT) > 0.05 else float("nan")
        r["H_flag_small_dT"] = abs(dT) <= 0.3
    # airflow split: y-flux leaving each channel at the rear edge of the modules
    dy_pl = P.Y0 / n["ny_pl"]
    rearrow = (Ca[:, 1] > P.Y0 + P.CELL_Y) & (Ca[:, 1] < P.Y0 + P.CELL_Y + dy_pl)
    inmodx = (Ca[:, 0] > P.X0) & (Ca[:, 0] < P.X0 + P.MOD_LEN)
    dz_cells = {"b": P.Z_BOTTOM / n["nz_b"], "g": P.GAP_Z / n["nz_g"], "t": P.TOP_SPACE / n["nz_t"]}
    chans = []
    zs = [(0.0, P.Z_BOTTOM, "b")] + [(P.module_z0(j) + P.CELL_Z, P.module_z0(j + 1), "g") for j in range(1, 8)] + [(P.Z_TOP_OF_STACK, P.CAB_H, "t")]
    for z0, z1, kind in zs:
        s = rearrow & inmodx & (Ca[:, 2] > z0) & (Ca[:, 2] < z1)
        chans.append(float((Ua[s, 1] * dx_c * dz_cells[kind]).sum()))
    side = (Ca[:, 0] < P.X0) | (Ca[:, 0] > P.X0 + P.MOD_LEN)
    zmid = P.module_z0(4) + P.CELL_Z / 2
    dzm = P.CELL_Z / n["nz_m"]; dxs = P.X0 / n["nxc"]; dys = None
    sel = side & (np.abs(Ca[:, 2] - zmid) < dzm / 2)
    # side clearance cells: y spacing differs per section; approximate with the cell's own y spacing
    ycell = np.where(Ca[sel, 1] < P.Y0, P.Y0 / n["ny_pl"], np.where(Ca[sel, 1] > P.Y0 + P.CELL_Y, P.Y0 / n["ny_pl"], dy_c))
    Qside = float((Ua[sel, 2] * dxs * ycell).sum())
    out = dict(case=os.path.basename(case), time=t, meta=meta, cells=rows, channel_flow_m3s=chans,
               side_flow_m3s=Qside, T_air_out_C=float(np.nan), summary={})
    Tm = np.array([r["T_volume_mean_C"] for r in rows]); Tx = np.array([r["T_internal_max_C"] for r in rows])
    out["summary"] = dict(T_mean_avg=float(Tm.mean()), T_mean_min=float(Tm.min()), T_mean_max=float(Tm.max()),
                          T_int_max=float(Tx.max()), hottest=rows[int(Tx.argmax())]["cell_id"],
                          total_heat_to_air=float(np.nansum([r["heat_to_air_W"] for r in rows])),
                          channel_share=[c / max(sum(chans), 1e-12) for c in chans], side_share=2 * Qside / meta.get("flow", 1) if meta.get("flow") else None)
    os.makedirs("/mnt/c/Users/anina/Downloads/MITEC/reon_thermal/results/openfoam", exist_ok=True)
    json.dump(out, open(f"/mnt/c/Users/anina/Downloads/MITEC/reon_thermal/results/openfoam/{os.path.basename(case)}.json", "w"), indent=1)
    print(json.dumps(out["summary"], indent=1))

if __name__ == "__main__":
    main(os.path.expanduser(sys.argv[1]))
