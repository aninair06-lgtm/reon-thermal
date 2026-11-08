# REON: Beyond the Weakest Cell

Electro-thermal study and early-warning dashboard for one REON EBS Na+ cabinet (30 kW / 60 kWh, 128 sodium-ion cells, 8 modules × 16). All data is simulated.

**Live dashboard:** https://aninair06-lgtm.github.io/reon-thermal/

The dashboard (`reon_thermal/dashboard/index.html`, open it directly in a browser) shows a cell's fault before it shows as heat or lost capacity. Its data comes from a one-year backtest of the team's diagnostic algorithm, with five hidden faults injected into a calibrated electro-thermal model: loose tab, contact corrosion, internal damage, sodium plating and a cooling fault. OpenFOAM and Elmer thermal simulations and a 30-year life model fill in the rest. One week slider drives a cabinet-health gauge (weakest cell still in service), a cabinet map, four factor cards and a 3D pack view. REON's bypass and retirement are shown in green, often weeks before a cell runs hot. A dark band explains each fault in plain words with an action and alternatives. A thermal section covers why cells run hot, why bypass pays (+1.08 years of life and +$3,669 NPV with this cabinet's faults) and which fixes keep cells under 60 °C on the worst day. The results are reported honestly: corrosion flagged 6 weeks early, the cooling fault missed, 55 % label accuracy and one healthy cell retired by mistake.

## Layout

- `reon_thermal/model/`: models and runs (`backtest.py`, `backtest_trace.py`, `backtest_health.py`, `econ.py`, network, OpenFOAM and Elmer helpers)
- `reon_thermal/results/`: model outputs (JSON and CSV)
- `reon_thermal/dashboard/`: `page.html` is the source; `python build_data.py` inlines the results and writes the standalone `index.html`
- `reon_thermal/report/`, `figures/`, `openfoam/`, `elmer/`: report, figures and simulation cases
- `PRODUCT.md`, `DESIGN.md`, `.impeccable/`: product context, design system and design reviews

The page uses REON's logo and colour scheme.
