---
version: 1
slug: "reon-thermal-dashboard-index-html"
primary_target: "reon_thermal/dashboard/index.html"
related_targets: []
---

# REON cabinet dashboard

Mode: Operate. Audience: REON battery and operations engineers. Job: see which cells are developing a fault, why, and what to do (keep / bypass / other strategy). Proof: one-year simulated backtest with five injected faults plus the thermal simulations. Constraint: every number is simulated and the page says so.

## Direction contract

THESIS: A cabinet reads like a credit score: one health number up top, the factors that move it beneath, the history and the offers in a dark band. It refuses the engineering-console default of dense tables and alarm lists.

OWN-WORLD: REON brand on the reference layout: off-white #E4E9E1 ground with a soft neon-green glow, white glass cards (16 px radius) with soft offset shadows, big light-weight numerals, REON-green pill tabs and wordmark, a REON-green #0A1A11 lower band holding the chart and action cards, neon green #00D000 for anything REON reads or does. Cell heat keeps one warm sequential ramp; fault kinds use five fixed hues.

STORY: Engineers see cabinet health for the scrubbed week: the weakest cell still in service falls from 98.7 in week 1 to 88.2 at year end, with the gap to no bypass beside it (+8.6 at year end; it jumps when REON pulls the plating and damaged cells). The user asked for it to follow the slider and to count only cells in service; projected life and "Why bypass pays" use the life model with this cabinet's own faults (+1.08 yr). Then they see the 8x16 cabinet with REON's green bypass rings, scrub the year and watch rings appear before the cells heat. Below, the same year plays in 3D: cells shrink as they lose health, warm as they heat, and REON pulls failing cells forward out of their shelf in green, often weeks before they run hot. Then they read each fault's cause as one or two plain sentences and the recommended action with alternatives.

FIRST VIEWPORT: Left: health gauge (70-100 % SOH arc, end of life marked). Right: cabinet cell map with week scrubber and play. Below: four factor cards. Simulated-data chip in the top bar.

FORM: pinned reference layout (user-supplied inspo), adapted one-to-one; the concept roll was not run because the user pinned the layout. seed: none (unavailable)

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
