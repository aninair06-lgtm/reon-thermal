# Answer: REON EBS cabinet, cell temperatures and selective bypass

_Generated 2026-11-07 22:57 from results/. Conditional on the assumptions in input_register.md (all-series string, assumed geometry, no REON CAD or measured heat)._

## The four questions

1. **Variation and hottest cells.** Fan on (3D OpenFOAM, steady, full power): cell means 45.1–67.5 °C, interior max 67.6 °C at M07_C08 (k-omega SST); laminar gives 90.9 °C at M08_C09. The 7 inter-module gaps carry <1 % of the flow, so modules 6–7 in the middle columns run hottest. Sealed 40 °C, 2 h: 3D transient peak 48.9 °C at M08_C04 (t = 7200 s), spread 0.63 K at the end; network peak 48.5 °C at M06_C08 at 7200 s, spread 1.1 K. Hottest = end of discharge in every passive case.
2. **Can bypass keep all interiors < 60 °C without cabinet cooling?** Normal starts: yes, and no bypass is needed (C peak 48.5 °C). Hot start (55 °C at 40 °C ambient): no; no-bypass 61.6 °C, 13 fixed 63.5 °C (constant power) / 61.5 °C (constant current), adaptive 63.3 / 61.5 °C. Bypass works for a cell that is hot because of its own heat: aged cell 56.2 → 48.5 °C. 3D check of D (13 bypassed, constant power): peak 51.0 °C vs C 48.9 °C.
3. **Cost and feasibility.** 13 bypassed at constant power: heat 869 W vs 780.8 W; with SOC tracking 30 kW lasts 1.76 h (52.8 kWh) vs 1.96 h (58.9 kWh) unbypassed; string 416→280 V, 72→107 A; switch loss 43 Wh. Constant current: 26.95 kW. 30 kW x 2 h is met with k ≤ 4 only with a 5 % larger usable window. Not '30 kW for 2 h' at k = 13.
4. **When bypass is not enough.** When the temperature is set by the enclosure (hot start, hot site): derate to 90 % (27 kW) keeps the hot-start case at 60.0 °C. With an aged cell a fixed string needs 19.5 kW; bypassing that cell allows 26.8 kW (+7.3 kW, 14.5 kWh per hot day).

## Decision table (network, calibrated to OpenFOAM and Elmer; peak = max interior over 0–7200 s)

| Case | All < 60 °C | Limiting cell @ time | Margin K | Energy kWh | Avg kW | Heat W (end) | Bypassed | Energy closure |
|---|---|---|---|---|---|---|---|---|
| A forced 25 C (network, 3D-calibrated) | yes | M07_C08 @ 7200 s | +27.9 | 60.0 | 30.00 | 781 | 0 | -0.0000 % |
| B passive 25 C, h=5 | yes | M06_C08 @ 7200 s | +26.5 | 60.0 | 30.00 | 781 | 0 | -0.0000 % |
| C passive 40 C, h=5 | yes | M06_C08 @ 7200 s | +11.5 | 60.0 | 30.00 | 781 | 0 | +0.0000 % |
| C passive 40 C, h=10 | yes | M06_C08 @ 7200 s | +11.6 | 60.0 | 30.00 | 781 | 0 | +0.0000 % |
| D: C + 13 hottest bypassed, constant power | yes | M03_C05 @ 7200 s | +9.5 | 60.0 | 30.00 | 869 | 13 | +0.0000 % |
| D: same, constant current | yes | M03_C05 @ 7200 s | +11.5 | 53.9 | 26.95 | 701 | 13 | +0.0000 % |
| D adaptive controller (constant power) | yes | M06_C08 @ 7200 s | +11.5 | 60.0 | 30.00 | 781 | 0 | +0.0000 % |
| Hot start 55 C @ 40 C, no bypass | NO | M06_C08 @ 7200 s | -1.6 | 60.0 | 30.00 | 781 | 0 | +0.0000 % |
| Hot start + 13 fixed, constant power | NO | M03_C07 @ 7200 s | -3.5 | 60.0 | 30.00 | 869 | 13 | +0.0000 % |
| Hot start + 13 fixed, constant current | NO | M03_C07 @ 7200 s | -1.5 | 53.9 | 26.95 | 701 | 13 | -0.0000 % |
| Hot start + adaptive, constant power | NO | M05_C08 @ 7200 s | -3.3 | 60.0 | 30.00 | 869 | 13 | +0.0000 % |
| Hot start + adaptive, constant current | NO | M05_C08 @ 7200 s | -1.5 | 54.5 | 27.27 | 702 | 13 | -0.0000 % |
| Hot start, derate to 95 % | NO | M06_C08 @ 7200 s | -0.7 | 57.0 | 28.50 | 705 | 0 | +0.0000 % |
| Hot start, derate to 90 % | yes | M06_C08 @ 7200 s | +0.0 | 54.0 | 27.00 | 632 | 0 | +0.0000 % |
| Hot start, derate to 80 % | yes | M06_C08 @ 7200 s | +1.5 | 48.0 | 24.00 | 500 | 0 | +0.0000 % |
| C + one aged cell (3x R) in hot zone | yes | M06_C08 @ 7200 s | +3.8 | 60.0 | 30.00 | 793 | 0 | +0.0000 % |
|   ... bypass that cell (constant current) | yes | M04_C11 @ 7200 s | +11.5 | 59.5 | 29.77 | 775 | 1 | +0.0000 % |
|   ... bypass that cell (constant power) | yes | M04_C11 @ 7200 s | +11.4 | 60.0 | 30.00 | 787 | 1 | +0.0000 % |
| Hot start + aged cell | NO | M06_C08 @ 7200 s | -9.2 | 60.0 | 30.00 | 793 | 0 | -0.0000 % |
|   ... adaptive (max 4 bypassed) | NO | M05_C11 @ 7200 s | -2.0 | 60.0 | 30.00 | 806 | 4 | +0.0000 % |
|   ... bypass that cell (constant current) | NO | M04_C10 @ 7200 s | -1.5 | 59.5 | 29.77 | 775 | 1 | -0.0000 % |
| A at half flow | yes | M07_C08 @ 7200 s | +27.5 | 60.0 | 30.00 | 781 | 0 | -0.0000 % |
| C with inverter inside (750 W) | yes | M02_C01 @ 7200 s | +5.3 | 60.0 | 30.00 | 781 | 0 | +0.0000 % |
| D with inverter inside | yes | M02_C01 @ 7200 s | +3.6 | 60.0 | 30.00 | 869 | 13 | +0.0000 % |
| D with 0.25 mOhm bypass-switch loss | yes | M03_C06 @ 7200 s | +9.5 | 60.0 | 30.00 | 892 | 13 | +0.0000 % |
| C with solar load | NO | M08_C16 @ 7200 s | -1.9 | 60.0 | 30.00 | 781 | 0 | +0.0000 % |
| D with solar load | NO | M08_C16 @ 7200 s | -3.6 | 60.0 | 30.00 | 869 | 13 | +0.0000 % |

Daily cycle (discharge 2 h, rest 4 h, charge 2.4 h at 0.83x, rest), 40 °C ambient, third day: peak 53.9 °C, cabinet mean at the start of day 3 43.2 °C.

Energy column uses prescribed-heat bookkeeping (P x t). The SOC-tracked runtime is in feasibility.json and item 3.

## Strategy
Bypass for cells that are hot because of themselves (high resistance, ageing, defects): one at a time, chosen by measured temperature or resistance (hotspot-selected beats random by ~7 K, results/gpu_studies.json). Do not bypass many cells to cool a cabinet that is uniformly hot: it raises the current and heat in every remaining cell. For hot starts, derate (≈10 %) or pre-cool; the Sobol ranking puts initial temperature first (ST 0.87).

## Uncertainty
Sobol (SALib, 6656 GPU runs, uniform inputs over stated bounds): hot-start peak 49.9–62.2 °C (5th–95th pct of the sampled range); 18 % of sampled combinations exceed 60 °C. These are ranges, not probabilities. Turbulence model alone: fan-on hot spot 67.6 (SST) vs 90.9 °C (laminar).

## Assumptions that control the conclusion
- All-series topology (sets the 128/115 current rise and the energy infeasibility).
- Initial cabinet temperature and ambient (dominant).
- No published fan curve, inlet/outlet or CAD: the gap-starving airflow is a property of the assumed geometry.
- Bypass switch resistance (0.25 mOhm: a bypassed cell still dissipates ~1.4 W).
- Ageing law (Arrhenius 35 kJ/mol) for the lifetime and economic numbers.

## Verification
- Stage 0 hand checks: 21/21 within 3 % (max 1.12 %).
- Zero-generation equilibrium: network drifts 0.0 K (passive and forced).
- Anisotropic conduction + contact benchmark (Elmer vs analytic): max error 1.1e-05 K through-plane, 0.0e+00 K in-plane.
- Same total heat in every model: 780.8 W (OpenFOAM heat to air at steady state 780.80 W SST, 778.07 W laminar; Elmer 16-cell module per-cell sources).
- Network transient energy balance (stored + walls + enthalpy + loop): |error| < 1e-4 % in every case (target 5 %, aim 1 %).
- Mesh: Elmer three meshes, peak moves -0.030 / +0.022 K (grid-convergence study, < 0.5 K). OpenFOAM three-grid study (Celik 2008; 306,432, 98,784, 25,916 cells): fan-on peak 72.55 / 67.63 / 65.21 °C, monotone, apparent order 1.32, extrapolated 61.5 °C, GCI_fine 7.2 % (band 60.5–69.9 °C). Fine-medium change -2.41 K: FAILS the 0.5 K criterion; hottest cell M07_C09, M07_C08, M07_C09; gap flow share -3.7 %, -3.8 %, +0.3 %. OpenFOAM refinement check (two meshes, 98,784 vs 306,432 cells, forced SST steady): peak 65.21 vs 67.63 °C, change -2.41 K: FAILED the 0.5 K criterion; gap flow share -3.7 % vs -3.8 %.
- Time step halved (Elmer): peak changes +0.0001 K (< 0.2 K). Network dt 10 s vs 5 s: H_hotstart +0.0034 K, E_aged_hot +0.0042 K (< 0.2 K).
- Peaks compared over the whole transient (histories in network_histories.json), not only the end.
- Left-out 3D check (network fitted to C only): D minus C hottest cell, network +1.97 K vs 3D +2.11 K; 3D end spread 0.63 K (C) vs 10.38 K (D); bypassed cells end at 42.3 °C, the other 115 at 50.7 °C vs 48.8 °C without bypass.
- Second left-out 3D check, case B (sealed, 25 °C, 2 h; network fitted to C at 40 °C only): 3D peak 33.93 °C, spread 0.63 K; network without radiation 33.99 °C (+0.05 K), with radiation 33.54 °C (-0.40 K).
- 3D half airflow (0.075 m3/s, SST, medium mesh): hottest cell 72.0 °C vs 67.6 °C at full flow; mean cell 65.1 vs 57.7 °C.
- Network vs 3D: forced steady RMS 4.8 K (peak -0.9 K); passive transient RMS 0.09 K (peak +0.00 K); vs Elmer module 0.44 K mean, 0.001 K peak after calibration.
- Validation needs measurements: cell surface thermocouples on M06–M07 and an end cell, gap and plenum air speed and temperature, inlet/outlet temperatures and flow, and a calorimetric cell heat rate vs current. Model agreement is not validation.

## Lifetime, economic and environmental (econ.py, assumptions in input_register.md)
- Service life to 70 % at a hot site: fixed string 6.25 yr, cell control 6.58 yr; with one 3x-R cell 5.7 → 6.6 yr.
- NPV gain $1114 per cabinet; LCOS (capex) 0.180 → 0.173 $/kWh.
- Embodied 3.9 t CO2 per cabinet; 0.62 → 0.59 t per service year.
- Air conditioning alternative (interior 25 °C, COP 3.6): 962 kWh/yr, 0.36 t CO2/yr, 4.4 % of throughput. AC would also slow ageing more than bypass; control's value is removing outliers, not replacing cooling.

## Stage 4: beyond bypass (network, sealed, 40 C ambient, start 55 C, aged cell M07_C08, 30 kW x 2 h)

| Idea | Peak °C | < 60 °C | Extra energy kWh/day | Type |
|---|---|---|---|---|
| Bypass aged cell + pre-cool to 45 C | 52.9 | yes | 0.24 | control + fan |
| Night pre-cooling: start at 40 C | 56.2 | yes | 0.32 | fan at night |
| Bypass aged cell + plates that melt at 57 C | 57.0 | yes | 0.00 | control + hardware |
| Same energy at half power over 4 h | 57.5 | yes | 0.00 | scheduling |
| Night pre-cooling: start at 45 C | 60.6 | NO | 0.24 | fan at night |
| Bypass aged cell + phase-change plates | 61.0 | NO | 0.00 | control + hardware |
| Bypass the aged cell | 61.6 | NO | 0.00 | control only |
| Air conditioning (0.15 m3/s supplied at 20 C) | 62.7 | NO | 0.74 | chiller |
| Phase-change plates that melt at 57 C | 63.4 | NO | 0.00 | hardware, passive |
| Turn cells so heat leaves along 25 W/m K | 63.5 | NO | 0.00 | redesign of the stack |
| Heat pipe from every cell to the rear wall (1 W/K each) | 65.5 | NO | 0.00 | hardware, passive |
| Move the aged cell to the coolest slot | 66.3 | NO | 0.00 | maintenance swap |
| Fan, no air conditioning (0.15 m3/s of 40 C air) | 66.4 | NO | 0.08 | fan |
| Chimney vent (natural draft ~0.03 m3/s, 40 C air) | 67.9 | NO | 0.00 | two grilles, no power |
| Phase-change plates in the gaps (0.25 kg/cell, melts 46 C) | 68.3 | NO | 0.00 | hardware, passive |
| Aluminium spreaders to the side walls (3 W/K per module end) | 69.1 | NO | 0.00 | hardware, passive |
| Do nothing (worst day) | 69.1 | NO | 0.00 |  |
| Reflective paint with that sun (absorptance 0.6 -> 0.2) | 69.4 | NO | 0.00 | paint |
| Worst day plus afternoon sun (dark paint, absorptance 0.6) | 72.6 | NO | 0.00 | for comparison |

Fan 40 W and AC COP 3 assumed. Coolest slot for the aged-cell move: M01_C01. Phase-change plates melting at 46 °C are already molten on a 55 °C start; at 57 °C they help.

## Heat-generation cross-check (PyBaMM, Chayambuka 2022 sodium-ion set; NOT the REON cell)
At 0.5 C the published Na-ion model turns 11.3 % of its power into heat (0.25 C: 7.8 %, 1 C: 16.8 %), about 28.5 W per cell scaled to 151 Ah, against the brief's 6.1 W (2.6 %). With that heat the network gives a normal-start peak of 79.3 °C (max 21.3 kW for < 60 °C) and a hot-start peak of 92.1 °C (max 12.5 kW). Cell heat is the assumption that controls the answer; a calorimetric measurement on a REON cell is the first validation step.

## Flow regime (why both laminar and k-omega SST)
inlet grille: Re 15,006, bottom space under M01: Re 8,035, rear plenum (top): Re 7,544, front plenum (to top space): Re 5,357, 30 mm gap (largest |flow|): Re 206. Richardson number in the front plenum 2.75 (mixed convection: buoyancy matters with the fan on). Sealed: Ra over the cabinet height 5.9e+09, on one module face 4.0e+06. forced: plenums Re 3,000-9,000 (transitional), gaps Re < 100 (laminar, buoyancy-dominated), Ri ~ 1 (mixed convection) -> run both laminar and k-omega SST and report the spread; sealed: Ra_H ~ 5e9 (transitional over the full height) but Ra < 1e7 on each module face -> laminar with gravity on.

## k_through
Layer-stack series bound (one repeat unit, wetted literature ranges): 0.66–1.46 W/m K through, 15.8–18.9 W/m K in-plane (brief: 1 and 25). Sweep (network peak °C):

| k_through | C sealed 40 °C | hot start 55 °C | C + aged cell |
|---|---|---|---|
| 0.5 | 48.49 | 61.56 | 58.81 |
| 1.0 | 48.49 | 61.56 | 56.23 |
| 2.0 | 48.49 | 61.56 | 54.15 |
| 3.0 | 48.49 | 61.56 | 53.20 |

Uniform heating does not care about k_through; the aged-cell hot spot does (it can only shed heat through its neighbours).

## Controllers (hot start 55 °C, aged cell, constant current)
- Threshold controller (T_on 55/57 °C, hysteresis 3 K, dwell 60–900 s, sensor delay 0–120 s, noise 0–2 K, ≤ 4 slots, 54 runs): peak 61.5–69.1 °C. Failure mode: with sensor noise at a hot start every cell is near the threshold, noise decides which cells take the 4 slots, and they never release, so the aged cell is never bypassed (69.1 °C = no control). Delay and dwell barely matter.

- Excess-over-module ranking with pre-emption (27 runs): 62.7–66.7 °C; no lock-up, but it acts late and releases the cell once it cools.
- Latching excess controller: 57.3–61.6 °C. Selection from the per-cell resistance estimate: always finds the aged cell at 5–20 % estimate error (61.6 °C), misses it 1 time in 6 at 50 % error.
- Rotating bypass among the k hottest cells: 62.4–63.2 °C (worse than bypassing the aged cell, 61.6 °C: rotation spends slots on cells that are hot only because of where they sit). Duty-cycle bypass of the aged cell (current allocation by bypass): 25 % 66.4, 50 % 63.6, 75 % 61.6 °C.
- Recommendation: choose by resistance or state of health (what the BMS measures per cell), latch, and reserve temperature for protection.

## Cell balancing by participation (each cell runs to its own end, ≥ 115 active)
year 0: +1.16 kWh per cycle (1.9 %), year 1: +1.12 kWh per cycle (1.9 %), year 3: +1.07 kWh per cycle (1.8 %), year 5: +1.06 kWh per cycle (1.8 %). Small for a new, uniform pack (1.5 % capacity spread assumed); the brief's 16-cell example (one 70 Ah cell among 85 Ah cells) recovers 70 → 84 Ah average-limited.

## Stage 4 on energy per year (120 hot-start days assumed)
Air conditioning year-round: 962 kWh/yr. Fan, no air conditioning (0.15 m3/s of 40 C air): 10 kWh/yr (fails); Night pre-cooling: start at 45 C: 29 kWh/yr (fails); Night pre-cooling: start at 40 C: 38 kWh/yr (passes); Air conditioning (0.15 m3/s supplied at 20 C): 89 kWh/yr (fails); Bypass aged cell + pre-cool to 45 C: 29 kWh/yr (passes).

## Deliverable 2: cell-to-air couplings H_i (results/H_couplings_A.csv)
- OpenFOAM A_sst_m1: median 0.213 W/K per cell (p10–p90 0.195–0.330), flagged small-dT cells 0; heat to air 781 W, radiation 0 W, supports 0 W.
- OpenFOAM A_sst_m15: median 0.238 W/K per cell (p10–p90 0.216–0.355), flagged small-dT cells 0; heat to air 781 W, radiation 0 W, supports 0 W.
- network (calibrated): median 0.181 W/K per cell (p10–p90 0.164–0.356), flagged small-dT cells 0; heat to air 453 W, radiation 291 W, supports 37 W.
Air reference = channel bulk next to each exposed face (definition in h_couplings.py). The 3D model has no radiation; in the network radiation carries about a third of the heat, so the 3D fan-on peaks are conservative.

## Late additions
- Sun (pvlib clear sky, Phoenix 21 June, discharge 14:00–16:00, absorptance 0.6; roof peak 1001 W/m², west wall 737 W/m²): sealed 40 °C day 61.9 °C at M08_C16 (top corner next to the sunny wall) vs 48.5 °C without sun; with 13 bypassed 63.6 °C. The sun-heated steel walls radiate into the nearest cells; the centre cell gains only ~0.7 K. Earlier sun results used a clock error that put the discharge at night and are superseded.
- CoolProp: R-32 air-conditioner COP 3.23 at 40 °C, 4.51 at 30 °C (used in Stage 4 and the annual AC energy). Air properties at operating temperature change every peak by < 0.01 K (A_forced25 +0.005 K, C_passive40 +0.001 K, H_hotstart +0.002 K).
- 3D, whole cabinet, aged cell M07_C08 (sealed 40 °C; runs stopped at 54 min for time): hottest cell 49.5 °C (the aged cell) vs 44.1 °C with it bypassed, identical to the cabinet without an aged cell at the same moment (44.1 °C); the bypassed cell itself 41.7 °C.
- 3D surface radiation (fvDOM, 32 rays, emissivity 0.8) and 3D inverter-inside runs were set up and passed 30 s smoke tests but diverged at ~300 s of the 2 h transient (energy-to-temperature inversion failure); not completed. The network carries both effects (radiation ~1/3 of heat; inverter +4.1 K at the centre cell).
## Two-way coupled electro-thermal runs with literature Na-ion parameters (results/ec_cases.json; cells.csv)
Current, voltage and SOC per cell come from the coupled model: literature OCV(SOC) and resistance SOC-shape (Fronc & Stefańczak 2025), Arrhenius resistance (Ea 72 kJ/mol polarisation, Leeds 2026; 15 kJ/mol ohmic, assumed), constant 30 kW, all-series string, cut-off 1.5 V. Resistance scaled to the brief's 6.1 W mean at 25 °C: 1.099 mΩ at 50 % SOC; capacity 155.2 Ah. The prescribed-heat results are kept in cells_prescribed_heat.csv.

| Case | Peak °C | Cell @ time | < 60 °C | Runtime h | Energy kWh | Heat first→last W (mean) |
|---|---|---|---|---|---|---|
| A_EC_forced25 | 32.5 | M07_C08 @ 7020 s | yes | 1.95 (power limit) | 58.5 | 4.8→19.0 (6.3) |
| B_EC_passive25 | 33.5 | M06_C08 @ 7030 s | yes | 1.95 (power limit) | 58.6 | 4.8→17.8 (6.1) |
| C_EC_passive40 | 44.9 | M06_C08 @ 7100 s | yes | 1.97 (power limit) | 59.2 | 2.3→10.9 (3.4) |
| D_EC_13bypassed | 45.4 | M03_C06 @ 6370 s | yes | 1.77 (power limit) | 53.1 | 2.7→12.7 (4.0) |
| H_EC_hotstart55 | 56.5 | M06_C08 @ 7140 s | yes | 1.98 (power limit) | 59.5 | 1.5→7.9 (2.4) |
| E_EC_aged | 49.9 | M07_C08 @ 7100 s | yes | 1.97 (power limit) | 59.2 | 2.4→11.0 (3.5) |
| E_EC_aged_bypassed | 44.9 | M05_C10 @ 7050 s | yes | 1.96 (power limit) | 58.8 | 2.4→11.1 (3.5) |
| E_EC_aged_hotstart | 60.3 | M07_C08 @ 7140 s | NO | 1.98 (power limit) | 59.5 | 1.5→8.1 (2.4) |
| E_EC_aged_hotstart_bypassed | 56.6 | M06_C10 @ 7080 s | yes | 1.97 (power limit) | 59.0 | 1.5→8.0 (2.4) |

Sensitivity (peak °C, sealed 40 °C / hot start 55 °C): dUdT +0.2 mV/K: 40.0 / 55.0; dUdT -0.2 mV/K: 51.3 / 63.5; polarisation share 0.05: 47.2 / 58.9; polarisation share 0.9: 42.9 / 55.0; published 18650 pulse resistance scaled: 40.8 / 55.0.

What changes: resistance falls as cells warm, so heat is self-limiting (about 3.4 W mean at 40 °C, 2.4 W from a 55 °C start, against the brief's fixed 6.1 W); heat rises steeply near the end of discharge (low voltage, high current, high resistance near empty); 30 kW cannot quite be held for 2 h (1.95–1.98 h). With these literature values the hot start passes without derating and bypassing the aged cell alone is enough on the worst day; the unknown entropic heat (±0.2 mV/K) can move the hot-start peak by about ±4 K, more than any other electrical parameter.

## Backtest of the team's diagnostic bypass algorithm (results/backtest.json, model/backtest.py)
One simulated year at a hot inland site (weekly ambient 12–36 °C), 52 weekly representative 30 kW discharges on the coupled electro-thermal network, synthetic BMS data (100 Hz pulse: 10 ms ohmic / 1 s slow, ±2–4 % R noise, ±0.5 K, ±3 mV OCV, ±1 % SOH) and injected faults with known ground truth: loose tab M03_C05 (week 10), contact corrosion M05_C12 (week 5), cracked electrode M02_C09 (week 20), sodium plating M06_C03 after a cold fast charge (week 4), cooling fault M07_C08 (week 26), SEI growth on all cells. Policy: safety faults retired; cooling and corrosion > 30 % bypassed; SEI cells > 25 % rested in hot weeks; at most 4 bypassed; empty cells bypassed at end of discharge (REON hardware).

| Strategy | Energy MWh/yr | Losses kWh/yr | Efficiency % | Peak °C | Faulty-cell days in service | Healthy-cell bypass weeks | Weakest cell SOH | Usable (cell control) |
|---|---|---|---|---|---|---|---|---|
| none | 19.38 | 565 | 97.17 | 46.4 | 854 | 0 | 0.796 | 0.882 |
| hottest | 19.38 | 565 | 97.17 | 46.4 | 854 | 0 | 0.796 | 0.882 |
| algo | 18.79 | 563 | 97.09 | 46.1 | 21 | 26 | 0.814 | 0.856 |
| oracle | 18.92 | 563 | 97.11 | 46.1 | 21 | 0 | 0.814 | 0.863 |

Detection delay (weeks after injection): algorithm {'M06_C03': 0, 'M03_C05': 0, 'M05_C12': 8, 'M02_C09': 0}; the cooling fault (+4 W, ≈ +2.5 K) was not detected at the 2 K threshold. Label accuracy over all cell-weeks 55 %, dominated by SEI-ageing cells labelled ambiguous / corrosion / temp effect (seasonal temperature correction spoils the √t fit); these rarely trigger bypass. A first version that explained cell temperature with end-of-discharge heat flagged 10–13 healthy cells a week as cooling faults (253 healthy-bypass weeks, −8.6 % energy); using discharge-average heat fixed it. 'Bypass the hottest' never acted (no cell above 50 °C at this site). Thresholds (15 %, 40 %, R² 0.8, 2 K) are the team's starting guesses, untuned.

## Figures (results/figs)
heatmaps_8x16.png, histories_and_bypass_timeline.png, temperature_vs_energy.png, sensitivity_and_attribution.png, streamlines_airflow_A_sst_m1.png, cell_numbering.png; the interactive cabinet, module and cause figures are in report/reon_cabinet_heat.html.
