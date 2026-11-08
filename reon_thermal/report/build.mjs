// Builds the 2-page plain-language report (an Artifact page) from the results files + the three Anatomy figures.
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import * as k from "file:///C:/Users/anina/.claude/skills/anatomy/kit/iso-kit.mjs";
import { kitScript } from "file:///C:/Users/anina/.claude/skills/anatomy/scripts/inline-kit.mjs";
import * as F1 from "../figures/fig_cabinet.mjs";
import * as F2 from "../figures/fig_module.mjs";
import * as F3 from "../figures/fig_blocks.mjs";

const R = "C:/Users/anina/Downloads/MITEC/reon_thermal/results";
const J = (f) => JSON.parse(readFileSync(`${R}/${f}`, "utf8").replace(/\bNaN\b/g, "null"));
const cases = J("network_cases.json"), gpu = J("gpu_studies.json"), econ = J("econ.json"), tax = J("hotspot_tax.json");
const feas = J("feasibility.json"), elm = J("elmer_module.json"), Asst = J("openfoam/A_sst_m1.json"), Alam = J("openfoam/A_lam_m1.json");
const hand = J("hand_checks.json");
const gci = existsSync(`${R}/openfoam/gci_A_sst.json`) ? J("openfoam/gci_A_sst.json") : null;
const half = existsSync(`${R}/openfoam/A_sst_half.json`) ? J("openfoam/A_sst_half.json") : null;
const s4 = existsSync(`${R}/stage4.json`) ? J("stage4.json") : null;
const ex = existsSync(`${R}/extras.json`) ? J("extras.json") : null;
const pbm = existsSync(`${R}/pybamm_heat.json`) ? J("pybamm_heat.json") : null;
const ct = existsSync(`${R}/openfoam/Ct_lam_m1_cells.json`) ? J("openfoam/Ct_lam_m1_cells.json") : null;
const dt = existsSync(`${R}/openfoam/Dt_lam_m1_cells.json`) ? J("openfoam/Dt_lam_m1_cells.json") : null;
const f1 = (v) => (+v).toFixed(1);
// 3D C vs D at the same moment (D was stopped early to free the cores for C)
let cdCmp = null;
if (ct && dt) {
  const n = Math.min(ct.t_s.length, dt.t_s.length) - 1;
  const pk = (d) => Math.max(...d.T_max.slice(0, n + 1).flat());
  const sp = (d) => Math.max(...d.T_mean[n]) - Math.min(...d.T_mean[n]);
  cdCmp = { t: dt.t_s[n], c: pk(ct), d: pk(dt), cs: sp(ct), ds: sp(dt) };
}
const c = (id) => cases[id];
const f = [F1.build(), F2.build(), F3.build()];
const sob = gpu.sobol, shap = gpu.shapley;
const sobTop = sob.names.map((n, i) => [n, sob.peak.ST[i]]).sort((a, b) => b[1] - a[1]);
const feasRow = (w, m, kk) => feas.find((r) => r.usable_window === w && r.mode === m && r.k_bypassed === kk);

// Light theme for the figure kit, driven by the viewer's theme (dark-first page)
const isoLight = (k.ISO_CSS.match(/\.iso\[data-theme="light"\]\{([^}]*)\}/) || [])[1] || "";
const themeCss = `@media (prefers-color-scheme: light){:root:not([data-theme="dark"]) .iso{${isoLight}}}:root[data-theme="light"] .iso{${isoLight}}`;

const verdict = [
  { q: "How uneven are the cells?", tag: "uneven", a: `Fan on, the middle of the stack runs hottest because the air skips the 30 mm gaps: ${gci ? `held at full power the hottest cell (module 7) settles near ${f1(gci.peak_interior_C.extrapolated)} °C in the 3D model (three meshes, ±${gci.peak_interior_C.gci_fine_pct.toFixed(0)}%), with cells as cool as ${f1(gci.mean_cell_C.extrapolated - (Asst.summary.T_mean_avg - Asst.summary.T_mean_min))} °C.` : `cells spread ${f1(Asst.summary.T_mean_min)}–${f1(Asst.summary.T_int_max)} °C in the 3D model (steady, full power).`} Sealed, the whole cabinet warms together: ${ct ? f1(ct.spread_end) + " K" : f1(c("C_passive40").spread_end_K) + " K"} spread after 2 h, hottest ${ct ? ct.peakCell : c("C_passive40").peak_cell} at the end of discharge.` },
  { q: "Can bypass keep every cell under 60 °C?", tag: "partly", a: `On a 40 °C day starting cool: no bypass needed (${f1(c("C_passive40").peak_interior_C)} °C). When the cabinet starts hot (55 °C): no. Bypassing 13 cells gives ${f1(c("H_fixed13_power").peak_interior_C)} °C, worse than doing nothing (${f1(c("H_hotstart").peak_interior_C)} °C), because the other cells carry more current.${cdCmp ? ` The 3D model agrees: ${cdCmp.t >= 7199 ? "over the 2 h discharge" : `after ${Math.round(cdCmp.t / 60)} min`}, bypassing 13 cells raises the hottest cell from ${f1(cdCmp.c)} to ${f1(cdCmp.d)} °C.` : ""}` },
  { q: "What does it cost?", tag: "cost", a: `Bypassing 13 cells at full power adds ${f1((c("D_fixed13_power").total_heat_end_W / 780.8 - 1) * 100)}% heat, and 30 kW then lasts ${f1(feasRow(1, "power", 13).runtime_h)} h instead of ${f1(feasRow(1, "power", 0).runtime_h)} h (${f1(feasRow(1, "power", 13).energy_kWh)} kWh). Bypassing one cell costs 0.8% of power. Up to 4 cells fit inside 30 kW × 2 h with 5% charge headroom.` },
  { q: "When is bypass not enough?", tag: "limit", a: `When the heat is everywhere. A 55 °C start needs a cut to ${f1(tax.max_power_no_aged_cell_kW)} kW (−10%). With one aged cell, a fixed string must drop to ${f1(tax.max_power_fixed_string_kW)} kW; bypassing just that cell holds ${f1(tax.max_power_cell_control_kW)} kW.` },
];

const rows = [
  ["Starting temperature (heat soak)", "Sets the peak: biggest single factor", `${f1(shap.shapley_K[shap.names.indexOf("hot start (55 C)")])} K; ${Math.round(sobTop[0][1] * 100)}% of the variance`, "Bypass can’t help. Schedule: pre-cool at night, don’t start a discharge hot"],
  ["Hot site (40 °C air) and sun", "Walls are slow (2–4 h time constant), so the cabinet stays warm day to day", `${f1(shap.shapley_K[shap.names.indexOf("hot site (40 C vs 25 C)")])} K site. Afternoon sun adds ${f1(shap.shapley_K[shap.names.indexOf("sun on roof/side")])} K at the centre but takes the top corner cell by the sunny wall to ${f1(c("C_solar").peak_interior_C)} °C (vs ${f1(c("C_passive40").peak_interior_C)} °C)`, "Not a cell problem: shade or reflective paint (about −3 K at the sunny corner), pre-cooling, or fans"],
  ["One cell’s resistance (ageing, defects)", "A local hot spot. Heat barely crosses cells (0.5 W/K per contact), so it stays put", `${f1(shap.shapley_K[shap.names.indexOf("ageing (+12.2 W, 3x R)")])} K at that cell; ages it ~1.6× faster per +10 K`, `Bypass that cell: −${f1(c("E_aged_C").peak_interior_C - c("E_aged_C_bypass1_current").peak_interior_C)} K, breaks the hotter → older → hotter loop. Pick it by measured resistance, not by temperature`],
  ["Current demand (I²R heat)", "Heat grows with current squared", "6.1 W per cell at 30 kW; +24% per cell when 13 are bypassed", "Bypass few cells, not many; derate on hot starts"],
  ["Heat from the other 127 cells", "Warms the shared air and walls", `${f1(shap.shapley_K[shap.names.indexOf("other 127 cells' heat")])} K`, "Spread load in time (scheduling)"],
  ["Airflow path", "The 30 mm gaps get under 1% of the fan’s air; the middle runs hot", gci ? `fan on, full power: hottest ${f1(gci.peak_interior_C.extrapolated)} °C (3 meshes, ±${gci.peak_interior_C.gci_fine_pct.toFixed(0)}%), ${f1(Alam.summary.T_int_max)} °C with a laminar air model` : `3D steady: ${f1(Asst.summary.T_int_max)} °C (SST); ${f1(Alam.summary.T_int_max)} °C laminar`, "Not fixable by control: baffles or gap ducts"],
  ["Inverter inside the cabinet", "750 W into the top air", `${f1(shap.shapley_K[shap.names.indexOf("inverter inside (750 W)")])} K at the hottest cell`, "Mount it outside or duct it"],
  ["Busbar and switch losses", "Small extra heat at every cell", `${f1(shap.shapley_K[shap.names.indexOf("busbar + switch losses")])} K; a bypassed cell still dissipates about 1.4 W in its switch`, "Low-resistance switches"],
];

const css = `
:root{
  /* Layout: two-page instrument report, a verdict strip, then figure + text pairs, a cause table, value, method notes */
  --bg:#0c0d0f; --panel:#131417; --line:#25272c; --fg:#dcdde1; --muted:#8d9098; --accent:#f0962e; --ok:#5ec79a; --bad:#ef6a5a;
  --display:"Archivo",ui-sans-serif,system-ui,sans-serif; --body:"IBM Plex Sans",ui-sans-serif,system-ui,sans-serif; --mono:"IBM Plex Mono",ui-monospace,Menlo,Consolas,monospace;
  color-scheme:dark;
}
@media (prefers-color-scheme: light){:root:not([data-theme="dark"]){--bg:#f3f3f1;--panel:#fbfbfa;--line:#dedfe0;--fg:#1b1c1f;--muted:#5d6068;--accent:#b85d08;--ok:#1d7f55;--bad:#c23a2b;color-scheme:light}}
:root[data-theme="light"]{--bg:#f3f3f1;--panel:#fbfbfa;--line:#dedfe0;--fg:#1b1c1f;--muted:#5d6068;--accent:#b85d08;--ok:#1d7f55;--bad:#c23a2b;color-scheme:light}
body{background:var(--bg);color:var(--fg);font:15px/1.55 var(--body);margin:0}
.wrap{max-width:1080px;margin:0 auto;padding-block:28px 56px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));display:grid;gap:28px}
.wrap>*{min-width:0}
header{display:grid;gap:10px}
.eyebrow{font:500 12px/1 var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
h1{font:700 clamp(30px,4.6vw,48px)/1.04 var(--display);font-stretch:88%;letter-spacing:-.01em;margin:0;text-wrap:balance}
h1 em{font-style:normal;color:var(--accent)}
.lede{font-size:17px;max-width:68ch;margin:0;color:var(--fg)}
h2{font:700 21px/1.2 var(--display);font-stretch:90%;margin:0 0 8px;text-wrap:balance}
p{margin:0;max-width:68ch}
.muted{color:var(--muted)}
.verdict{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
.v{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:14px 14px 16px;display:grid;gap:8px;align-content:start;min-width:0}
.v h3{font:600 14px/1.25 var(--body);margin:0}
.v p{font-size:13.5px;line-height:1.5}
.pill{justify-self:start;font:600 11px/1 var(--mono);letter-spacing:.08em;text-transform:uppercase;padding:5px 7px;border-radius:3px;border:1px solid currentColor}
.pill.uneven{color:var(--accent)} .pill.partly{color:var(--accent)} .pill.cost{color:var(--muted)} .pill.limit{color:var(--bad)}
.pair{display:grid;grid-template-columns:minmax(0,1.05fr) minmax(0,1fr);gap:28px;align-items:start}
.pair>div{min-width:0;display:grid;gap:12px}
.duo{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:20px;align-items:start}
.duo>div{min-width:0}
.iso{background:transparent}
.iso .iso-plate{margin:0}
.nums{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
.n{border-top:2px solid var(--accent);padding-top:10px;display:grid;gap:4px;min-width:0}
.n b{font:700 26px/1.05 var(--display);font-stretch:90%;font-variant-numeric:tabular-nums}
.n span{font-size:13px;color:var(--muted)}
.tbl{overflow-x:auto;border:1px solid var(--line);border-radius:6px;background:var(--panel)}
table{border-collapse:collapse;width:100%;min-width:760px;font-size:13.5px}
th,td{text-align:left;vertical-align:top;padding:9px 12px;border-bottom:1px solid var(--line)}
th{font:600 11px/1.2 var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
tr:last-child td{border-bottom:0}
td:first-child{font-weight:600}
td.k{font-family:var(--mono);font-size:12.5px;font-variant-numeric:tabular-nums}
.notes{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px;font-size:13px;color:var(--muted)}
.notes ul{margin:6px 0 0;padding-left:18px;display:grid;gap:4px}
.notes h2{font-size:16px;color:var(--fg)}
a{color:var(--accent)}
.ok{color:var(--ok);font-weight:600}.bad{color:var(--bad);font-weight:600}
section>p+.tbl,section>.tbl+p{margin-top:10px}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
@media (max-width:900px){.verdict{grid-template-columns:repeat(2,minmax(0,1fr))}.pair,.duo,.notes{grid-template-columns:1fr}}
@media (max-width:520px){.verdict,.nums{grid-template-columns:1fr}}
`;

const life = econ.life_fixed_years.p50, lifeC = econ.life_control_years.p50;
const html = `<title>EBS Cabinet Heat Study</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,500..800&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>${k.ISO_CSS}${themeCss}${css}${f.map((x) => x.css || "").join("")}</style>
<div class="wrap iso">
<header>
  <span class="eyebrow">REON EBS Na+ · 30 kW / 60 kWh · 128 sodium-ion cells · MIT Energy &amp; Climate Hack 2026</span>
  <h1>Bypass fixes <em>hot cells</em>, not a hot cabinet</h1>
  <p class="lede">We simulated REON’s battery cabinet cell by cell to see what makes each cell hot and what switching one cell out of the string can fix. Switching out an aged cell removes its hot spot and gives back up to ${f1(tax.recovered_kW)} kW on a hot day. Switching out many cells to cool the whole cabinet makes it hotter, because the remaining cells carry more current.</p>
</header>
<section class="verdict" aria-label="Answers to the four questions">
${verdict.map((v) => `<article class="v"><span class="pill ${v.tag}">${v.tag === "partly" ? "only for hot spots" : v.tag === "uneven" ? "depends on airflow" : v.tag === "cost" ? "energy and power" : "derate or cool"}</span><h3>${v.q}</h3><p>${v.a}</p></article>`).join("")}
</section>
<section class="pair">
  <div>${f[0].plate}</div>
  <div>
    <h2>The air goes around the cells, not between them</h2>
    <p>The fan blows 0.15 m³/s in at the bottom front. In our 3D airflow model it takes the easy paths: under the bottom module, up the side gaps and over the top. The seven 30 mm gaps between modules get under 1% of it, so the middle modules sit in still air and run hottest.</p>
    <p>Sealed, with no fan, every cell warms together by about ${ct ? f1(ct.T_end_mean.reduce((a, b) => a + b, 0) / 128 - 40) : f1(c("C_passive40").mean_end_C - 40)} K over a 2 h discharge (adiabatic would be 9.1 K). The cabinet’s own mass (618 kJ/K) sets the pace, and the spread between cells is only ${ct ? ct.spread_end.toFixed(1) : f1(c("C_passive40").spread_end_K)} K in the 3D model. In both cases the hottest cell is hot because of where it sits, not because of what it is. Bypass cannot fix that.</p>
    <div class="nums">
      <div class="n"><b>${gci ? `${f1(gci.peak_interior_C.extrapolated)} °C` : `${f1(Asst.summary.T_int_max)} °C`}</b><span>hottest cell, fan on, held at full power (3-mesh extrapolation, ±${gci ? gci.peak_interior_C.gci_fine_pct.toFixed(0) : "?"}%; laminar air model: ${f1(Alam.summary.T_int_max)} °C)</span></div>
      <div class="n"><b>${ct && ct.t_end >= 7199 ? f1(ct.peak) : f1(c("C_passive40").peak_interior_C)} °C</b><span>hottest cell, sealed, 40 °C day, after 2 h${ct && ct.t_end >= 7199 ? " (3D)" : " (network, matched to 3D)"}</span></div>
      <div class="n"><b>&lt;1%</b><span>of the air passes through the gaps between modules</span></div>
    </div>
    ${f[2].plate}
  </div>
</section>
<section>
  <h2>What heats a cell, what it does, and what control can change</h2>
  <div class="tbl"><table>
    <thead><tr><th>Cause</th><th>What it does to the cell</th><th>How much (our runs)</th><th>What helps</th></tr></thead>
    <tbody>${rows.map((r) => `<tr><td>${r[0]}</td><td>${r[1]}</td><td class="k">${r[2]}</td><td>${r[3]}</td></tr>`).join("")}</tbody>
  </table></div>
</section>
${s4 ? `<section>
  <h2>Beyond bypass: what else gets the worst day under 60 °C</h2>
  <p class="muted">Worst realistic day: sealed cabinet, 40 °C outside, cabinet already at 55 °C, one aged cell, 30 kW for 2 h. Doing nothing, the hottest cell reaches ${f1(s4.ideas[0].peak_C)} °C.</p>
  <div class="tbl"><table>
    <thead><tr><th>Idea</th><th>Hottest cell</th><th>Under 60 °C</th><th>Extra energy per day</th><th>Type</th></tr></thead>
    <tbody>${s4.ideas.slice(1).sort((a, b) => a.peak_C - b.peak_C).map((r) => `<tr><td>${r.idea.replace("Bypass aged cell + phase-change plates", "Bypass aged cell + plates that melt at 46 C").replace(/ C\b/g, " °C").replace(/</g, "&lt;")}</td><td class="k">${f1(r.peak_C)} °C</td><td>${r.below_60 ? '<span class="ok">yes</span>' : '<span class="bad">no</span>'}</td><td class="k">${r.extra_kWh_per_day > 0 ? r.extra_kWh_per_day.toFixed(2) + " kWh" : "none"}</td><td>${r.kind}</td></tr>`).join("")}</tbody>
  </table></div>
  <p>Only three things beat the limit on their own or in pairs: starting cooler (pre-cool at night), spreading the same energy over more time, and bypassing the aged cell together with pre-cooling or phase-change plates that melt just below the limit. Air conditioning alone does not get there in 2 h: the cool air skips the gaps and the cells hold too much heat. Spreaders, a chimney vent and a reflective roof barely move the hottest cell.</p>
</section>` : ""}
<section class="pair">
  <div>${f[1].plate}</div>
  <div>
    <h2>What it is worth</h2>
    <p>The value of cell-level control is that one weak cell no longer sets the limit for the other 127, for heat or for capacity.</p>
    <div class="nums">
      <div class="n"><b>+${f1(tax.recovered_kW)} kW</b><span>held on a hot-start day with one aged cell: ${f1(tax.max_power_cell_control_kW)} kW instead of ${f1(tax.max_power_fixed_string_kW)} kW (${f1(tax.recovered_kWh_per_hot_day)} kWh more per hot day)</span></div>
      <div class="n"><b>${f1(life)} → ${f1(lifeC)} yr</b><span>service life at a hot site, fixed string vs cell control (to 70%); with one 3×-resistance cell: ${f1(econ.sensitivity.defect_r[1].life_fixed)} → ${f1(econ.sensitivity.defect_r[1].life_control)} yr</span></div>
      <div class="n"><b>+$${Math.round(econ.economics.npv_gain_usd).toLocaleString("en-US")}</b><span>net present value per cabinet from the longer life (7% discount, $350/kWh capex)</span></div>
    </div>
    <h2>And for the climate</h2>
    <p>Each cabinet carries about ${f1(econ.economics.embodied_tco2)} t CO₂ from manufacturing. A longer life spreads that over more years: ${econ.economics.embodied_tco2_per_service_year_fixed.toFixed(2)} → ${econ.economics.embodied_tco2_per_service_year_control.toFixed(2)} t per year of service, about ${f1(econ.economics.avoided_embodied_tco2_over_30y)} t avoided over 30 years of replacements. Air conditioning sized to protect the worst cell at this site would use about ${Math.round(econ.hvac_alternative.electricity_kwh)} kWh a year (${econ.hvac_alternative.co2_t.toFixed(2)} t CO₂). Control lets that cooling be sized for the average cell, not the worst one.</p>
    <p class="muted">Air conditioning that cools the whole cabinet would slow ageing more than bypass does. Cell control is not a replacement for cooling a hot site; it removes the outliers that would otherwise force derating or oversizing.</p>
  </div>
</section>
<section class="notes">
  <div>
    <h2>How we got these numbers</h2>
    <ul>
      <li>OpenFOAM 13, cabinet air plus cells: 98,784 cells, anisotropic cells, Boussinesq air; forced case run steady with laminar and k-omega SST; sealed 40 °C case run as a ${ct && ct.t_end >= 7199 ? "full 2 h" : Math.round((ct ? ct.t_end : 0) / 60) + "-minute"} transient${cdCmp ? (cdCmp.t >= 7199 ? ", with and without the 13 hottest cells bypassed" : `; the 13-bypassed case ran to ${Math.round(cdCmp.t / 60)} min and is compared at the same moment`) : ""}. Internal radiation is not in the 3D model (the network carries it).</li>
      <li>Elmer FEM 26.2, one module with 16 cells and 15 resolved 0.2 mm interface layers: matches the exact solution to 0.00001 K; three meshes agree within 0.03 K; halving the time step changes the peak by 0.0001 K.</li>
      <li>A cell-by-cell network model (128 cells, walls, air streams), calibrated to both 3D models, closes energy to under 0.001% in every case. It ran ${(sob.n_runs + 256 + 2065 + 220).toLocaleString("en-US")} scenarios on the GPU for the sensitivity sweep (Sobol), the exact cause split (Shapley) and the bypass sets.</li>
      <li>All ${Object.keys(hand).length} hand checks from the brief reproduce within 1.1%.</li>
      ${cdCmp && cdCmp.t >= 7199 ? `<li>Left-out check: the network was fitted only to the sealed case without bypass. For the 13-bypassed case it predicts the hottest cell rises by ${f1(c("D_fixed13_power").peak_interior_C - c("C_passive40").peak_interior_C)} K; the 3D model, run separately, gives ${f1(cdCmp.d - cdCmp.c)} K.${existsSync(`${R}/B_leftout_check.json`) ? (() => { const b = J("B_leftout_check.json"); return ` For the same cabinet on a 25 °C day it predicts ${f1(b.network_no_radiation.peak)} °C against ${f1(b.peak_3D)} °C in 3D.`; })() : ""}</li>` : ""}
      ${existsSync(`${R}/openfoam/E_aged_3D_partial.json`) ? (() => { const a = J("openfoam/E_aged_3D_partial.json"); return `<li>Whole-cabinet 3D check of the aged cell (stopped at ${Math.round(a.t_s / 60)} min for time): the aged cell reaches ${f1(a.aged_peak)} °C; bypassed, the hottest cell is ${f1(a.byp_peak)} °C, the same as a cabinet with no aged cell at that moment.</li>`; })() : ""}
      ${existsSync(`${R}/ec_cases.json`) ? (() => { const e = J("ec_cases.json"); const s = e.cases; return `<li>Fully coupled electro-thermal check with published sodium-ion data (voltage curve and resistance from a commercial 18650 cell, Fronc &amp; Stefańczak 2025; resistance falling with temperature, 72 kJ/mol, Leeds 2026). Warmer cells make less heat, so peaks drop: 40 °C day ${f1(s.C_EC_passive40.peak_interior_C)} °C, hot start ${f1(s.H_EC_hotstart55.peak_interior_C)} °C, hot start with the aged cell ${f1(s.E_EC_aged_hotstart.peak_interior_C)} °C and ${f1(s.E_EC_aged_hotstart_bypassed.peak_interior_C)} °C with it bypassed. Heat climbs from about ${Math.round(s.B_EC_passive25.heat_first_W)} to ${Math.round(s.B_EC_passive25.heat_last_W)} W per cell near the end of a discharge, and 30 kW lasts ${f1(s.C_EC_passive40.runtime_h)} h, not quite 2. Reversible heat is unpublished for sodium-ion; ±0.2 mV/K moves the hot-start peak from ${f1(e.sensitivity["dUdT +0.2 mV/K"].hot_start.peak_interior_C)} to ${f1(e.sensitivity["dUdT -0.2 mV/K"].hot_start.peak_interior_C)} °C.</li>`; })() : ""}
      ${existsSync(`${R}/backtest.json`) ? (() => { const b = J("backtest.json"); return `<li>Backtest of the team’s diagnostic bypass algorithm over a simulated year with injected faults: it caught the loose tab, the cracked electrode and sodium plating in the week they appeared and corrosion after 8 weeks, cutting days that faulty cells carried current from ${Math.round(b.none.safety_risk_cell_days)} to ${Math.round(b.algo.safety_risk_cell_days)} (same as perfect knowledge), for ${f1(100 * (1 - b.algo.energy_MWh_year / b.none.energy_MWh_year))}% less energy a year. It missed a mild cooling fault and labels ageing cells inconsistently.</li>`; })() : ""}
      <li>3D surface radiation and the inverter inside were set up and passed short tests but diverged early in the 2 h runs; they are covered by the network model only.</li>
      ${ex && ex.controller_latch_resistance ? `<li>How to choose the cell matters. A controller that bypasses whatever reads hottest locked up on a hot start: with 0.5 K of sensor noise every cell sat near its trip point, the wrong 4 cells took the slots and the aged cell stayed in (${f1(ex.controller_robustness.peak_max)} °C, as if uncontrolled). Choosing from REON’s per-cell resistance estimate found the aged cell every time up to 20% estimate error (${f1(ex.controller_latch_resistance["resistance_sigma0.2"].worst)} °C). Rotating the bypass among the hottest cells was worse than keeping the aged cell out.</li>` : ""}
      ${ex ? `<li>Through-cell conductivity from the electrode layer stack (series rule): ${ex.k_through.series_bound_W_mK[0].toFixed(2)}–${ex.k_through.series_bound_W_mK[1].toFixed(2)} W/m K, bracketing the brief’s 1. It barely changes a uniformly heated cabinet but moves the aged-cell hot spot from ${f1(ex.k_through.sweep["0.5"].aged)} °C (0.5) to ${f1(ex.k_through.sweep["3.0"].aged)} °C (3).</li>` : ""}
      ${half ? `<li>Halving the fan (0.075 m³/s, 3D, full power held): hottest cell ${f1(half.summary.T_int_max)} °C vs ${f1(Asst.summary.T_int_max)} °C on the same mesh (+${f1(half.summary.T_int_max - Asst.summary.T_int_max)} K); the average cell rises ${f1(half.summary.T_mean_avg - Asst.summary.T_mean_avg)} K.</li>` : ""}
      ${gci ? `<li>OpenFOAM grid-convergence study, three meshes (${gci.cells.map((n) => n.toLocaleString("en-US")).join(", ")} cells): the fan-on hottest cell reads ${gci.peak_interior_C.phi_coarse.toFixed(1)}, ${gci.peak_interior_C.phi_medium.toFixed(1)} and ${gci.peak_interior_C.phi_fine.toFixed(1)} °C, converging (order ${gci.peak_interior_C.apparent_order.toFixed(1)}) to ${f1(gci.peak_interior_C.extrapolated)} °C. The fine mesh is still ${f1(gci.peak_interior_C.change_fine_medium * -1)} K from the medium one, so it misses the brief’s 0.5 K target; grid uncertainty ±${gci.peak_interior_C.gci_fine_pct.toFixed(0)}%. The hottest module and the starved gaps are the same on all three.</li>` : ""}
    </ul>
  </div>
  <div>
    <h2>What we assumed (REON has not published these)</h2>
    <ul>
      <li>Cabinet geometry, inlet and outlet sizes, 1.5 mm steel walls; an all-series string of 128 cells (3.1 V, 151 Ah); 0.25 mΩ bypass switch.</li>
      <li>Ageing speeds up 1.6× per +10 K (35 kJ/mol), about 7,500 cycles to 70% at 25 °C; $350/kWh, 0.37 kg CO₂/kWh grid.</li>
      <li>Ranges, not probabilities: peak cell ${f1(sob.peak.p05)}–${f1(sob.peak.p95)} °C across the sampled inputs on a hot-start day. The airflow model choice alone moves the fan-on hot spot by ${f1(Alam.summary.T_int_max - Asst.summary.T_int_max)} K.</li>
      ${pbm ? `<li>The cell heat (6.1 W, from the brief) is the assumption that could overturn everything. It means losing ${f1(pbm.brief_6_1W_as_pct_of_power)}% of the power as heat. The only open sodium-ion model (PyBaMM, Chayambuka 2022, a lab cell, not REON’s) loses ${f1(pbm.rate["0.5"].heat_as_pct_of_power)}% at the same rate, about ${Math.round(pbm.scaled_to_151Ah_0_5C_W)} W per cell at REON’s size. At that heat a normal 40 °C day peaks at ${s4 ? f1(s4.pybamm_whatif["normal start 40 C"].peak_C) : "?"} °C, and staying under 60 °C would need a cut to ${s4 ? f1(s4.pybamm_whatif["normal start 40 C"].max_power_kW) : "?"} kW.</li>` : ""}
      <li>Models agreeing with each other is not validation. A measured cell heat rate comes first, then thermocouples on cells M06–M07 and gap air speed.</li>
    </ul>
  </div>
</section>
</div>
<script type="module">${(kitScript() + f.map((x) => x.live).join("\n")).replace(/<\/(script)/gi, "<\\/$1")}</script>
`;
writeFileSync("C:/Users/anina/Downloads/MITEC/reon_thermal/report/reon_cabinet_heat.html", html);
console.log("report written", html.length, "bytes");
