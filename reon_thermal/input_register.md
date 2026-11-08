# Input register

Classes: **MP** manufacturer-published (REON pages and slides) · **US** user-supplied (the challenge brief) · **CAL** calibrated (fitted to our own 3D runs) · **AA** analyst-assumed (us). Values live in `model/params.py` (single source for every model).

| Quantity | Value | Class | Source / note |
|---|---|---|---|
| Rated power / energy | 30 kW / 60 kWh | MP | REON EBS Na+ (slides, "Who we are") |
| Chemistry | sodium-ion, UL 1973 / 9540 / 9540A | MP | REON; subtype not published |
| Cell count, modules | 128 cells, 8 modules x 16 | US | brief |
| Cell size | 174.7 (y) x 71.7 (x) x 207 (z) mm | US | brief |
| Cell density, cp | 1,773 kg/m3, 1,050 J/kg K | US | brief |
| Cell k | diag(k_through, 25, 25) W/m K, k_through 0.5-3 (base 1) | US | brief |
| Interface | 0.2 mm at 0.2 W/m K + 0.0003 = 0.0013 m2K/W, counted once | US | brief |
| Heat per cell | 6.1 W normal, 18.3 W aged, 0 W ideal bypass | US | brief |
| Discharge | 7,200 s | US | brief |
| Cabinet | 1.30 W x 0.40 D x 2.35 H m, 8 modules, 30 mm gaps | US | brief (REON has not confirmed) |
| Module length closure | 16 x 71.7 + 15 x 0.2 = 1,150.2 mm vs 1,170 assumed; 19.8 mm = two 9.9 mm end plates, folded into the side clearances in 3D (74.9 mm each) | AA | |
| Bottom space / top space | 150 mm / 334 mm | AA | |
| Inlet / outlet | full-width front grille z 0-150 mm / roof strip over rear plenum (1.30 x 0.113 m) | AA | positions US, sizes AA |
| Supply | 0.15 m3/s at 20 C, return 0 Pa gauge, ambient 25 C | US | brief |
| External h | 5 and 10 W/m2K on walls only (combined convection + radiation) | US | brief |
| Walls | 1.5 mm steel, rho 7,850, cp 490, k 50 | AA | |
| Emissivity | 0.8 cells and walls (Sobol range 0.2-0.9) | AA | |
| Supports | 0.2 W/K per module end to the side wall (range 0-1) | AA | |
| Topology | all-series string of 128 cells | AA | NOT published; drives the 128/115 current scaling |
| Cell voltage / capacity | 3.10 V nominal, OCV 2.55-3.70 V linear in SOC; 151 Ah implied | AA | |
| Effective resistance | 1.07 mOhm (calibrated so 6.1 W at 75.6 A) | CAL | to the brief's 6.1 W |
| Bypass switch / busbar | 0.25 mOhm per switch, 0.10 mOhm per joint | AA | sweep 0.1-0.5 mOhm |
| Usable SOC window | 1.00 (sensitivity 1.05) | AA | |
| Inverter | 750 W top block (paired runs with and without) | US | |
| Through-cell lumped factor beta | 0.475 | CAL | Elmer resolved module, cell means within 0.44 K |
| Interior-peak factor gamma | 0.11 | CAL | Elmer, peak within 0.001 K |
| Forced flow split | 62 % under module 1, 41.5 % over module 8, ~0 % in the 7 gaps (of main), 31 % through side clearances | CAL | OpenFOAM A, k-omega SST |
| Forced h multiplier, gap exchange | 0.6, 0.02 W/K per column | CAL | OpenFOAM A SST, RMS 4.8 K, peak within 0.9 K |
| Passive loop (Q_circ, G_ex, h_gap) | see results/calibration_*.json | CAL | OpenFOAM C transient (if run finished) |
| Ageing activation energy | 35 kJ/mol (range 20-50) | AA | Na-ion data sparse |
| Fade | 4e-5 per full cycle + 1 %/yr calendar at 25 C | AA | ~7,500 cycles to 70 % |
| Resistance growth | R = R0 (1 + 1.5 fade/0.30) | AA | |
| Economics | $350/kWh capex, $0.12/kWh, $12/kW-month demand, 7 % discount | AA | |
| Carbon | 0.37 kg CO2/kWh grid, 65 kg CO2/kWh embodied | AA | |
| Solar | clear-sky hot site, 1,000 W/m2 roof, 600 W/m2 west wall, absorptance 0.6 | AA | pvlib not used; clear-sky shape |

## Literature values (class LIT) used by the coupled electro-thermal runs (model/lit_params.py, ec_cases.py)
| Quantity | Value | Source |
|---|---|---|
| OCV vs SOC (layered oxide / hard carbon) | 1.86, 2.31, 2.62, 2.80, 2.88, 3.01, 3.18, 3.35, 3.54, 3.67, 3.83 V at 0–100 % SOC (mean 3.02 V) | Fronc & Stefańczak, *Przegląd Elektrotechniczny* 101(8) 2025, Fig. 10 (commercial 18650, 1.3 Ah), read off the figure (±0.03 V) |
| Voltage window, nominal | 1.5–3.95 V, 3.1 V nominal, < 20 mΩ, 30 g | same paper, Table 3 |
| Series resistance vs SOC | 18.7–20.0 mΩ (1.3 Ah cell, HPPC) | same paper, Fig. 11 |
| Polarisation (dynamic) resistance vs SOC | 0.7–1.2 mΩ mid-SOC, 7.8 mΩ at 10 %, 4.3 mΩ at 100 % | same paper, Fig. 12 |
| Arrhenius activation energy, polarisation resistance | 70–75 kJ/mol (72 used) for layered oxides; NFPP less sensitive | Leeds group, *Applied Energy* 2026, doi:10.1016/j.apenergy.2026.127687 (CC BY 4.0) |
| Ohmic activation energy, ohmic/polarisation split at 2 h | 15 kJ/mol, 50 % (sensitivity 5–90 %) | AA |
| Entropic coefficient dU/dT | not tabulated in open Na-ion literature (figures only: J. Electrochem. Soc. 2023, doi:10.1149/1945-7111/ace5e5; Mercer et al., ChemPhysChem 2022) → 0, sensitivity ±0.2 mV/K | AA |
| Absolute resistance | 1.099 mΩ at 25 °C, 50 % SOC, scaled so a 30 kW / 25 °C discharge averages the brief's 6.1 W (CAL); published 18650 pulse resistance scaled by capacity = 0.17 mΩ (sensitivity) | CAL / LIT |
| Cell capacity | 155.2 Ah (60 kWh / 128 / 3.02 V mean OCV) | derived |

## Missing from REON (would change the answer)
Cell part number and datasheet; series/parallel topology and the inverter DC voltage window; usable SOC window and voltage/current limits; CAD (supports, walls, inlet/outlet sizes and positions, inverter location); fan curve; measured cell heat versus current and temperature (entropic heat); bypass-switch on-resistance and where it dissipates; measured cell and air temperatures for validation.
