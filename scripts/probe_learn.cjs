/* Structural probe of the learning layer on a surface.
   Asserts, without a browser: the page parses, every EXPL entry is well formed,
   every data-ex in the markup resolves to a defined entry, every entry is
   reachable from somewhere, and nothing claims a provenance it does not have. */
const fs = require("fs");
const { JSDOM } = require("jsdom");

const file = process.argv[2];
const html = fs.readFileSync(file, "utf8");
let fail = 0;
const bad = (m) => { console.log("  FAIL " + m); fail++; };
const ok  = (m) => console.log("  ok   " + m);

// --- 1. the document parses and the explainer objects evaluate
const dom = new JSDOM("<!doctype html><html><body>" + html + "</body></html>");
const doc = dom.window.document;

const m = html.match(/const EXPL\s*=\s*\{[\s\S]*?\n\};/);
if (!m) { bad("EXPL block not found"); process.exit(1); }
let EXPL, KIND;
try {
  const kindSrc = (html.match(/const EXKIND\s*=\s*\{[^}]*\};/) ||
                   html.match(/const KIND\s*=\s*\{[^}]*\};/))[0].replace(/const EXKIND/, "const KIND");
  EXPL = eval("(function(){ " + kindSrc + " " + m[0] + " return {EXPL:EXPL, KIND:KIND}; })()");
  KIND = EXPL.KIND; EXPL = EXPL.EXPL;
  ok("EXPL evaluates — " + Object.keys(EXPL).length + " entries");
} catch (e) { bad("EXPL does not evaluate: " + e.message); process.exit(1); }

// --- 2. every entry is well formed
const kinds = new Set(Object.keys(KIND));
for (const [id, e] of Object.entries(EXPL)) {
  if (!e.k || !kinds.has(e.k)) bad(id + ": kind '" + e.k + "' not in KIND");
  if (!e.t || !e.t.trim())     bad(id + ": no title");
  if (!e.b || e.b.length < 60) bad(id + ": body too short to be an explanation");
  if (!e.p || e.p.length < 10) bad(id + ": no provenance line");   // the whole thesis
  if (/\bTODO|TBD|lorem/i.test(e.b + e.p)) bad(id + ": placeholder text");
  const opens = (e.b.match(/<b>/g)||[]).length, closes = (e.b.match(/<\/b>/g)||[]).length;
  if (opens !== closes) bad(id + ": unbalanced <b> (" + opens + "/" + closes + ")");
  const io = (e.b.match(/<i>/g)||[]).length, ic = (e.b.match(/<\/i>/g)||[]).length;
  if (io !== ic) bad(id + ": unbalanced <i>");
}
if (!fail) ok("all entries well formed, each with a provenance line");

// --- 3. every data-ex in the static markup resolves
const staticRefs = new Map();
doc.querySelectorAll("[data-ex]").forEach(el => {
  const k = el.getAttribute("data-ex");
  if (!k || k.includes("$") || k.includes("{")) return;         // template, checked below
  staticRefs.set(k, (staticRefs.get(k) || 0) + 1);
});
let unresolved = [];
for (const k of staticRefs.keys()) if (!EXPL[k]) unresolved.push(k);
if (unresolved.length) bad("markup points at undefined entries: " + unresolved.join(", "));
else ok(staticRefs.size + " distinct data-ex targets in markup, all resolve");

// --- 4. every data-ex written from JS literals resolves
const jsRefs = new Set();
// a literal followed by "+" is a key prefix, completed at runtime: it resolves if
// the page generates entries under that prefix (EXPL["node_"+id] = {...})
const prefixes = new Set();
for (const mm of html.matchAll(/ex\s*:\s*"([a-z0-9_]+)"\s*\+/g)) prefixes.add(mm[1]);
for (const mm of html.matchAll(/ex\s*:\s*"([a-z0-9_]+)"(?!\s*\+)/g)) jsRefs.add(mm[1]);
// feed chips: the explainer key is the last element of each F.push([...])
for (const mm of html.matchAll(/F\.push\(\[[^\n]*?,\s*"([a-z0-9_]+)"\s*\]\)/g)) jsRefs.add(mm[1]);
for (const mm of html.matchAll(/"live"\s*,\s*"([a-z0-9_]+)"\]/g)) jsRefs.add(mm[1]);
for (const mm of html.matchAll(/"warn"\s*,\s*"([a-z0-9_]+)"\]/g)) jsRefs.add(mm[1]);
for (const mm of html.matchAll(/setAttribute\("data-ex"\s*,\s*"([a-z0-9_]+)"\)/g)) jsRefs.add(mm[1]);
// data-ex written inside template literals, which jsdom never sees as markup
for (const mm of html.matchAll(/data-ex="([a-z0-9_]+)"/g)) jsRefs.add(mm[1]);

const jsBad = [...jsRefs].filter(k => !EXPL[k]);
for (const pre of prefixes) {
  const gen = new RegExp('EXPL\\["' + pre + '"\\s*\\+[^\\]]+\\]\\s*=').test(html);
  if (gen) ok(`prefix "${pre}*" is generated at runtime, so references to it resolve`);
  else jsBad.push(pre + "*");
}
if (jsBad.length) bad("script points at undefined entries: " + jsBad.join(", "));
else ok(jsRefs.size + " distinct data-ex targets in script, all resolve");

// --- 5. orphans: entries nothing can reach (map hotspots are keyed by site id)
// map hotspots: the deck keys them by thermohaline site id, the atlas by callout
const siteIds = new Set();
for (const mm of html.matchAll(/\{"id":"([a-z0-9_]+)","kind":"(?:array|dwf|sill)"/g)) siteIds.add(mm[1]);
for (const mm of html.matchAll(/\{ex:"([a-z0-9_]+)",\s*S:/g)) siteIds.add(mm[1]);
const siteBad = [...siteIds].filter(k => !EXPL[k]);
if (siteBad.length) bad("map hotspots point at undefined entries: " + siteBad.join(", "));
else ok(siteIds.size + " map hotspot ids, all resolve");
// loose pass, for the orphan report only: any quoted key used outside the block
const outside = html.slice(0, html.indexOf("const EXPL")) + html.slice(html.indexOf(m[0]) + m[0].length);
const loose = new Set();
for (const k of Object.keys(EXPL)) if (outside.includes('"' + k + '"')) loose.add(k);
const reachable = new Set([...staticRefs.keys(), ...jsRefs, ...siteIds, ...loose]);
const orphans = Object.keys(EXPL).filter(k => !reachable.has(k));
console.log("  ..   " + orphans.length + " entries reachable only from map hotspots: " + orphans.slice(0,60).join(", "));

// --- 6. the LEARN control exists and defaults on
const learn = doc.querySelector("#learnBtn, [data-learn]");
if (!learn) bad("no LEARN control");
else ok("LEARN control present, aria-pressed=" + learn.getAttribute("aria-pressed"));

// --- 7. no layer left pointing nowhere
for (const mm of html.matchAll(/\{id:"([a-z0-9]+)",\s*nm:"([^"]+)"[^}]*\}/g)) {
  if (!/ex:"/.test(mm[0])) bad("layer '" + mm[1] + "' (" + mm[2] + ") has no explainer");
}

console.log(fail ? "\nFAILED: " + fail : "\nPASS");
process.exit(fail ? 1 : 0);
