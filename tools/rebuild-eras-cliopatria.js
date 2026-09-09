// 将全部 49 个时代切片整体重建为纯 Cliopatria（Seshat Global History Databank, CC BY 4.0）数据。
// 规则：
//  - 每个年份取 Type=POLITY 且 FromYear<=Y<=ToYear 的记录；
//  - 跳过伞记录（Components 非空）与括号别名记录（Name 以 "(" 开头），其几何与成员政权重复；
//  - 不改写任何坐标，仅做与 prepare-eras.js 一致的降精度/去重复点简化；
//  - 从被覆盖的旧切片按 NAME 继承已考据的 capital/type/region 元数据；
//  - 中文名与 _a/_c 由 tools/add-nz.js 统一注入。
// 旧切片已备份至 data/eras-backup/。用法：node tools/rebuild-eras-cliopatria.js
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const ERAS_DIR = path.join(ROOT, 'data', 'eras');
const CLIO = path.join(__dirname, 'cliopatria', 'cliopatria_polities_only.geojson');
const SOURCE = 'Cliopatria / Seshat Global History Databank (CC BY 4.0)';

const ERAS = [-3000, -2000, -1500, -1000, -700, -500, -400, -323, -300, -200, -100, -1,
  100, 200, 300, 376, 400, 500, 600, 700, 800, 900, 950, 1000, 1100, 1200, 1279, 1300, 1400, 1492,
  1500, 1530, 1600, 1650, 1700, 1715, 1783, 1800, 1815, 1880, 1900, 1914, 1920, 1930,
  1938, 1945, 1960, 1994, 2000];
const fileFor = y => y < 0 ? `world_bc${-y}.geojson` : `world_${y}.geojson`;

function hashName(s) { let h = 0; for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0; return h; }

function roundCoords(c) {
  return typeof c[0] === 'number'
    ? [Math.round(c[0] * 100) / 100, Math.round(c[1] * 100) / 100]
    : c.map(roundCoords);
}
function dedupeRing(ring) {
  const out = [];
  for (const p of ring) {
    const last = out[out.length - 1];
    if (!last || p[0] !== last[0] || p[1] !== last[1]) out.push(p);
  }
  if (out.length > 3 && (out[0][0] !== out[out.length - 1][0] || out[0][1] !== out[out.length - 1][1])) out.push(out[0]);
  return out.length >= 4 ? out : null;
}
function simplifyGeom(g) {
  const rounded = roundCoords(g.coordinates);
  if (g.type === 'Polygon') {
    const rings = rounded.map(dedupeRing).filter(Boolean);
    return rings.length ? { type: 'Polygon', coordinates: rings } : null;
  }
  const polys = rounded.map(p => p.map(dedupeRing).filter(Boolean)).filter(p => p.length);
  return polys.length ? { type: 'MultiPolygon', coordinates: polys } : null;
}

// 从旧切片继承元数据（1200/950/376 等已人工考据过 capital/type/region）
const META = new Map();
for (const f of fs.readdirSync(ERAS_DIR)) {
  if (!f.endsWith('.geojson')) continue;
  const fc = JSON.parse(fs.readFileSync(path.join(ERAS_DIR, f), 'utf8'));
  for (const feat of fc.features) {
    const p = feat.properties || {};
    if (!p.NAME || META.has(p.NAME)) continue;
    if (p.capital || p.type || p.region) META.set(p.NAME, { capital: p.capital || '', type: p.type || '', region: p.region || '' });
  }
}
console.log(`元数据继承表：${META.size} 个政权名`);

console.log('parsing Cliopatria (158MB)...');
const t0 = Date.now();
const clio = JSON.parse(fs.readFileSync(CLIO, 'utf8'));
const pol = clio.features.filter(f => f.properties.Type === 'POLITY');
console.log(`parsed in ${Date.now() - t0}ms, POLITY 记录 ${pol.length}`);

let total = 0;
for (const y of ERAS) {
  const rows = pol.filter(f =>
    f.properties.FromYear <= y && y <= f.properties.ToYear &&
    !f.properties.Components && !f.properties.Name.startsWith('('));
  const feats = [];
  let dropped = 0;
  for (const f of rows) {
    const p = f.properties;
    const geom = simplifyGeom(f.geometry);
    if (!geom) { dropped++; continue; }
    const meta = META.get(p.Name) || {};
    feats.push({
      type: 'Feature',
      properties: {
        NAME: p.Name,
        C: hashName(p.Name) % 12,
        name: p.Name,
        start_year: p.FromYear,
        end_year: p.ToYear,
        capital: meta.capital || '',
        type: meta.type || 'polity',
        region: meta.region || '',
        event: '',
        source: SOURCE,
        wikipedia: p.Wikipedia || '',
        wikidata: p.Wikidata || ''
      },
      geometry: geom
    });
  }
  const outPath = path.join(ERAS_DIR, fileFor(y));
  fs.writeFileSync(outPath, JSON.stringify({ type: 'FeatureCollection', features: feats }));
  total += feats.length;
  console.log(`${fileFor(y).padEnd(22)} ${String(feats.length).padStart(3)} 个政权${dropped ? `（丢弃空几何 ${dropped}）` : ''}`);
}
console.log(`\n✓ 49 个切片全部重建为 Cliopatria 数据，共 ${total} 个要素`);
