// 列出指定切片中 bbox 东缘 >=75°E 的要素（NAME + bbox），用于确定替换/保留清单。
// 用法：node tools/dump-east.js <file>
const fs = require('fs');
const path = require('path');
const p = path.join(__dirname, '..', 'data', 'eras', process.argv[2]);
const fc = JSON.parse(fs.readFileSync(p, 'utf8'));
function bbox(g) {
  let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
  const walk = c => { if (typeof c[0] === 'number') {
    if (c[0] < x0) x0 = c[0]; if (c[0] > x1) x1 = c[0];
    if (c[1] < y0) y0 = c[1]; if (c[1] > y1) y1 = c[1];
  } else c.forEach(walk); };
  walk(g.coordinates);
  return [x0, y0, x1, y1].map(v => +v.toFixed(1));
}
const rows = fc.features
  .map(f => ({ name: f.properties.NAME, nz: f.properties._nz, bbox: bbox(f.geometry) }))
  .filter(r => r.bbox[2] >= 75)
  .sort((a, b) => a.bbox[0] - b.bbox[0]);
for (const r of rows) console.log(`${r.name} (${r.nz}) | ${r.bbox.join(', ')}`);
console.log(`共 ${rows.length} 个`);
