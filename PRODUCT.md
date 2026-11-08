# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Static HTML/CSS/JS: one self-contained page published as a private claude.ai artifact (user's choice).

## Users

REON battery and operations engineers watching an EBS cabinet. Their job: read per-cell signals, see which cells are developing a fault, understand why, and decide which cells to bypass.

## Product Purpose

A cell-level health and early-warning dashboard for one REON EBS Na+ cabinet (30 kW / 60 kWh, 128 sodium-ion cells, 8 modules x 16). It turns per-cell BMS data into a diagnosis per cell and a bypass decision. Success: a fault is flagged before it shows up as heat in the cells and before the cell measurably degrades, and the engineer can see why in a glance.

## Positioning

REON senses and switches every cell individually. A conventional BMS can see a bad cell but cannot take it out of a series string; this dashboard pairs each diagnosis with the bypass action that REON hardware can actually take.

## Operating Context

- Per-cell BMS data: voltage, current, temperature, pack temperature, SOC, SOH, OCV; 100 Hz pulse sampling splits resistance into a 10 ms ohmic part and a 1 s slow part.
- The team's diagnostic flowchart (healthy, temperature effect, cooling fault, plating, internal damage, loose tab or weld, contact corrosion, SEI build-up, ambiguous) drives the diagnosis.
- Bypass is limited to a few cells at once at full power (about 4 at 30 kW in our feasibility study).

## Capabilities and Constraints

- Data shown is simulated (product concept mock): a one-year backtest with injected faults on the calibrated electro-thermal model of the cabinet, plus the thermal simulations. It must carry a visible "simulated data" tag.
- Diagnosis thresholds (15 %, 40 %, R² 0.8, 2 K) are starting guesses, not tuned on field data.
- Sodium-ion chemistry: the "lithium plating" branch is sodium plating.

## Brand Commitments

- Product and company name: REON (EBS Na+ cabinet). The user asked for REON's own logo and colour scheme, taken from reoncorp.com: the REON wordmark (inline SVG, currentColor) and the palette reon-green #0A1A11, off-white #E4E9E1, white #F5F7F3, neon green #00D000, greens #4CDE4C / #00A600 / #005300, 16 px radius. REON's site face is Neue Montreal (licensed, not on Google Fonts); Geist stands in.
- Layout reference supplied by the user: a credit-score dashboard concept (glassy cards, big numerals, a gradient glow, a dark lower band, pill tabs). Match its layout and finish; colour now comes from REON, not the reference. Do not reuse the reference's third-party name, logo or content.
- Keep the interface low on words. Explain a diagnosis as plain reasoning, not as the flowchart's yes/no steps.
- The page carries REON's logo. The team chose to publish the project, dashboard included, in a public GitHub repo (github.com/aninair06-lgtm/reon-thermal); it is not published as a claude.ai artifact.

## Evidence on Hand

- reon_thermal/results/backtest.json, backtest_trace.json: one-year backtest of the diagnostic algorithm (strategies, detection weeks, per-cell weekly traces).
- reon_thermal/results/ec_cases.json, network_cases.json, gpu_studies.json, openfoam/*.json, elmer_module.json: thermal and electro-thermal simulation results.
- No field data, customers or measured REON cell data exist; do not fabricate them.

## Product Principles

1. Early over late: show the warning before the heat and before the damage.
2. Show why in a few words: a fault always comes with its cause.
3. Numbers and shapes over prose.
4. Every decision is a real REON action: keep a cell, or bypass it.
5. Label simulated data honestly.
