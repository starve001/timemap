// 按年份列表生成缺失的版图切片并插入 index.json，规则与 rebuild-eras-cliopatria.js 一致
// 用法：node tools/add-era-slices.js 或 node tools/add-era-slices.js 260 570 930
const fs = require('fs');
const path = require('path');
const ROOT = path.join(__dirname, '..');
const ERAS_DIR = path.join(ROOT, 'data', 'eras');
const CLIO = path.join(__dirname, 'cliopatria', 'cliopatria_polities_only.geojson');
const SOURCE = 'Cliopatria / Seshat Global History Databank (CC BY 4.0)';
const YEARS = (process.argv.slice(2).map(Number).filter(Number.isFinite).length
  ? process.argv.slice(2).map(Number).filter(Number.isFinite)
  : [-1200, 260, 330, 460, 570, 930]).sort((a, b) => a - b);
const fileFor = y => y < 0 ? `world_bc${-y}.geojson` : `world_${y}.geojson`;
const labelFor = y => (y < 0 ? '前' + (-y) : '公元' + y) + '年';

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

console.log('parsing Cliopatria...');
const t0 = Date.now();
const clio = JSON.parse(fs.readFileSync(CLIO, 'utf8'));
const pol = clio.features.filter(f => f.properties.Type === 'POLITY');
console.log(`parsed in ${Date.now() - t0}ms`);

const idxPath = path.join(ERAS_DIR, 'index.json');
const idx = JSON.parse(fs.readFileSync(idxPath, 'utf8'));

for (const y of YEARS) {
  if (idx.eras.some(e => e.y === y)) { console.log(`${labelFor(y)} 切片已存在，跳过`); continue; }
  const rows = pol.filter(f =>
    f.properties.FromYear <= y && y <= f.properties.ToYear &&
    !f.properties.Components && !f.properties.Name.startsWith('('));
  const feats = [];
  for (const f of rows) {
    const p = f.properties;
    const geom = simplifyGeom(f.geometry);
    if (!geom) continue;
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
  idx.eras.push({ y, f: fileFor(y), l: labelFor(y) });
  console.log(`✓ 生成 ${fileFor(y)}（${labelFor(y)}）: ${feats.length} 个政权`);
  const cn = feats.filter(x => /China|Chinese|Qin|Han|Tang|Song|Sui|Yuan|Ming|Qing|Wei|Shu|Wu|Liang|Chen|Qi|Zhou|Jin|Liao|Xia|Chu|Yan|Zhao|Mongol|Xiongnu|Rouran|Goguryeo|Baekje|Silla|Joseon|Balhae|Nanzhao|Viet|Champa|Funan|Chenla|Khmer|Korea|Tuyuhun|Tibet|Dali|Uyghur/i.test(x.properties.NAME));
  for (const x of cn) console.log('    东亚: ' + x.properties.start_year + '~' + x.properties.end_year + '  ' + x.properties.NAME);
}
idx.eras.sort((a, b) => a.y - b.y);
fs.writeFileSync(idxPath, JSON.stringify(idx), 'utf8');
console.log(`\n✓ index.json 已更新，共 ${idx.eras.length} 个切片`);
