"""Stage 0 hand checks from the brief; later model results must agree or explain why not."""
import json, os
import params as P

def checks():
    r = {}
    V = P.CELL_VOL; m = P.CELL_MASS; C = P.C_CELL
    r["cell_volume_m3"] = (V, 2.593e-3)
    r["cell_mass_kg"] = (m, 4.6)
    r["cell_C_kJ_per_K"] = (C / 1e3, 4.83)
    r["q_vol_W_per_m3_at_6.1W"] = (6.1 / V, 2353)
    r["pack_C_kJ_per_K"] = (128 * C / 1e3, 618)
    r["heat_normal_W"] = (128 * 6.1, 780.8)
    r["heat_13_bypassed_115_at_7.6_W"] = (115 * 7.6, 874)
    for q, ref in ((6.1, 9.1), (7.6, 11.3), (18.3, 27.0)):
        r[f"adiabatic_rise_2h_{q}W_K"] = (q * 7200 / C, ref)
    r["forced_air_rise_K"] = (780.8 / (0.15 * 1.19 * 1006), 4.3)
    A = P.WALL_AREA
    r["wall_area_m2"] = (A, 9.0)
    r["UA_passive_h5_W_per_K"] = (A * 5, 45)
    r["UA_passive_h10_W_per_K"] = (A * 10, 90)
    r["tau_h5_h"] = (128 * C / (A * 5) / 3600, 3.8)
    r["tau_h10_h"] = (128 * C / (A * 10) / 3600, 1.9)
    r["contact_R_m2K_per_W"] = (P.R_CONTACT, 0.0013)
    r["through_cell_R_m2K_per_W_k1"] = (P.CELL_X / 1.0, 0.0717)
    r["module_length_closure_mm"] = (P.MOD_LEN * 1e3, 1150.2)
    r["module_allowance_mm"] = (P.END_ALLOWANCE * 1e3, 19.8)
    r["energy_share_115_of_128_pct"] = (128 / 115 * 100, 111)
    out = {k: dict(computed=round(v[0], 5), brief=v[1], rel_diff_pct=round(100 * (v[0] - v[1]) / v[1], 2)) for k, v in r.items()}
    return out

if __name__ == "__main__":
    out = checks()
    for k, v in out.items():
        flag = "OK " if abs(v["rel_diff_pct"]) < 3 else "CHK"
        print(f"{flag} {k:40s} computed {v['computed']:>12} brief {v['brief']:>8}  diff {v['rel_diff_pct']:+.2f}%")
    os.makedirs(os.path.join(os.path.dirname(__file__), "..", "results"), exist_ok=True)
    json.dump(out, open(os.path.join(os.path.dirname(__file__), "..", "results", "hand_checks.json"), "w"), indent=1)
