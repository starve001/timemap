// 用 Cliopatria（Seshat Global History Databank, CC BY 4.0）修正 world_1200 切片的中国区域政权。
// 背景：historical-basemaps 的 world_1200 中，金朝只画了东北狭长地带（史实应覆盖整个华北）、
// “Song Empire”实为北宋形状（1200 年应为南宋，北界在淮河—大散关一线）、西夏与吐蕃形状亦失真。
// 本脚本只做“整块替换”：删除失实要素、加入 Cliopatria 的 Type=POLITY 要素，不改写任何坐标。
const fs = require('fs');
const path = require('path');

const YEAR = 1200;
const ROOT = path.join(__dirname, '..');
const TARGET = path.join(ROOT, 'data', 'eras', 'world_1200.geojson');
const CLIO = path.join(__dirname, 'cliopatria', 'cliopatria_polities_only.geojson');
const NAME_ZH = path.join(ROOT, 'data', 'eras', 'name-zh.json');

// 从 Cliopatria 选取的政权（均为 Type=POLITY 且时间范围覆盖 1200 年）
const PICK = ['Great Jin', 'Southern Song', 'Western Xia', 'Tibetans', 'Yenisei Kyrgyz'];
// historical-basemaps 中形状失实、需要整体替换的政权（含 PICK 自身，保证脚本幂等）
const REMOVE = new Set(['Song Empire', 'Liao', 'Xixia', 'Tibet', ...PICK]);
// 蒙古帝国 1206 年才建立，1200 年蒙古高原为诸部并立；仅改名，几何不动。
const RENAME = { 'Mongol Empire': 'Mongols' };
// 运行时无 name-zh.json 映射，中文名直接写入要素的 _nz 字段
const ZH = {
  'Great Jin': '金',
  'Southern Song': '南宋',
  'Western Xia': '西夏',
  'Tibetans': '吐蕃',
  'Yenisei Kyrgyz': '黠戛斯',
  'Mongols': '蒙古诸部'
};
// 补充属性（capital 依据通行史料；无统一都城的填“无”）
const META = {
  'Great Jin': { capital: '中都（今北京）', type: 'dynasty', region: 'china' },
  'Southern Song': { capital: '临安（今杭州）', type: 'dynasty', region: 'china' },
  'Western Xia': { capital: '兴庆府（今银川）', type: 'dynasty', region: 'china' },
  'Tibetans': { capital: '无（分裂时期）', type: 'polity', region: 'tibet' },
  'Yenisei Kyrgyz': { capital: '无固定都城', type: 'polity', region: 'central_asia' }
};
const SOURCE = 'Cliopatria / Seshat Global History Databank (CC BY 4.0)';

function hashName(s) { let h = 0; for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0; return h; }

// 与 prepare-eras.js 一致的轻量简化：坐标取 2 位小数 + 去重复点，不改变轮廓
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

const era = JSON.parse(fs.readFileSync(TARGET, 'utf8'));
const before = era.features.length;
const removed = era.features.filter(f => REMOVE.has(f.properties.NAME)).map(f => f.properties.NAME);
era.features = era.features.filter(f => !REMOVE.has(f.properties.NAME));
let renamed = 0;
for (const f of era.features) {
  if (RENAME[f.properties.NAME]) {
    f.properties.NAME = RENAME[f.properties.NAME];
    f.properties._nz = ZH[f.properties.NAME];
    renamed++;
  }
  // 幂等修正：此前已改名但 _nz 仍是旧值的要素
  if (f.properties.NAME === 'Mongols' && f.properties._nz !== ZH['Mongols']) {
    f.properties._nz = ZH['Mongols'];
  }
}
console.log(`removed: ${removed.join(', ')}; renamed Mongol Empire->Mongols: ${renamed}`);

console.log('parsing Cliopatria (165MB)...');
const t0 = Date.now();
const clio = JSON.parse(fs.readFileSync(CLIO, 'utf8'));
console.log(`parsed in ${Date.now() - t0}ms, ${clio.features.length} records`);

const picked = clio.features.filter(f =>
  PICK.includes(f.properties.Name) &&
  f.properties.Type === 'POLITY' &&
  f.properties.FromYear <= YEAR && YEAR <= f.properties.ToYear);
console.log('picked:', picked.map(f => `${f.properties.Name}(${f.properties.FromYear}~${f.properties.ToYear})`).join(', '));
if (picked.length !== PICK.length) {
  console.error('ERROR: 未能找齐全部目标政权，中止（不写入）');
  process.exit(1);
}

for (const f of picked) {
  const p = f.properties;
  const geom = simplifyGeom(f.geometry);
  if (!geom) { console.error(`ERROR: ${p.Name} 几何简化后为空，中止`); process.exit(1); }
  const meta = META[p.Name] || {};
  era.features.push({
    type: 'Feature',
    properties: {
      NAME: p.Name,
      _nz: ZH[p.Name] || '',
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

fs.writeFileSync(TARGET, JSON.stringify(era));
console.log(`features: ${before} -> ${era.features.length}; file: ${(fs.statSync(TARGET).size / 1024).toFixed(0)}KB`);

// 更新中文名映射
const zh = JSON.parse(fs.readFileSync(NAME_ZH, 'utf8'));
zh['Great Jin'] = '金';
zh['Southern Song'] = '南宋';
zh['Yenisei Kyrgyz'] = '黠戛斯';
zh['Tibetans'] = '吐蕃';
fs.writeFileSync(NAME_ZH, JSON.stringify(zh, null, 1));
console.log('name-zh.json updated: Great Jin/Southern Song/Yenisei Kyrgyz/Tibetans');
