// Fig 3 - "What heats the hottest cell": a stack of gauge blocks on a surface plate, one block per cause,
// each block as tall as the kelvins that cause adds (exact Shapley attribution from 256 GPU runs).
// A height gauge beside the stack reads the cell temperature on a 25-75 C scale with the 60 C limit marked.
import * as k from "file:///C:/Users/anina/.claude/skills/anatomy/kit/iso-kit.mjs";
import { readFileSync } from "node:fs";

const RES = "C:/Users/anina/Downloads/MITEC/reon_thermal/results";
const sh = JSON.parse(readFileSync(`${RES}/gpu_studies.json`, "utf8")).shapley;

export function build() {
  const WIDTH = 600, HEIGHT = 420;
  const KPU = 2.6;                     // world units per kelvin
  const BASE_T = 25;
  const short = ["hot start 55 C", "hot site 40 C", "ageing 3x R", "other 127 cells", "own heat 6.1 W", "inverter inside", "busbar + switch", "sun"];
  const map = { "hot start (55 C)": 0, "hot site (40 C vs 25 C)": 1, "ageing (+12.2 W, 3x R)": 2, "other 127 cells' heat": 3,
    "own Joule heat (6.1 W)": 4, "inverter inside (750 W)": 5, "busbar + switch losses": 6, "sun on roof/side": 7 };
  const parts = sh.names.map((n, i) => ({ name: short[map[n]], K: sh.shapley_K[i], order: map[n] })).sort((a, b) => a.order - b.order);
  const PLATE = { x: -112, y: -46, w: 186, d: 92, r: 7 };
  const PH = 9, FOOT = 5;
  const PLINTH = 14;                   // the 25 C datum block
  const BLK = { x: -4, y: -26, w: 58, d: 52, r: 1.2 };
  const COL = { x: -88, y: 4, w: 11, d: 14, r: 1.5 };
  const zOf = (T) => PLINTH + (T - BASE_T) * KPU;
  const TOP_T = 76;
  const COL_TOP = zOf(TOP_T) + 6;
  const P = k.fitProjection([...k.boxCorners(PLATE, -PH - FOOT, 0), [COL.x, COL.y, COL_TOP + 4], [BLK.x + BLK.w, BLK.y + BLK.d, zOf(BASE_T + sh.total_rise_K) + 2]],
    WIDTH, HEIGHT, { pad: 28, azimuth: 38 });
  const at = (p) => k.iso(p, P);
  const S = (paths, style) => k.solidSvg(paths, style);
  const L = (d, style) => k.lineSvg(d, style);
  const D = (pts, style) => k.dotsSvg(pts, style);
  const out = [];
  // ---- surface plate on four feet, groove, screws, ruler strip
  out.push(`<path class="iso-halo" d="${k.haloOf(PLATE, -PH - FOOT, PH, P)}"/>`);
  const feet = k.corners(PLATE, 20).sort((a, b) => k.depthOf([...a, 0], P) - k.depthOf([...b, 0], P));
  for (const [x, y] of feet) {
    out.push(S(k.cylinder(x, y, 7, -PH - FOOT, 1.6, P, 28), { tone: "lo" }));
    out.push(S(k.cylinder(x, y, 5.2, -PH - FOOT + 1.6, FOOT - 1.6, P, 28), { tone: "mid" }));
  }
  out.push(S(k.slabOf(PLATE, -PH, PH, P, 8, 1.4), { tone: "mid" }));
  out.push(L(k.planOutline(k.insetPlan(PLATE, 5), 0, P), { tone: "lo" }));
  const screws = k.corners(PLATE, 10);
  out.push(L(screws.map(([x, y]) => k.ring(x, y, 2.2, 0, P, 16)).join(""), { tone: "lo" }));
  out.push(D(screws.map(([x, y]) => at([x, y, 0])), { size: 0.5 }));
  const strip = { x: PLATE.x + 16, y: PLATE.y + PLATE.d - 15, w: PLATE.w - 32, d: 7, r: 1 };
  out.push(S(k.slabOf(strip, 0, 0.6, P, 3), { tone: "lo", crease: "none" }));
  const ticks = k.topTicks(strip.x + 4, strip.x + strip.w - 4, 4, 5, strip.y + 0.8, 0.6, [2, 3.6], P);
  out.push(L(ticks.minor, { tone: "lo" }), L(ticks.major, { tone: "mid" }));
  // label plate with three rule lines
  const lab = { x: PLATE.x + 12, y: PLATE.y + 10, w: 34, d: 16, r: 1.2 };
  out.push(S(k.slabOf(lab, 0, 0.8, P, 3, 0.3), { tone: "lo" }));
  for (const [i, y] of [lab.y + 4, lab.y + 8, lab.y + 12].entries())
    out.push(L(k.lineOnTop([lab.x + 4, y], [lab.x + (i === 2 ? 18 : 28), y], 0.8, P), { tone: "faint", free: true }));
  out.push(D([at([lab.x + 2, lab.y + 2, 0.8]), at([lab.x + lab.w - 2, lab.y + lab.d - 2, 0.8])], { size: 0.4 }));

  // ---- height gauge: heavy base, column with the temperature scale, scriber carriage (moves)
  const GB = { x: COL.x - 12, y: COL.y - 12, w: 34, d: 38, r: 3 };
  out.push(`<path class="iso-halo" d="${k.haloOf(GB, 0, 1, P)}" style="filter:blur(5px)"/>`);
  out.push(S(k.slabOf(GB, 0, 9, P, 6, 0.8), { tone: "mid" }));
  out.push(L(k.planOutline(k.insetPlan(GB, 3), 9, P), { tone: "faint" }));
  out.push(D([[GB.x + 4, GB.y + 4], [GB.x + GB.w - 4, GB.y + 4], [GB.x + 4, GB.y + GB.d - 4]].map(([x, y]) => at([x, y, 9])), { size: 0.45 }));
  // column
  const colInner = [];
  for (let T = 25; T <= 75; T += 1) {
    const z = zOf(T), len = T % 5 === 0 ? 3.6 : 1.8;
    colInner.push(k.segment([COL.x + COL.w, COL.y + COL.d, z], [COL.x + COL.w - len, COL.y + COL.d, z], P));
  }
  out.push(S(k.slabOf(COL, 9, COL_TOP - 9, P, 3, 0.4), { tone: "mid", inner: L(colInner.join(""), { tone: "lo" }) }));
  out.push(L(k.segment([COL.x + COL.w, COL.y + COL.d, zOf(60)], [COL.x + 0.6, COL.y + COL.d, zOf(60)], P), { tone: "red" }));
  out.push(L(k.segment([COL.x + COL.w, COL.y + COL.d, zOf(60)], [COL.x + COL.w, COL.y + 0.6, zOf(60)], P), { tone: "red" }));
  out.push(k.faceTextSvg(k.sideMatrix([COL.x + 1.4, COL.y + COL.d, zOf(60) + 1.2], 0, P, "left"), "60", { size: 2.8, tone: "mid" }));
  out.push(S(k.slabOf(k.insetPlan(COL, -0.8), COL_TOP, 2, P, 3), { tone: "mid" }));
  // ---- gauge-block stack (one block per cause)
  const blocks = [];
  out.push(`<path class="iso-halo" d="${k.haloOf(BLK, 0, 1, P)}" style="filter:blur(4px)"/>`);
  out.push(S(k.slabOf(BLK, 0, PLINTH, P, 3, 0.5), { tone: "mid", crease: "lo" }));
  out.push(L(k.planOutline(k.insetPlan(BLK, 3), PLINTH, P, 3), { tone: "faint" }));
  out.push(k.faceTextSvg(k.sideMatrix([BLK.x + 4, BLK.y + BLK.d, PLINTH - 4.5], 0, P, "left"), "25 C", { size: 5.2, tone: "mid" }));
  let z = PLINTH;
  const tops = [z];
  parts.forEach((p, i) => {
    const h = Math.max(p.K * KPU, 0.7);
    const tone = p.name.startsWith("ageing") ? "hi" : (i === 0 || i === 1 || i === 7) ? "mid" : "hi";
    const lit = p.name.startsWith("ageing");
    const inner = h > 4 ? L(k.sideSeam(k.insetPlan(BLK, 0), z + h - 1.2, P, 3), { tone: "faint" }) : "";
    const engr = h > 6.5 ? k.faceTextSvg(k.sideMatrix([BLK.x + 4, BLK.y + BLK.d, z + h / 2 + 1.4], 0, P, "left"), `+${p.K.toFixed(1)} K`, { size: 5.2, tone: lit ? "hi" : "mid" }) : "";
    blocks.push(`<g data-block="${i}" class="gb" style="--d:${i}">${S(k.slabOf(BLK, z, h, P, 3, h > 3 ? 0.5 : 0), { tone, lit, crease: "lo", inner })}${engr}${h > 6 ? L(k.planOutline(k.insetPlan(BLK, 3), z + h, P, 3), { tone: "faint" }) : ""}</g>`);
    z += h; tops.push(z);
  });
  out.push(...blocks);
  // ---- scriber carriage on the column (moves with the reading)
  const car = [];
  const CAR = { x: COL.x - 3, y: COL.y - 3, w: COL.w + 6, d: COL.d + 6, r: 2 };
  car.push(S(k.slabOf(CAR, -6, 12, P, 4, 0.5), { tone: "mid" }));
  const knob = [CAR.x + CAR.w / 2, CAR.y + CAR.d + 3.2];
  car.push(S(k.slabOf({ x: knob[0] - 1.4, y: CAR.y + CAR.d, w: 2.8, d: 2.2, r: 0.6 }, -1, 3, P, 2), { tone: "mid", crease: "none" }));
  car.push(S(k.cylinder(knob[0], knob[1], 2.8, -3, 6, P, 22), { tone: "mid" }));
  car.push(L(k.knurl(knob[0], knob[1], 2.8, -3, 3, 18, P), { tone: "lo" }));
  const AY = COL.y + COL.d / 2;
  const ARM = { x: CAR.x + CAR.w, y: AY - 2.5, w: BLK.x + BLK.w / 2 - (CAR.x + CAR.w), d: 5, r: 1 };
  car.push(S(k.slabOf(ARM, -1, 3.2, P, 3, 0.4), { tone: "hi", lit: true }));
  car.push(S(k.slabOf({ x: ARM.x + ARM.w - 3, y: AY - 3.4, w: 8, d: 6.8, r: 1 }, -0.2, 1.6, P, 3), { tone: "hi", lit: true }));
  car.push(D([at([ARM.x + 4, AY, 2.2]), at([ARM.x + ARM.w - 6, AY, 2.2])], { size: 0.45 }));
  car.push(L(k.segment([CAR.x, CAR.y + CAR.d, 0], [CAR.x + CAR.w, CAR.y + CAR.d, 0], P), { tone: "lit" }));
  const zEnd = tops[tops.length - 1];
  out.push(`<g data-part="carriage" transform="${k.translateAlong(P, [0, 0, zEnd])}">${car.join("")}</g>`);
  const svg = k.figureSvg({ width: WIDTH, height: HEIGHT, label: "A stack of gauge blocks on a surface plate. Each block is as tall as the temperature rise one cause adds to the hottest cell, from a 25 C datum; a height gauge reads the total against a scale with the 60 C limit marked.", body: out });
  const T_end = BASE_T + sh.total_rise_K;
  const live = `
(() => {
const P = ${JSON.stringify(P)};
const tops = ${JSON.stringify(tops)}, KPU = ${KPU}, PL = ${PLINTH};
const names = ${JSON.stringify(parts.map((p) => p.name))}, Ks = ${JSON.stringify(parts.map((p) => p.K))};
const fig = document.querySelector('[data-fig="blocks"]');
const stage = fig.querySelector(".iso-stage"), svg = stage.querySelector("svg");
const car = svg.querySelector('[data-part="carriage"]'), readout = fig.querySelector("[data-readout]");
const blocks = [...svg.querySelectorAll("[data-block]")];
const still = matchMedia("(prefers-reduced-motion: reduce)");
let step = names.length, z = tops[step], target = z, frame = 0, last = 0, clock = 0, touring = !still.matches, visible = false, idle = 0;
function show(n) {
  step = n; target = tops[n];
  blocks.forEach((b, i) => b.toggleAttribute("data-off", i >= n));
  const T = 25 + (tops[n] - PL) / KPU;
  const t = n === 0 ? "start: 25.0 C datum" : "+ " + names[n - 1] + " " + Ks[n - 1].toFixed(1) + " K · cell at " + T.toFixed(1) + " C";
  if (readout.textContent !== t) readout.textContent = t;
}
function tick(now) {
  const dt = last ? Math.min((now - last) / 1000, 1 / 30) : 1 / 60; last = now;
  if (touring) { clock += dt; const n = (Math.floor(clock / 1.5) + names.length) % (names.length + 3); const s = Math.min(n, names.length); if (s !== step) show(s); }
  z = still.matches ? target : z + (target - z) * (1 - Math.exp(-dt / 0.25));
  if (Math.abs(target - z) < 0.01) z = target;
  car.setAttribute("transform", translateAlong(P, [0, 0, z]));
  frame = visible && (touring || z !== target) ? requestAnimationFrame(tick) : 0;
}
const run = () => { if (!frame && visible) { last = 0; frame = requestAnimationFrame(tick); } };
new IntersectionObserver((e) => { visible = e[e.length - 1].isIntersecting; if (visible) run(); }, { rootMargin: "120px 0px" }).observe(stage);
const steer = (n) => { touring = false; show(n); clearTimeout(idle); idle = setTimeout(() => { touring = !still.matches; clock = 0; run(); }, 4000); run(); };
stage.addEventListener("pointermove", (ev) => { const b = svg.getBoundingClientRect(); const f = 1 - (ev.clientY - b.top) / b.height; steer(Math.max(0, Math.min(names.length, Math.round((f - 0.18) / 0.62 * names.length)))); });
stage.addEventListener("keydown", (ev) => { if (ev.key === "ArrowUp" || ev.key === "ArrowRight") { ev.preventDefault(); steer(Math.min(names.length, step + 1)); } if (ev.key === "ArrowDown" || ev.key === "ArrowLeft") { ev.preventDefault(); steer(Math.max(0, step - 1)); } });
show(names.length);
})();
`;
  const plate = k.plateHtml({
    fig: "Fig 3", title: "What heats the hottest cell",
    hint: "Hover up and down to add causes",
    readout: `all causes · cell at ${T_end.toFixed(1)} C`,
    keys: [{ mark: "lit", label: "Ageing (3× resistance): the part a bypass can remove" }, { mark: "raised", label: "Electrical heat: own cell, the other 127, inverter, busbars" },
      { mark: "flat", label: "Site: hot start, hot ambient, sun" }, { mark: "red", label: "60 C cell limit" }],
    caption: `Each block is one cause's share of the hottest cell's rise above 25 C (exact Shapley split over all 256 on/off combinations, 2 h sealed discharge). Bottom to top: ${parts.map((p) => p.name + " " + p.K.toFixed(1) + " K").join(", ")}. Total ${sh.total_rise_K.toFixed(1)} K.`,
    body: `<div class="iso-stage" tabindex="0" role="slider" aria-label="Causes of the hottest cell temperature, arrow keys add or remove causes" aria-valuemin="0" aria-valuemax="8">${svg}</div>`,
  });
  return { plate: `<div data-fig="blocks">${plate}</div>`, live, css: `.gb{transition:opacity .45s var(--anatomy-ease)}.gb[data-off]{opacity:.12}` };
}
