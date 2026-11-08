// node preview.mjs blocks|module|cabinet [--light]  -> writes figures/out/<name>.html for capture
import { writeFileSync, mkdirSync } from "node:fs";
import * as k from "file:///C:/Users/anina/.claude/skills/anatomy/kit/iso-kit.mjs";
import { kitScript } from "file:///C:/Users/anina/.claude/skills/anatomy/scripts/inline-kit.mjs";
const name = process.argv[2];
const theme = process.argv.includes("--light") ? "light" : "dark";
const mod = await import(`./fig_${name}.mjs`);
const f = mod.build();
mkdirSync("C:/Users/anina/Downloads/MITEC/reon_thermal/figures/out", { recursive: true });
const html = k.pageHtml({ title: name, theme, body: `<style>${f.css || ""}</style>` + f.plate, script: kitScript() + f.live });
const file = `C:/Users/anina/Downloads/MITEC/reon_thermal/figures/out/${name}${theme === "light" ? "-light" : ""}.html`;
writeFileSync(file, html);
console.log("wrote", file);
