// Fig 2 - One module on a bench (Elmer 3D result): 16 cells in a compression frame, series busbars on top,
// a switch board on every cell. Cell 8 is aged (3x resistance, 18.3 W). The tour flips its bypass:
// the string current jumps to the bypass strap, the cell stops heating and cools; the dial thermometer follows.
import * as k from "file:///C:/Users/anina/.claude/skills/anatomy/kit/iso-kit.mjs";
import { readFileSync } from "node:fs";
import { heatHex, HEAT_JS, HEAT_CSS, scaleHtml } from "./heat.mjs";

const RES = "C:/Users/anina/Downloads/MITEC/reon_thermal/results";
const el = JSON.parse(readFileSync(`${RES}/elmer_module.json`, "utf8"));

export function build() {
  const WIDTH = 620, HEIGHT = 400;
  const U = 1 / 3;                                // world units per mm
  const CX = 71.7 * U, CY = 174.7 * U, CZ = 207 * U, PAD = 0.2 * U * 4;
  const N = 16, AGED = 7;
  const PITCH = CX + PAD;
  const LEN = N * CX + (N - 1) * PAD;
  const END = 9.9 * U * 1.6;                       // end plate thickness (drawn a little thicker to read)
  const X0 = -LEN / 2, Y0 = -CY / 2, TRAY_Z = 4;
  const BENCH = { x: X0 - END - 16, y: Y0 - 16, w: LEN + 2 * END + 32, d: CY + 70, r: 8 };
  const P = k.fitProjection([...k.boxCorners(BENCH, -14, 0), [X0, Y0, CZ + 8], [X0 + LEN, Y0 + CY, CZ + 8]],
    WIDTH, HEIGHT, { pad: 16, azimuth: 30 });
  const at = (p) => k.iso(p, P);
  const S = (paths, style) => k.solidSvg(paths, style);
  const L = (d, style) => k.lineSvg(d, style);
  const D = (pts, style) => k.dotsSvg(pts, style);
  const inT = el.mod_aged_r2.cell_mean_end, byT = el.mod_byp_r1.cell_mean_end;
  const out = [];
  // ---- bench
  out.push(`<path class="iso-halo" d="${k.haloOf(BENCH, -14, 10, P)}"/>`);
  for (const [x, y] of k.corners(BENCH, 18).sort((a, b) => k.depthOf([...a, 0], P) - k.depthOf([...b, 0], P))) {
    out.push(S(k.cylinder(x, y, 7, -14, 1.6, P, 28), { tone: "lo" }));
    out.push(S(k.cylinder(x, y, 5.2, -12.4, 2.4, P, 28), { tone: "mid" }));
  }
  out.push(S(k.slabOf(BENCH, -10, 10, P, 8, 1.4), { tone: "mid" }));
  out.push(L(k.planOutline(k.insetPlan(BENCH, 5), 0, P), { tone: "lo" }));
  const sc = k.corners(BENCH, 10);
  out.push(L(sc.map(([x, y]) => k.ring(x, y, 2.2, 0, P, 16)).join(""), { tone: "lo" }), D(sc.map(([x, y]) => at([x, y, 0])), { size: 0.5 }));
  const strip = { x: X0, y: BENCH.y + BENCH.d - 14, w: LEN, d: 6, r: 1 };
  out.push(S(k.slabOf(strip, 0, 0.6, P, 3), { tone: "lo", crease: "none" }));
  const tk = k.topTicks(strip.x + 2, strip.x + strip.w - 2, PITCH / 2, 2, strip.y + 0.8, 0.6, [1.8, 3.4], P);
  out.push(L(tk.minor, { tone: "lo" }), L(tk.major, { tone: "mid" }));
  // ---- module tray
  const TRAY = { x: X0 - END - 2, y: Y0 - 3, w: LEN + 2 * END + 4, d: CY + 6, r: 2 };
  out.push(`<path class="iso-halo" d="${k.haloOf(TRAY, 0, 1, P)}" style="filter:blur(4px)"/>`);
  out.push(S(k.slabOf(TRAY, 0, TRAY_Z, P, 4, 0.6), { tone: "mid" }));
  out.push(D([[TRAY.x + 3, TRAY.y + 3], [TRAY.x + TRAY.w - 3, TRAY.y + 3], [TRAY.x + 3, TRAY.y + TRAY.d - 3], [TRAY.x + TRAY.w - 3, TRAY.y + TRAY.d - 3]].map(([x, y]) => at([x, y, TRAY_Z])), { size: 0.45 }));
  // back end plate
  const endPlate = (x) => {
    const pl = { x, y: Y0 - 2, w: END, d: CY + 4, r: 1 };
    const o = [S(k.slabOf(pl, TRAY_Z, CZ + 2, P, 3, 0.5), { tone: "mid" })];
    o.push(D([0.2, 0.5, 0.8].flatMap((f) => [[x + END, Y0 + 6, TRAY_Z + f * CZ], [x + END, Y0 + CY - 6, TRAY_Z + f * CZ]]).map((p) => at(p)), { size: 0.5, tone: "mid" }));
    return o.join("");
  };
  out.push(endPlate(X0 - END));
  // ---- cells, back to front along x (depth grows with x for this azimuth)
  const cellG = [];
  for (let c = 0; c < N; c++) {
    const x = X0 + c * PITCH;
    const cl = { x, y: Y0, w: CX, d: CY, r: 0.8 };
    const seam = L(k.sideSeam(cl, TRAY_Z + CZ - 3, P, 2), { tone: "faint" });
    cellG.push(`<g class="hc" data-cell="${c}" style="--h:${heatHex(inT[c])}">${S(k.slabOf(cl, TRAY_Z, CZ, P, 2, 0.4), { tone: "hi", crease: "lo", inner: seam })}</g>`);
    // vent and label rules on top
    const zt = TRAY_Z + CZ;
    cellG.push(L(k.ring(x + CX / 2, Y0 + CY / 2, 2.2, zt, P, 16), { tone: "lo" }));
    // terminals
    for (const ty of [Y0 + 11, Y0 + CY - 11]) cellG.push(S(k.cylinder(x + CX / 2, ty, 3.1, zt, 2.6, P, 18), { tone: "mid" }));
  }
  out.push(...cellG);
  out.push(endPlate(X0 + LEN));
  // tie rods along the module, front and back, ending in nuts on the end plates
  for (const y of [Y0 + 4, Y0 + CY - 4]) {
    out.push(S(k.slabOf({ x: X0 - END, y: y - 1.2, w: LEN + 2 * END, d: 2.4, r: 1.2 }, TRAY_Z + CZ + 1.2, 2.2, P, 4), { tone: "lo", crease: "none" }));
  }
  // ---- busbars (series) and switch boards
  const zt = TRAY_Z + CZ + 2.6;
  const busFront = [], busBack = [];
  for (let c = 0; c < N - 1; c++) {
    const x1 = X0 + c * PITCH + CX / 2, x2 = x1 + PITCH;
    const y = c % 2 === 0 ? Y0 + CY - 11 : Y0 + 11;
    (c % 2 === 0 ? busFront : busBack).push(S(k.slabOf({ x: x1 - 1.6, y: y - 3, w: x2 - x1 + 3.2, d: 6, r: 1.4 }, zt, 1.4, P, 3, 0.3), { tone: "mid" }));
  }
  out.push(...busBack, ...busFront);
  const boards = [];
  for (let c = 0; c < N; c++) {
    const x = X0 + c * PITCH;
    const bd = { x: x + 2.2, y: Y0 + 20, w: CX - 4.4, d: CY - 40, r: 0.8 };
    const aged = c === AGED;
    boards.push(S(k.slabOf(bd, TRAY_Z + CZ, 1.6, P, 2, 0.3), { tone: aged ? "hi" : "lo", lit: aged }));
    boards.push(D([at([x + CX / 2, Y0 + 26, TRAY_Z + CZ + 1.6])], { size: 0.55, tone: aged ? "hi" : "mid" }));
    // relay can on the board
    boards.push(S(k.slabOf({ x: x + CX / 2 - 2.6, y: Y0 + CY / 2 - 4, w: 5.2, d: 8, r: 0.6 }, TRAY_Z + CZ + 1.6, 2.4, P, 2), { tone: "mid" }));
  }
  out.push(...boards);
  // bypass strap over the aged cell: drawn lit when bypassed (data-part toggles)
  const xa = X0 + AGED * PITCH;
  const strapY = Y0 + CY / 2 + 9;
  const strap = S(k.slabOf({ x: xa - PITCH / 2 + CX / 2 - 1, y: strapY - 2, w: PITCH + 2, d: 4, r: 1 }, zt + 1.4, 1.2, P, 3), { tone: "hi", lit: true });
  out.push(`<g data-part="strap" class="strap">${strap}</g>`);
  // current path: string current through the cells (flow line on busbars), two variants
  const pathThrough = [], pathBypass = [];
  for (let c = 0; c < N; c++) {
    const xc = X0 + c * PITCH + CX / 2;
    pathThrough.push([xc, Y0 + 11, zt + 1.6], [xc, Y0 + CY - 11, zt + 1.6]);
  }
  const through = pathThrough.map((p, i) => (i % 4 === 0 || i % 4 === 3 ? p : p)).map((p) => at(p));
  // build zig-zag order: cell c goes - to + ; series alternates
  const zig = [];
  for (let c = 0; c < N; c++) {
    const xc = X0 + c * PITCH + CX / 2;
    const a = c % 2 === 0 ? Y0 + 11 : Y0 + CY - 11, b = c % 2 === 0 ? Y0 + CY - 11 : Y0 + 11;
    zig.push([xc, a, zt + 1.6], [xc, b, zt + 1.6]);
  }
  const zigBy = zig.slice(0, AGED * 2).concat([[X0 + (AGED - 1) * PITCH + CX / 2, strapY, zt + 2.8], [X0 + (AGED + 1) * PITCH + CX / 2, strapY, zt + 2.8]], zig.slice((AGED + 1) * 2));
  const dOf = (pts) => "M" + pts.map((p) => at(p).map((v) => v.toFixed(1)).join(" ")).join("L");
  out.push(`<path data-part="flow" class="iso-line" data-tone="lit" data-flow="" d="${dOf(zig)}" style="stroke-width:.9"/>`);
  // ---- dial thermometer on a stand, probe wire to the aged cell's front face
  const DIAL = [xa + 40, Y0 + CY + 36], DR = 21, DZ = 44;
  out.push(S(k.slabOf({ x: DIAL[0] - 12, y: DIAL[1] - 10, w: 24, d: 20, r: 2 }, 0, 6, P, 4, 0.6), { tone: "mid" }));
  out.push(S(k.cylinder(DIAL[0], DIAL[1], 2.2, 6, DZ - 6, P, 16), { tone: "mid" }));
  out.push(S(k.cylinder(DIAL[0], DIAL[1], DR, DZ, 6, P, 56, 0.6), { tone: "hi", crease: "lo" }));
  out.push(L(k.ring(DIAL[0], DIAL[1], DR - 2, DZ + 6, P, 56), { tone: "lo" }));
  const T0 = 40, T1 = 60, SPAN = 1.5 * Math.PI, FROM = -0.75 * Math.PI;
  const rt = k.radialTicks(DIAL[0], DIAL[1], DR - 3, 20, 5, DZ + 6, [1.2, 2.6], P, FROM, SPAN);
  out.push(L(rt.minor, { tone: "lo" }), L(rt.major, { tone: "mid" }));
  out.push(k.faceTextSvg(k.topMatrix([DIAL[0], DIAL[1] + 8], DZ + 6, P, "x"), "°C", { size: 3, tone: "lo", anchor: "middle" }));
  const needle = (T) => {
    const f = Math.max(0, Math.min(1, (T - T0) / (T1 - T0))); const a = FROM + f * SPAN;
    return k.lineOnTop([DIAL[0] - Math.sin(a) * 2.5, DIAL[1] + Math.cos(a) * 2.5], [DIAL[0] + Math.sin(a) * (DR - 4), DIAL[1] - Math.cos(a) * (DR - 4)], DZ + 6.2, P);
  };
  out.push(`<path data-part="needle" class="iso-line" data-tone="lit" data-free="start" d="${needle(el.mod_aged_r2.cell_max_end[7])}" style="stroke-width:1.1"/>`);
  out.push(D([at([DIAL[0], DIAL[1], DZ + 6.2])], { size: 0.8, tone: "hi" }));
  out.push(k.wireSvg(at([DIAL[0] - 12, DIAL[1] - 2, 3]), at([xa + CX / 2, Y0 + CY, TRAY_Z + CZ * 0.55]), { via: [at([xa + CX / 2, Y0 + CY + 14, 3])], tone: "mid" }));
  const svg = k.figureSvg({ width: WIDTH, height: HEIGHT, label: "One battery module of 16 cells on a bench, with series busbars and a switch board on each cell. Cell 8 is aged and runs hot; when its switch bypasses it, the string current takes a strap over the cell and the cell cools.", body: out });
  const live = `
(() => {
${HEAT_JS}
const P = ${JSON.stringify(P)};
const inT = ${JSON.stringify(inT)}, byT = ${JSON.stringify(byT)}, PEAK_IN = ${el.mod_aged_r2.cell_max_end[7]}, PEAK_BY = ${el.mod_byp_r1.cell_max_end[7]};
const DIAL = ${JSON.stringify(DIAL)}, DR = ${DR}, DZ = ${DZ}, T0 = ${T0}, T1 = ${T1}, SPAN = ${SPAN}, FROM = ${FROM};
const zig = ${JSON.stringify(zig)}, zigBy = ${JSON.stringify(zigBy)};
const fig = document.querySelector('[data-fig="module"]');
const stage = fig.querySelector(".iso-stage"), svg = stage.querySelector("svg"), readout = fig.querySelector("[data-readout]");
const cells = [...svg.querySelectorAll("[data-cell]")], flow = svg.querySelector('[data-part="flow"]'), strap = svg.querySelector('[data-part="strap"]');
const needle = svg.querySelector('[data-part="needle"]');
const still = matchMedia("(prefers-reduced-motion: reduce)");
const dOf = (pts) => "M" + pts.map((p) => iso(p, P).map((v) => v.toFixed(1)).join(" ")).join("L");
let byp = false, mix = 0, frame = 0, last = 0, clock = 0, touring = !still.matches, visible = false, idle = 0, shown = -1;
function needleAt(T) { const f = Math.max(0, Math.min(1, (T - T0) / (T1 - T0))); const a = FROM + f * SPAN;
  return lineOnTop([DIAL[0] - Math.sin(a) * 2.5, DIAL[1] + Math.cos(a) * 2.5], [DIAL[0] + Math.sin(a) * (DR - 4), DIAL[1] - Math.cos(a) * (DR - 4)], DZ + 6.2, P); }
function set(b) { byp = b; flow.setAttribute("d", dOf(b ? zigBy : zig)); strap.toggleAttribute("data-on", b); }
function draw() {
  cells.forEach((c, i) => c.style.setProperty("--h", heatHex(inT[i] + (byT[i] - inT[i]) * mix)));
  const T = PEAK_IN + (PEAK_BY - PEAK_IN) * mix;
  needle.setAttribute("d", needleAt(T));
  const txt = (byp ? "cell 8 bypassed · 127 cells carry the string · " : "cell 8 aged, in string · 18.3 W · ") + "cell 8 at " + T.toFixed(1) + " °C";
  if (readout.textContent !== txt) readout.textContent = txt;
}
function tick(now) {
  const dt = last ? Math.min((now - last) / 1000, 1 / 30) : 1 / 60; last = now;
  if (touring) { clock += dt; const b = Math.floor(clock / 4.5) % 2 === 1; if (b !== byp) set(b); }
  const goal = byp ? 1 : 0;
  mix = still.matches ? goal : mix + (goal - mix) * (1 - Math.exp(-dt / 0.9));
  if (Math.abs(goal - mix) < 0.002) mix = goal;
  draw();
  frame = visible && (touring || mix !== goal) ? requestAnimationFrame(tick) : 0;
}
const run = () => { if (!frame && visible) { last = 0; frame = requestAnimationFrame(tick); } };
new IntersectionObserver((e) => { visible = e[e.length - 1].isIntersecting; if (visible) run(); }, { rootMargin: "120px 0px" }).observe(stage);
const steer = (b) => { touring = false; set(b); clearTimeout(idle); idle = setTimeout(() => { touring = !still.matches; clock = byp ? 4.5 : 0; run(); }, 5000); run(); };
stage.addEventListener("click", () => steer(!byp));
stage.addEventListener("keydown", (ev) => { if (ev.key === " " || ev.key === "Enter") { ev.preventDefault(); steer(!byp); } });
set(false); draw();
})();
`;
  const plate = k.plateHtml({
    fig: "Fig 2", title: "Bypassing one aged cell",
    hint: "Click to flip the bypass",
    readout: `cell 8 aged, in string · 18.3 W · cell 8 at ${el.mod_aged_r2.cell_max_end[7].toFixed(1)} °C`,
    keys: [{ mark: "lit", label: "String current and the bypass strap" }, { mark: "raised", label: "Cells, coloured by temperature after a 2 h discharge" }],
    caption: `Elmer FEM, one module: 16 cells, 15 resolved 0.2 mm interface layers, through-cell k = 1 W/m K, in-plane 25 W/m K; 40 °C air, h = 3 W/m² K, 2 h. Aged cell 8 (3× resistance) peaks at ${el.mod_aged_r2.peak_internal_C.toFixed(1)} °C and warms its neighbours to ${inT[6].toFixed(1)} °C; bypassed, it settles at ${byT[7].toFixed(1)} °C and the module peak is ${el.mod_byp_r1.peak_internal_C.toFixed(1)} °C. Three meshes agree within 0.03 K.`,
    body: `<div class="iso-stage" tabindex="0" role="switch" aria-checked="false" aria-label="Bypass switch for aged cell 8">${svg}</div>${scaleHtml()}`,
  });
  return { plate: `<div data-fig="module">${plate}</div>`, live, css: HEAT_CSS + `.strap{opacity:0;transition:opacity .4s var(--anatomy-ease)}.strap[data-on]{opacity:1}` };
}
