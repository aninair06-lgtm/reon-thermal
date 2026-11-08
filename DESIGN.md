---
name: REON Cabinet Health
description: Cell-level health and early-warning dashboard for one REON EBS Na+ cabinet, in REON's own palette.
colors:
  reon-green: "#0A1A11"
  neon-green: "#00D000"
  green-bright: "#4CDE4C"
  green-mid: "#00A600"
  green-deep: "#005300"
  glow-mint: "#CCF5CC"
  off-white: "#E4E9E1"
  reon-white: "#F5F7F3"
  card-solid: "#F9FAF8"
  card-glass: "rgba(245,247,243,.66)"
  ink-2: "#4A554F"
  ink-3: "#535E58"
  band-ink-2: "#B6BAB4"
  night: "#030705"
  band-night: "#0E2417"
  card-solid-night: "#0E1C14"
  ok: "#066316"
  warn: "#8A5208"
  bad: "#A8281F"
  bad-on-band: "#FF7B6E"
  heat-cold: "#9FB6C9"
  heat-0: "#DCE2D8"
  heat-1: "#FFD7A3"
  heat-2: "#FFAA52"
  heat-3: "#EE6A17"
  heat-4: "#B8321D"
  band-warm: "#FFC24A"
  band-heat: "#FF7A45"
  band-health: "#86B6FF"
  fault-tab: "#7457F5"
  fault-corrosion: "#0A86A8"
  fault-damage: "#CF3779"
  fault-plating: "#3B5BDB"
  fault-cooling: "#A86A12"
typography:
  display:
    fontFamily: "Geist, 'Neue Montreal', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Arial, sans-serif"
    fontSize: "64px"
    fontWeight: 300
    lineHeight: 1
    letterSpacing: "-0.045em"
    fontFeature: "tnum"
  numeral:
    fontFamily: "Geist, 'Neue Montreal', ui-sans-serif, system-ui, sans-serif"
    fontSize: "40px"
    fontWeight: 300
    lineHeight: 1
    letterSpacing: "-0.045em"
    fontFeature: "tnum"
  headline:
    fontFamily: "Geist, 'Neue Montreal', ui-sans-serif, system-ui, sans-serif"
    fontSize: "30px"
    fontWeight: 450
    letterSpacing: "-0.03em"
  title:
    fontFamily: "Geist, 'Neue Montreal', ui-sans-serif, system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 550
    letterSpacing: "-0.01em"
  body:
    fontFamily: "Geist, 'Neue Montreal', ui-sans-serif, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.45
    fontFeature: "tnum"
  label:
    fontFamily: "Geist, 'Neue Montreal', ui-sans-serif, system-ui, sans-serif"
    fontSize: "12.5px"
    fontWeight: 500
rounded:
  bar: "6px"
  tip: "10px"
  card: "16px"
  band: "32px"
  pill: "999px"
spacing:
  gutter: "16px"
  grid-gap: "20px"
  card-pad: "22px"
  section: "56px"
components:
  card:
    backgroundColor: "{colors.card-glass}"
    textColor: "{colors.reon-green}"
    rounded: "{rounded.card}"
    padding: "22px"
  band-card:
    backgroundColor: "rgba(255,255,255,.045)"
    textColor: "{colors.reon-white}"
    rounded: "{rounded.card}"
    padding: "22px"
  tab:
    textColor: "{colors.ink-2}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "8px 16px"
  tab-active:
    backgroundColor: "{colors.reon-green}"
    textColor: "{colors.reon-white}"
    rounded: "{rounded.pill}"
    padding: "8px 16px"
  pill-toggle:
    textColor: "{colors.band-ink-2}"
    rounded: "{rounded.pill}"
    padding: "7px 13px"
  pill-toggle-pressed:
    backgroundColor: "{colors.reon-white}"
    textColor: "{colors.reon-green}"
    rounded: "{rounded.pill}"
    padding: "7px 13px"
  chip-ok:
    backgroundColor: "rgba(0,166,0,.13)"
    textColor: "{colors.ok}"
    rounded: "{rounded.pill}"
    padding: "4px 10px"
  chip-warn:
    backgroundColor: "rgba(200,130,20,.15)"
    textColor: "{colors.warn}"
    rounded: "{rounded.pill}"
    padding: "4px 10px"
  chip-bad:
    backgroundColor: "rgba(194,53,42,.12)"
    textColor: "{colors.bad}"
    rounded: "{rounded.pill}"
    padding: "4px 10px"
  button-band:
    backgroundColor: "rgba(255,255,255,.09)"
    textColor: "{colors.reon-white}"
    rounded: "{rounded.pill}"
    padding: "8px 14px"
  button-play:
    backgroundColor: "{colors.reon-green}"
    textColor: "{colors.reon-white}"
    rounded: "{rounded.pill}"
    size: "42px"
---

# Design System: REON Cabinet Health

## Overview

**Creative North Star: "The Cabinet Credit Score"**

One health number up top, the factors that move it beneath, the history and the offers in a dark band. The world is REON's own: an off-white ground lit by a soft neon-green glow, frosted white glass cards with 16px corners, big light numerals, and a REON-green band that the page descends into for the early-warning story. It reads as a calm consumer-grade dashboard laid over engineering data, not an engineering console of tables and alarm lists.

Colour carries meaning, never decoration. Green is REON's voice: whatever REON reads or does (its signal, its bypass rings, its flags, the accent on controls) is green. Heat has its own warm ramp and never borrows brand green. Fault kinds each own one fixed hue that follows them across pills, dots, 3D tags and timelines; bypass rings are always REON green, because a bypass is REON acting. Words are few; numbers and shapes do the talking, and a diagnosis is one or two plain sentences.

Both themes are first-class: a light theme by default and a dark theme via `prefers-color-scheme` or `data-theme="dark"`, with every chart re-reading its colours from the tokens when the theme changes.

**Key Characteristics:**
- Off-white ground, neon-green glow, frosted glass cards (16px radius, soft offset shadow).
- A REON-green lower band with a 32px top radius holding the timeline, diagnosis and action cards.
- Big light-weight (300) tabular numerals with a small muted unit.
- Pill geometry for every control: tabs, toggles, chips, buttons, the play button.
- Charts drawn in SVG to their container's width, re-coloured from tokens on theme change.
- One authored motion moment: the year playback, where the health gauge's arc eases to each week's value, new bypass rings pop in and failing cells slide out of their shelf in the 3D pack.

## Colors

REON's palette (reoncorp.com) carries brand and interface; a separate warm ramp carries heat; five fixed hues carry fault identity.

### Primary
- **REON Green** (reon-green): the brand dark. Ink colour in light theme, the lower band, the active tab pill, the play button, tooltips and the wordmark (drawn in `currentColor`).
- **Neon Green** (neon-green): "what REON reads or does". The REON-signal line and its "REON flags" marker in the timeline, the "weeks early" bracket, emphasised words in a diagnosis, the REON bar in the year card, the gauge's bright end, the glow, and the accent in dark theme.
- **Green Mid** (green-mid): the light-theme accent: bypass rings in the legend, slider fill and thumb ring, focus outline, selection tint, simulated-data dot.
- **Green Deep** (green-deep) and **Green Bright** (green-bright): the gauge sweep runs from deep to neon; factor bars fill bright to mid; deep is the light-theme accent ink for small positive deltas.

### Secondary
- **Heat Ramp** (heat-cold, heat-0 to heat-4): one sequential warm ramp, interpolated in code. Cooler than pack fades to heat-cold; hotter steps through heat-1 to heat-4 per kelvin. Used by the cabinet map, the CFD maps, the Shapley stack and over-limit bars in the worst-day chart. Dark theme swaps to a darker ramp in the same order.
- **Band Signals** (band-warm, band-heat, band-health): on the dark band only. Heat lane and "Heat shows" marker in band-heat; offer thermometers run band-warm to band-heat; the health lane in band-health.

### Tertiary
- **Fault Hues** (fault-tab, fault-corrosion, fault-damage, fault-plating, fault-cooling): violet, teal, magenta, blue, amber. Each fault kind keeps its hue everywhere it names the fault: pill-toggle dots, caught/not-caught dots, 3D pack tags. It never colours a bypass ring or a slab outline. Non-fault readings (SEI ageing, temperature effect, healthy, unclear) use quiet greys from the same token family. Dark theme lifts each hue for contrast.

### Neutral
- **Off-White** (off-white): page ground, light theme.
- **REON White** (reon-white): text on the band and on dark pills; the glass card tint.
- **Card Solid** (card-solid): opaque card colour for slider thumbs, gauge knob, chart text halos and mini-stat tiles.
- **Ink 2 / Ink 3** (ink-2, ink-3): secondary text, captions and axis labels. On the band, band-ink-2 does the same job.
- **Night** (night), **Band Night** (band-night), **Card Solid Night** (card-solid-night): dark theme ground, band and solid card.
- **Semantic** (ok, warn, bad; bad-on-band on the band): status chips, the 60 °C limit line, missed-fault text, passing bars in the worst-day chart. Always on a 12-15 % tint of the same hue.

### Named Rules
**The REON Is Green Rule.** Green means REON sensed or acted. Heat, health and faults never use green; status "ok" is the one semantic exception and stays on a tinted chip or a passing bar.

**The Separate Heat Rule.** Temperature is drawn only with the warm heat ramp, never with brand colour or fault hues.

**The Fixed Fault Hue Rule.** A fault kind's hue is assigned once and follows it into every pill, dot, tag and lane that names the fault. Bypass rings and outlines are REON green, never a fault hue (user decision).

## Typography

**Display Font:** Geist (stand-in for REON's licensed Neue Montreal, which is next in the stack), falling back to the system sans.
**Body Font:** Geist.

**Character:** One neo-grotesk at many weights. Big numbers go light (300) and tight; headings sit at 450-550 with negative tracking; all numbers are tabular so weekly values do not jitter during playback.

### Hierarchy
- **Display** (300, 64px, line-height 1, -0.045em): the gauge's health number. 56px under 640px. The decimals and unit drop to a 24px muted `small`.
- **Numeral** (300, 40px, line-height 1, -0.045em): factor-card values and offer peaks (32px on mobile for factors); 52px in the timeline lead. Unit in a 16-17px muted `small`.
- **Page title** (450, 34px, -0.03em): the cabinet name; 28px on mobile.
- **Headline** (450, 30px, -0.03em): band and section heads; 25px on mobile.
- **Title** (550, 17px, -0.01em): card heads.
- **Body** (400, 15px, line-height 1.45): sub-heads and reasoning (1.55 line height, 46ch max on the band).
- **Label** (500-550, 12.5-14px): tabs, chips, legends, captions, chart labels (11-13.5px in SVG).

### Named Rules
**The Light Numeral Rule.** The bigger the number, the lighter the weight: 300 at 40px and up, 400-450 for 20-28px stat values.

**The Tabular Rule.** `font-variant-numeric: tabular-nums` is set on the body and holds everywhere numbers change.

## Layout

A 1240px max container with a 16px minimum side gutter (respecting safe-area insets) and a 12-column grid with a 20px gap. The page is three acts: a light hero under the glow (title, gauge span 4 beside map span 8, four factor cards span 3), the full-bleed dark band (timeline span 8 beside diagnosis span 4, then year card span 3 beside three offer cards), and a light thermal section (span 7 + 5, then two span-12 cards). Sections are separated by 56px.

At 1040px all 4/5/7/8 spans go full width, factor cards pair up, and the tabs drop to their own centred row. At 640px gaps drop to 14px, card padding to 18px, CFD maps and offers stack, the band radius eases to 26px. At 420px factor cards go single-column. Charts measure their container and redraw on resize; below 600px the timeline and worst-day chart move their labels above the lanes and bars instead of beside them.

## Elevation & Depth

Depth is glass over glow. Light cards are translucent (`backdrop-filter: blur(20px) saturate(150%)`) with a 1px white edge, floating over three blurred green radial blobs. One soft two-layer shadow lifts every card and the tab bar; band cards have no shadow and rely on a 4.5 % white tint and a hairline edge. The dark theme deepens the shadow and dims the glow to 20 % opacity.

### Shadow Vocabulary
- **Card lift** (`box-shadow: 0 1px 2px rgba(10,26,17,.06), 0 16px 36px -16px rgba(0,60,20,.28)`): all light cards and the tab bar. Dark: `0 1px 2px rgba(0,0,0,.4), 0 18px 40px -18px rgba(0,0,0,.8)`.
- **Float** (`box-shadow: 0 10px 24px -8px rgba(0,0,0,.4)`): the map tooltip.
- **Button press** (`box-shadow: 0 6px 16px -6px rgba(0,0,0,.35)`): the play button.

### Named Rules
**The Soft Lift Rule.** Shadows are soft, offset downward and green-tinted in light theme. No hard or stacked shadows.

## Shapes

Rounded and pill-shaped throughout. Cards and mini-stat tiles use 16px; the dark band opens with a 32px top radius; every control and chip is a full pill (999px). Data marks repeat the rounding at small scale: map cells at 7px with 9px bypass rings, CFD cells at 6px, bars and tracks at 6px, Shapley stack at 12px. Dashed strokes mean "bypassed" or "simulated" (bypassed cells on the CFD maps, the empty home slot in the 3D pack, the simulated-data tag).

## Components

### Buttons
- **Play** (button-play): a 42px REON-green circle with a white SVG play/pause glyph; scales to 1.06 on hover and 0.96 on press.
- **Band button** (button-band): a translucent white pill on the band with a hairline edge; hover lightens the fill to 16 % white. Used for "Compare all".

### Navigation
- **Pill tabs** (tab, tab-active): three anchors in a frosted pill bar centred in the top bar. The current section (scroll-spied) gets a REON-green pill with white text; others are ink-2 and darken on hover. On mobile the bar takes its own row.

### Pill toggles
- **Fault pills** (pill-toggle, pill-toggle-pressed): on the band, outlined pills each leading with an 8px dot in the fault's hue; `aria-pressed="true"` fills the pill white with REON-green text.

### Chips
- **Status chips** (chip-ok, chip-warn, chip-bad): semantic text on a tinted pill. A neutral chip (track tint, ink-2) carries context such as run conditions.
- **Band chips**: 9 % white pills with white text for the diagnosis evidence; ok and bad variants tint green or red.
- **Simulated-data tag**: a dashed-outline pill with a green status dot, fixed in the top bar.

### Cards / Containers
- **Corner Style:** 16px.
- **Background:** glass card-glass on light; 4.5 % white on the band.
- **Shadow Strategy:** card lift on light, none on the band.
- **Border:** 1px white edge (light) or hairline white (band).
- **Internal Padding:** 22px, 18px on mobile.

### Inputs / Fields
- **Week scrubber:** a 6px pill track filled with the accent up to the current week, a 20px solid thumb ringed in the accent, month ticks beneath, and the week number and site temperature to the right.

### Health Gauge
A half-circle of 46 rounded ticks from 70 % (end of life) to 100 % (new); lit ticks sweep from green-deep to neon green, unlit ticks are the track tint, and a solid knob marks the value. The display numeral sits inside the arc. The gauge follows the shared week slider (user request): the numeral, its two-line caption ("Weakest cell in service" over "Week N", "End of year" at week 52), the Average cell tile and the chip all show the scrubbed week from the REON-policy backtest run (`D.health`, built by `model/backtest_health.py`). Retired cells are out of the string, so the gauge reads only cells still in service (`live_*` series; user decision); the year card's "Weakest cell in service" row uses the same definition. The chip is the gap to the no-bypass run, taken between the one-decimal values shown so it always matches them; a zero gap reads "Same as no bypass" on a neutral chip. "Projected life" comes from the life model run on this cabinet's five backtest faults (`econ.py` `cabinet_faults`), stays fixed, and says so in its tooltip; "Why bypass pays" uses the same case and shows the fault-free gain on a second line. Both sliders carry `aria-valuetext` with the week and the weakest-cell value.

### Cabinet Map
8 modules by 16 cells in SVG. Each cell is filled from the heat ramp (relative to pack); retired cells go solid ink with an X; hidden faults carry a corner tab; REON's bypass (active or retired) gets a REON-green ring (`--accent`). The map does not mark the fault selected in the band below (user decision: no "Dashed: …" label or selection outline); clicking or pressing Enter on a fault cell still selects it there. Labels scale with container width so they stay legible.

### 3D Pack (#pack3d)
A full-width card under the factor cards. A canvas-2D orthographic view of the 8 modules as stacked glass shelves of 16 cell slabs, drawn bottom shelf first and cells by depth, with one fixed world light. Encoding: slab height is cell health (SOH 70-100 %), colour is heat vs pack from the warm ramp, a REON bypass slides the slab forward and draws it see-through with a green outline, retirement slides it further, draws it solid (`--cell-ret`) with the map's X on its front face, and a dashed green footprint marks the empty home slot. Fault cells carry pill tags in their fault hue (only the selected fault's tag below 600px). Drag or arrow keys turn it within ±1 rad of yaw; double-click or Home resets. Canvas height follows the pack's own shape (cap 720px on wide cards, 600px narrower). Beside it: the week as a light numeral, the last five events with coloured dots (grey: fault starts hidden; green: REON flags or pulls; red: healthy cell retired by mistake; heat ramp orange: runs hot; ink-2: loses health) and a four-row key. Its slider sits directly under the canvas at every width, with event ticks above it.

### Fault Timeline
Three stacked lanes on the band (REON signal in neon, heat in band-heat, health in band-health), each with a dashed threshold, an area gradient and an event marker row whose labels are packed into rows so they never collide. Chart text carries a band-coloured halo. A hover or click cursor reads the week into a white readout pill.

### Motion
One authored moment: pressing play (either play button; they share state) steps the year at 260ms a week. The gauge's lit ticks and knob ease to the new week's value over 240ms (cubic ease-out) while the numeral jumps straight to the model's value, so it never shows an in-between number. Each newly appearing bypass ring pops in (scale 1.9 to 1 with a blur fade, 0.7s, `cubic-bezier(.16,1,.3,1)`), and in the 3D pack every slab eases to its new height, heat colour and slide over 240ms (cubic ease-out). Rings that already existed do not re-animate; reduced motion snaps the gauge and the 3D pack to each week. `prefers-reduced-motion` removes the pop and smooth scrolling. Everything else is 0.15-0.2s colour and transform transitions.

## Do's and Don'ts

### Do:
- **Do** use neon green only for what REON reads or does: its signal, flags, bypass rings, and the words that name its conclusion.
- **Do** draw every temperature with the warm heat ramp, read from the `--h-*` tokens so both themes stay in step.
- **Do** keep each fault kind on its fixed hue across pills, dots, tags and lanes; keep bypass rings and outlines green.
- **Do** set big numbers light (300) and tabular with a smaller muted unit.
- **Do** explain a diagnosis in one or two plain sentences that name the cause, with bold neon emphasis on the deciding facts.
- **Do** carry the dashed "Simulated data" tag in the top bar and the simulated-data line in the footer on every surface.
- **Do** draw charts to their container width and redraw on resize and theme change.
- **Do** keep the REON wordmark as inline SVG in `currentColor`, and keep any page that carries it a local file, never a published link.

### Don't:
- **Don't** colour heat, health or faults in brand green.
- **Don't** render the diagnostic flowchart's yes/no steps as the explanation.
- **Don't** add words where a number or a shape will do; labels stay short and sentence case.
- **Don't** use hard offset shadows or square corners on cards and controls.
- **Don't** animate anything beyond the year playback (gauge arc, ring pop, 3D slab transition) and short state transitions, and never ignore reduced motion.
- **Don't** reuse the layout reference's third-party name, logo or content.
