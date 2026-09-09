// 查看指定名称在指定年份命中的 Cliopatria 记录的完整属性（用于核准译名与含义）。
// 用法：node tools/inspect-cliopatria.js <year> <name1> [name2 ...]
const fs = require('fs');
const path = require('path');
const CLIO = path.join(__dirname, 'cliopatria', 'cliopatria_polities_only.geojson');
const YEAR = Number(process.argv[2]);
const NAMES = process.argv.slice(3);
const clio = JSON.parse(fs.readFileSync(CLIO, 'utf8'));
for (const f of clio.features) {
  const p = f.properties;
  if (!NAMES.includes(p.Name)) continue;
  if (!(p.FromYear <= YEAR && YEAR <= p.ToYear)) continue;
  const { geometry, ...rest } = f;
  console.log(JSON.stringify(rest.properties, null, 1));
}
