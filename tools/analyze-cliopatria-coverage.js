// 分析 Cliopatria 对项目 49 个切片年份的覆盖：
// 每年命中的记录数、去重后的政权数、同名多条记录（需去重策略）、伞/别名记录数。
const fs = require('fs');
const path = require('path');
const CLIO = path.join(__dirname, 'cliopatria', 'cliopatria_polities_only.geojson');
const ERAS = [-3000, -2000, -1500, -1000, -700, -500, -400, -323, -300, -200, -100, -1,
  100, 200, 300, 376, 400, 500, 600, 700, 800, 900, 950, 1000, 1100, 1200, 1279, 1300, 1400, 1492,
  1500, 1530, 1600, 1650, 1700, 1715, 1783, 1800, 1815, 1880, 1900, 1914, 1920, 1930,
  1938, 1945, 1960, 1994, 2000];

const clio = JSON.parse(fs.readFileSync(CLIO, 'utf8'));
const pol = clio.features.filter(f => f.properties.Type === 'POLITY');
console.log(`总记录 ${clio.features.length}，其中 Type=POLITY ${pol.length}`);
const withComp = pol.filter(f => f.properties.Components);
console.log(`含 Components 的伞记录 ${withComp.length}：${[...new Set(withComp.map(f => f.properties.Name))].join(' | ')}`);
const paren = pol.filter(f => f.properties.Name.startsWith('('));
console.log(`括号别名记录（去重前样本）：${[...new Set(paren.map(f => f.properties.Name))].slice(0, 15).join(' | ')}`);

for (const y of ERAS) {
  const rows = pol.filter(f => f.properties.FromYear <= y && y <= f.properties.ToYear);
  const usable = rows.filter(f => !f.properties.Components && !f.properties.Name.startsWith('('));
  const byName = new Map();
  for (const f of usable) {
    const n = f.properties.Name;
    byName.set(n, (byName.get(n) || 0) + 1);
  }
  const dups = [...byName].filter(([, c]) => c > 1);
  console.log(`${String(y).padStart(5)} 年: 记录 ${String(rows.length).padStart(3)} | 可用 ${String(usable.length).padStart(3)} | 政权 ${String(byName.size).padStart(3)}${dups.length ? ' | 同名多条: ' + dups.map(([n, c]) => `${n}x${c}`).join(', ') : ''}`);
}
