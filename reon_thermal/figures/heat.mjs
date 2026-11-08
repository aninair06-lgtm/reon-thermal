// Shared fixed 20-70 C colour scale (inferno-like, perceptual) and CSS that tints a solid by --h.
export const T_MIN = 20, T_MAX = 70;
const STOPS = [[0, [20, 11, 52]], [0.2, [66, 10, 104]], [0.4, [147, 38, 103]], [0.6, [221, 81, 58]], [0.8, [249, 155, 32]], [1, [252, 245, 140]]];
export function heatRGB(T) {
  const t = Math.max(0, Math.min(1, (T - T_MIN) / (T_MAX - T_MIN)));
  for (let i = 1; i < STOPS.length; i++) {
    if (t <= STOPS[i][0]) {
      const [t0, a] = STOPS[i - 1], [t1, b] = STOPS[i]; const f = (t - t0) / (t1 - t0);
      return a.map((v, j) => Math.round(v + (b[j] - v) * f));
    }
  }
  return STOPS[STOPS.length - 1][1];
}
export const heatHex = (T) => "#" + heatRGB(T).map((v) => v.toString(16).padStart(2, "0")).join("");
export const HEAT_JS = `const HSTOPS=${JSON.stringify(STOPS)};function heatHex(T){const t=Math.max(0,Math.min(1,(T-${T_MIN})/${T_MAX - T_MIN}));for(let i=1;i<HSTOPS.length;i++){if(t<=HSTOPS[i][0]){const[t0,a]=HSTOPS[i-1],[t1,b]=HSTOPS[i];const f=(t-t0)/(t1-t0);return"#"+a.map((v,j)=>Math.round(v+(b[j]-v)*f).toString(16).padStart(2,"0")).join("")}}return"#fcf58c"}`;
export const HEAT_CSS = `
.hc .iso-top{fill:var(--h)}
.hc .iso-shade[data-shade="0"]{fill:color-mix(in oklab,var(--h) 52%,#000)}
.hc .iso-shade[data-shade="1"]{fill:color-mix(in oklab,var(--h) 60%,#000)}
.hc .iso-shade[data-shade="2"]{fill:color-mix(in oklab,var(--h) 70%,#000)}
.hc .iso-shade[data-shade="3"]{fill:color-mix(in oklab,var(--h) 80%,#000)}
.hc .iso-fill{fill:color-mix(in oklab,var(--h) 60%,#000)}
.hc .iso-top,.hc .iso-shade,.hc .iso-fill{transition:fill .5s var(--anatomy-ease)}
.heat-scale{display:flex;align-items:center;gap:8px;font:11px var(--anatomy-mono);color:var(--anatomy-text);margin:6px 0 0}
.heat-scale i{flex:1;height:8px;border-radius:2px;background:linear-gradient(90deg,${STOPS.map(([t, c]) => `rgb(${c.join(",")}) ${t * 100}%`).join(",")})}
`;
export const scaleHtml = () => `<div class="heat-scale"><span>${T_MIN} &deg;C</span><i></i><span>${T_MAX} &deg;C</span></div>`;
