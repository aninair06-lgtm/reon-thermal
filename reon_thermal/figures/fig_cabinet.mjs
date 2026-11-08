// Fig 1 - The cabinet, front and right panels removed: 8 modules x 16 cells coloured by temperature (fixed 20-70 C),
// and the air paths the 3D CFD found: under the bottom module, up the sides and over the top - almost none through the gaps.
import * as k from "file:///C:/Users/anina/.claude/skills/anatomy/kit/iso-kit.mjs";
import { readFileSync, existsSync } from "node:fs";
import { heatHex, HEAT_JS, HEAT_CSS, scaleHtml } from "./heat.mjs";

const RES = "C:/Users/anina/Downloads/MITEC/reon_thermal/results";
const A = JSON.parse(readFileSync(`${RES}/openfoam/A_sst_m1.json`, "utf8").replace(/\bNaN\b/g, "null"));
function sealedState() {
  const f = `${RES}/openfoam/Ct_lam_m1_cells.json`;
  if (existsSync(f)) { const d = JSON.parse(readFileSync(f, "utf8")); return { T: d.T_end_mean, src: d.src, peak: d.peak, peakCell: d.peakCell }; }
  const n = JSON.parse(readFileSync(`${RES}/network_Tmax_cell.json`, "utf8")).C_passive40.flat();
  const i = n.indexOf(Math.max(...n));
  return { T: n, src: "network model", peak: Math.max(...n), peakCell: `M${String(Math.floor(i / 16) + 1).padStart(2, "0")}_C${String(i % 16 + 1).padStart(2, "0")}` };
}

function bypassState() {
  const f = `${RES}/openfoam/Dt_lam_m1_cells.json`;
  if (!existsSync(f)) return null;
  const d = JSON.parse(readFileSync(f, "utf8"));
  return d.t_end >= 7199 ? { T: d.T_end_mean, peak: d.peak, peakCell: d.peakCell, bypassed: d.bypassed } : null;
}

export function build() {
  const WIDTH = 560, HEIGHT = 640;
  const W = 130, Dp = 40, H = 235;
  const CX = 7.17, CY = 17.47, CZ = 20.7, PAD = 0.02, GAP = 3.0, ZB = 15;
  const X0 = (W - (16 * CX + 15 * PAD)) / 2, Y0 = (Dp - CY) / 2;
  const PITCH = CX + PAD;
  const mz = (m) => ZB + m * (CZ + GAP);
  const TOPZ = mz(7) + CZ;
  const WT = 1.2;
  const P = k.fitProjection([[0, 0, -8], [W, 0, -8], [W, Dp, -8], [0, Dp, -8], [0, 0, H + 2], [W, Dp, H + 2], [0, Dp, H + 2], [W, 0, H + 2]],
    WIDTH, HEIGHT, { pad: 18, azimuth: 58 });
  const at = (p) => k.iso(p, P);
  const S = (paths, style) => k.solidSvg(paths, style);
  const L = (d, style) => k.lineSvg(d, style);
  const D = (pts, style) => k.dotsSvg(pts, style);
  const dOf = (pts) => "M" + pts.map((p) => at(p).map((v) => v.toFixed(1)).join(" ")).join("L");
  const forcedT = A.cells.map((c) => c.T_volume_mean_C);
  const sealed = sealedState();
  const byp = bypassState();
  const out = [];
  // ---- plinth and feet
  const BASE = { x: -2, y: -2, w: W + 4, d: Dp + 4, r: 1.5 };
  out.push(`<path class="iso-halo" d="${k.haloOf(BASE, -8, 8, P)}"/>`);
  for (const [x, y] of k.corners(BASE, 6).sort((a, b) => k.depthOf([...a, 0], P) - k.depthOf([...b, 0], P))) {
    out.push(S(k.cylinder(x, y, 3.2, -8, 2.5, P, 20), { tone: "lo" }));
  }
  out.push(S(k.slabOf(BASE, -5.5, 5.5, P, 3, 0.5), { tone: "mid" }));
  out.push(D(k.corners(BASE, 3).map(([x, y]) => at([x, y, 0])), { size: 0.45 }));
  // ---- back wall (interior face visible) with stiffener seams, left wall, floor pan
  const back = { x: 0, y: 0, w: W, d: WT, r: 0.2 };
  const backSeams = [0.25, 0.5, 0.75].map((f) => k.segment([f * W, WT, 0], [f * W, WT, H], P)).join("");
  out.push(S(k.slabOf(back, 0, H, P, 2), { tone: "lo", crease: "none", inner: L(backSeams, { tone: "faint" }) }));
  const left = { x: 0, y: 0, w: WT, d: Dp, r: 0.2 };
  out.push(S(k.slabOf(left, 0, H, P, 2), { tone: "lo", crease: "none" }));
  out.push(S(k.slabOf({ x: WT, y: WT, w: W - WT, d: Dp - WT, r: 0.2 }, 0, 0.6, P, 2), { tone: "lo", crease: "none" }));
  // ---- air paths BEHIND the modules: rear plenum rise, left side rise, under-module crossflow
  const flowsBack = [], flowsFront = [];
  const fl = (pts, share, cls = "") => `<path class="iso-line air ${cls}" data-tone="lit" data-flow="" d="${dOf(pts)}" style="stroke-width:${(0.5 + 2.2 * share).toFixed(2)}"/>`;
  const sh = A.summary.channel_share, side = A.summary.side_share;
  for (const x of [26, 65, 104]) flowsBack.push(fl([[x, Dp - 2, 6], [x, 4, 6], [x, 4, TOPZ + 6]], sh[0] / 3));
  flowsBack.push(fl([[3.7, Dp - 2, 5], [3.7, Dp / 2, 12], [3.7, Dp / 2, H - 6]], side / 2));
  out.push(`<g data-part="airback">${flowsBack.join("")}</g>`);
  // ---- modules: supports, cells (heat coloured), busbar caps
  const cells = [];
  for (let m = 0; m < 8; m++) {
    const z0 = mz(m);
    // two support rails (angle brackets) from left to right wall under the module, front and back edges
    for (const y of [Y0 + 1, Y0 + CY - 4]) out.push(S(k.slabOf({ x: WT, y, w: W - WT, d: 3, r: 0.3 }, z0 - 1.6, 1.6, P, 2), { tone: "mid", crease: "none" }));
    if (m > 0) {
      // stagnant air in the gap below this module: a faint dotted line, front to back
      out.push(L(dOf([[X0 + 2, Y0 + CY, z0 - GAP / 2], [X0 + 2, Y0, z0 - GAP / 2]]).replace(/^M/, "M"), { tone: "faint", dotted: true }));
    }
    for (let c = 0; c < 16; c++) {
      const x = X0 + c * PITCH, i = m * 16 + c;
      const plan = { x, y: Y0, w: CX, d: CY, r: 0.25 };
      cells.push(`<g class="hc" data-cell="${i}" style="--h:${heatHex(forcedT[i])}">${S(k.slabOf(plan, z0, CZ, P, 2), { tone: "hi", crease: "lo" })}</g>`);
    }
    // module end plates with bolts
    for (const x of [X0 - 1.6, X0 + 16 * CX + 15 * PAD]) {
      cells.push(S(k.slabOf({ x, y: Y0 - 0.4, w: 1.6, d: CY + 0.8, r: 0.2 }, z0, CZ + 0.6, P, 2), { tone: "mid", crease: "none" }));
    }
    cells.push(D([0.25, 0.75].map((f) => at([X0 + 16 * CX + 15 * PAD + 1.6, Y0 + CY - 2, z0 + f * CZ])), { size: 0.4 }));
    // busbar caps along the front top edge of each module
    cells.push(S(k.slabOf({ x: X0, y: Y0 + CY - 3.2, w: 16 * CX, d: 1.6, r: 0.4 }, z0 + CZ, 0.7, P, 2), { tone: "mid", crease: "none" }));
    // one switch-board status LED per cell on its front face (REON: a switch at every cell)
    cells.push(D(Array.from({ length: 16 }, (_, c) => at([X0 + c * PITCH + CX / 2, Y0 + CY, z0 + CZ - 2.2])), { size: 0.55, tone: "hi" }));
  }
  out.push(...cells);
  // ---- inverter / top block in the top space with fins
  const INV = { x: 22, y: 6, w: 86, d: 22, r: 1 };
  const iz = TOPZ + 8;
  out.push(S(k.slabOf(INV, iz, 16, P, 3, 0.5), { tone: "mid", inner: L(k.sideSeam(INV, iz + 12, P, 3), { tone: "faint" }) }));
  for (let i = 0; i < 9; i++) out.push(S(k.slabOf({ x: INV.x + 6 + i * 9.2, y: INV.y + 2, w: 1.4, d: INV.d - 4, r: 0.2 }, iz + 16, 5, P, 2), { tone: "lo", crease: "none" }));
  out.push(D([[INV.x + 3, INV.y + INV.d, iz + 3], [INV.x + INV.w - 3, INV.y + INV.d, iz + 3]].map(at), { size: 0.45 }));
  out.push(k.wireSvg(at([INV.x + INV.w - 6, INV.y + INV.d, iz + 2]), at([X0 + 16 * CX, Y0 + CY - 2.4, TOPZ + 0.7]), { via: [at([INV.x + INV.w - 6, INV.y + INV.d + 3, TOPZ + 4])], tone: "mid" }));
  // ---- air paths IN FRONT: front plenum rise to the top space, over the top, right side clearance
  flowsFront.push(fl([[65, Dp - 1, 2], [65, Dp - 6, 12], [65, Dp - 6, TOPZ + 4], [65, 8, TOPZ + 4], [65, 8, H - 2]], sh[8]));
  flowsFront.push(fl([[W - 3.7, Dp - 2, 5], [W - 3.7, Dp / 2, 12], [W - 3.7, Dp / 2, H - 6]], side / 2));
  out.push(`<g data-part="airfront">${flowsFront.join("")}</g>`);
  // ---- frame: corner posts on the open side, top rails, inlet kick panel with grille slats, roof rear with outlet slats
  out.push(S(k.slabOf({ x: W - 2.4, y: 0, w: 2.4, d: 2.4, r: 0.3 }, 0, H, P, 2), { tone: "mid", crease: "none" }));
  out.push(S(k.slabOf({ x: 0, y: Dp - 2.4, w: 2.4, d: 2.4, r: 0.3 }, 0, H, P, 2), { tone: "mid", crease: "none" }));
  const KICK = { x: 0, y: Dp - 1.2, w: W, d: 1.2, r: 0.2 };
  const slats = []; for (let z = 2.5; z < ZB - 1; z += 2.4) slats.push(k.segment([3, Dp, z], [W - 3, Dp, z], P));
  // the kick panel is the inlet grille: closed slots bounded by the panel edges
  out.push(S(k.slabOf(KICK, 0, ZB - 2, P, 2), { tone: "mid", crease: "none", inner: L(slats.join(""), { tone: "lo" }) }));
  const ROOF = { x: 0, y: 0, w: W, d: Dp * 0.45, r: 0.3 };
  const oslats = []; for (let x = 6; x < W - 4; x += 4) oslats.push(k.segment([x, 2, H + 1.2], [x, Dp * 0.45 - 2, H + 1.2], P));
  out.push(S(k.slabOf(ROOF, H, 1.2, P, 2, 0.3), { tone: "mid", inner: "" }), L(oslats.join(""), { tone: "lo" }));
  out.push(S(k.slabOf({ x: 0, y: Dp - 2.4, w: W, d: 2.4, r: 0.3 }, H - 2.4, 2.4, P, 2), { tone: "mid", crease: "none" }));
  out.push(S(k.slabOf({ x: W - 2.4, y: 0, w: 2.4, d: Dp, r: 0.3 }, H - 2.4, 2.4, P, 2), { tone: "mid", crease: "none" }));
  out.push(D([[W - 1.2, Dp - 1.2, H], [1.2, Dp - 1.2, H], [W - 1.2, 1.2, H]].map(at), { size: 0.5, tone: "mid" }));
  const svg = k.figureSvg({ width: WIDTH, height: HEIGHT, label: "The REON battery cabinet with its front and right panels removed: eight modules of sixteen cells stacked with 30 mm gaps, coloured by temperature; lines show where the cooling air goes.", body: out });
  const live = `
(() => {
${HEAT_JS}
const fT = ${JSON.stringify(forcedT.map((v) => +v.toFixed(2)))}, sT = ${JSON.stringify(sealed.T.map((v) => +v.toFixed(2)))};
const bT = ${byp ? JSON.stringify(byp.T.map((v) => +v.toFixed(2))) : "null"};
const fig = document.querySelector('[data-fig="cabinet"]');
const stage = fig.querySelector(".iso-stage"), svg = stage.querySelector("svg"), readout = fig.querySelector("[data-readout]");
const cells = [...svg.querySelectorAll("[data-cell]")], air = [...svg.querySelectorAll(".air")];
const still = matchMedia("(prefers-reduced-motion: reduce)");
const lab = (i) => "M0" + (Math.floor(i / 16) + 1) + "_C" + String(i % 16 + 1).padStart(2, "0");
const stats = (T) => { let i = 0; T.forEach((v, j) => { if (v > T[i]) i = j; }); return [i, T[i], Math.max(...T) - Math.min(...T)]; };
const FIELDS = bT ? [fT, sT, bT] : [fT, sT];
const NAMES = ["fan on, steady", "sealed, 40 °C, 2 h", "sealed, 13 bypassed, 2 h"];
const S = FIELDS.map(stats);
let mode = 0, frame = 0, last = 0, clock = 0, touring = !still.matches, visible = false, idle = 0;
function set(m) {
  mode = m;
  cells.forEach((c, i) => c.style.setProperty("--h", heatHex(FIELDS[m][i])));
  air.forEach((a) => a.toggleAttribute("data-off", m !== 0));
  const [i, T, sp] = S[m];
  const t = NAMES[m] + " · hottest " + lab(i) + " " + T.toFixed(1) + " °C";
  if (readout.textContent !== t) readout.textContent = t;
  stage.setAttribute("aria-checked", String(m !== 0));
}
function tick(now) { const dt = last ? Math.min((now - last) / 1000, 1 / 30) : 1 / 60; last = now;
  if (touring) { clock += dt; const m = Math.floor(clock / 5.5) % FIELDS.length; if (m !== mode) set(m); }
  frame = visible && touring ? requestAnimationFrame(tick) : 0; }
const run = () => { if (!frame && visible) { last = 0; frame = requestAnimationFrame(tick); } };
new IntersectionObserver((e) => { visible = e[e.length - 1].isIntersecting; if (visible) run(); }, { rootMargin: "120px 0px" }).observe(stage);
const steer = (m) => { touring = false; set(m); clearTimeout(idle); idle = setTimeout(() => { touring = !still.matches; clock = mode * 5.5; run(); }, 6000); };
stage.addEventListener("click", () => steer((mode + 1) % FIELDS.length));
stage.addEventListener("keydown", (ev) => { if (ev.key === " " || ev.key === "Enter") { ev.preventDefault(); steer((mode + 1) % FIELDS.length); } });
set(0);
})();
`;
  const [fi] = [forcedT.indexOf(Math.max(...forcedT))];
  const plate = k.plateHtml({
    fig: "Fig 1", title: "Where the heat and the air go",
    hint: byp ? "Click to switch cooling" : "Click: fan on / sealed",
    readout: `fan on · steady · hottest ${A.summary.hottest} ${A.summary.T_int_max.toFixed(1)} °C`,
    keys: [{ mark: "lit", label: "Cooling air (line width = share of flow)" }, { mark: "dotted", label: "30 mm gaps: almost no air" }, { mark: "raised", label: "128 cells, coloured by temperature" }],
    caption: `OpenFOAM 13 conjugate heat transfer, 98,784 cells, k-omega SST: of the 0.15 m³/s supplied at the bottom front, ${(sh[0] * 100 * (1 - side)).toFixed(0)}% runs under the bottom module, ${(side * 100).toFixed(0)}% bypasses up the side clearances, ${(sh[8] * 100 * (1 - side)).toFixed(0)}% rises in front and crosses over the top, and the seven gaps between modules carry under 1%. Fan on, held at full power: hottest cell ${A.summary.T_int_max.toFixed(1)} °C (steady state).${existsSync(`${RES}/openfoam/gci_A_sst.json`) ? (() => { const g = JSON.parse(readFileSync(`${RES}/openfoam/gci_A_sst.json`, "utf8")); return ` Three meshes (${g.cells.map((n) => n.toLocaleString("en-US")).join(", ")} cells) agree the gaps are starved and module 7 is hottest; the hottest cell converges toward ${g.peak_interior_C.extrapolated.toFixed(1)} °C (shown: medium mesh), and the side-bypass share is mesh-sensitive (${g.side_share.map((s) => Math.round(s * 100) + "%").join(", ")}).`; })() : ""} Sealed on a 40 °C day: ${sealed.src}, end of a 2 h discharge, hottest ${sealed.peakCell} ${sealed.peak.toFixed(1)} °C.${byp ? ` The same day with the 13 hottest cells bypassed at constant power: hottest ${byp.peakCell} ${byp.peak.toFixed(1)} °C. The bypassed cells cool, but the other 115 carry 11% more current and run hotter.` : ""}`,
    body: `<div class="iso-stage" tabindex="0" role="switch" aria-checked="false" aria-label="Switch between fan-cooled and sealed cabinet">${svg}</div>${scaleHtml()}`,
  });
  return { plate: `<div data-fig="cabinet">${plate}</div>`, live, css: HEAT_CSS + `.air{transition:opacity .6s var(--anatomy-ease)}.air[data-off]{opacity:0}` };
}
