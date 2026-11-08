# Run manifest

| Run | Tool | Status | Checks |
|---|---|---|---|
| Stage 0 hand checks | Python | done | 21/21 within 1.1 % |
| A_sst_m1 forced steady k-omega SST, 98,784 cells | OpenFOAM 13 | done (4000 it) | continuity 7e-6; heat to air 780.8 W of 780.8 |
| A_lam_m1 forced steady laminar | OpenFOAM 13 | done (14000 it) | peak oscillates ±0.03 K; heat to air 779.7 W |
| C_lam_m1 passive 40 C steady (continuous duty, no radiation) | OpenFOAM 13 | done (8000 it) | infinite-duration bound only, not used for the 2 h answer |
| Bt_lam_m1 passive 25 C, 2 h transient | Python | done | left-out check of the network (B_leftout_check.json) |
| Ct_lam_m1 passive 40 C, 2 h transient | OpenFOAM 13 | done | per-cell histories every 60 s |
| Dt_lam_m1 = Ct + 13 bypassed (constant power 7.6 W) | OpenFOAM 13 | done | 13 chosen from the network C basis (see D_heatmap_network13_ids.json) |
| OpenFOAM A_sst_m067 / A_sst_m15 (coarse 25,916 / fine 306,432 cells) | OpenFOAM 13 | done (5000 it each) | 3-grid GCI 7.2 %, extrapolated peak 61.5 C; fine-medium -2.41 K FAILS 0.5 K |
| OpenFOAM A_sst_half (0.075 m3/s, medium mesh) | OpenFOAM 13 | done (5000 it) | peak 72.0 C vs 67.6 C at full flow |
| OpenFOAM radiation | OpenFOAM 13 | NOT MODELLED | network carries radiation; 3D comparisons run with radiation off in the network |
| Elmer bench_x / bench_y | Elmer 26.2 | done | 1e-5 K / 0 K vs analytic |
| Elmer module r1 / r1.5 / r2, dt 60 / 30, bypass | Elmer 26.2 | done | grid 0.03 K, dt 0.0001 K |
| Network: 30 cases + 3-day cycle | Python | done | energy closure < 1e-4 % |
| Network calibration forced (220 GPU combos) | Python | done | RMS 4.8 K |
| Network calibration passive transient (GPU) | Python | done | RMS 0.094 K over 7200 s |
| Shapley attribution (256 GPU runs) | Python | done | sum of shares = total exactly |
| Sobol (SALib, GPU) | Python | done | 6656 runs |
| Bypass sets hotspot vs random (2,065 GPU runs) | Python | done |  |
| Electrical feasibility (SOC tracked) | Python | done | 16 runs |
| Lifetime / economics Monte Carlo | Python | done | 300 packs x 2, one-at-a-time sensitivity |
| PyBaMM Chayambuka2022 heat cross-check (C/50, C/4, C/2, 1C) | Python | done | irreversible heat from equilibrium-curve difference; entropic heat not included |
| Stage 4 beyond-bypass ideas (18 network runs) + PyBaMM-heat what-if | Python | done | energy closure < 1e-4 % |
| CoolProp, pvlib | Python | NOT USED | air properties constant; clear-sky solar shape |

## Open assumptions
See input_register.md, section 'Missing from REON'.
