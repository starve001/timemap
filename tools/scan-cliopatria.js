// 扫描 Cliopatria：列出覆盖指定年份的全部政权（名称/年代/面积/bbox），
// 并单独输出 bbox 与东亚相交的子集，供选取切片数据时决策。
// 用法：node tools/scan-cliopatria.js <year>
const fs = require('fs');
const path = require('path');
const CLIO = path.join(__dirname, 'cliopatria', 'cliopatria_polities_only.geojson');
const YEAR = Number(process.argv[2]);
if (!Number.isFinite(YEAR)) { console.error('用法: node scan-cliopatria.js <year>'); process.exit(1); }

function bbox(g) {
  let minX = 1e9, minY = 1e9, maxX = -1e9, maxY = -1e9;
  const walk = c => {
    if (typeof c[0] === 'number') {
      if (c[0] < minX) minX = c[0]; if (c[0] > maxX) maxX = c[0];
      if (c[1] < minY) minY = c[1]; if (c[1] > maxY) maxY = c[1];
    } else c.forEach(walk);
  };
  walk(g.coordinates);
  return [minX, minY, maxX, maxY];
}

console.log('parsing Cliopatria...');
const t0 = Date.now();
const clio = JSON.parse(fs.readFileSync(CLIO, 'utf8'));
console.log(`parsed in ${Date.now() - t0}ms, ${clio.features.length} records`);

const rows = [];
for (const f of clio.features) {
  const p = f.properties;
  if (p.Type !== 'POLITY') continue;
  if (!(p.FromYear <= YEAR && YEAR <= p.ToYear)) continue;
  const b = bbox(f.geometry).map(v => +v.toFixed(1));
  rows.push({ name: p.Name, from: p.FromYear, to: p.ToYear, area: Math.round(p.Area || 0), bbox: b });
}
rows.sort((a, b) => b.area - a.area);
console.log(`\n=== ${YEAR} 年全部政权（Type=POLITY，共 ${rows.length}）===`);
for (const r of rows) console.log(`${r.name} | ${r.from}~${r.to} | ${r.area} km² | bbox ${r.bbox.join(',')}`);

const ea = rows.filter(r => r.bbox[2] >= 75 && r.bbox[0] <= 150 && r.bbox[3] >= 15 && r.bbox[1] <= 56);
console.log(`\n=== 东亚相关（bbox 与 75-150°E, 15-56°N 相交，共 ${ea.length}）===`);
for (const r of ea) console.log(`${r.name} | ${r.from}~${r.to} | ${r.area} km² | bbox ${r.bbox.join(',')}`);
