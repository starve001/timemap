/* ============================================================
 * tools/add-nz.js — 给 data/eras/*.geojson 注入中文译名
 * properties._nz = zh(NAME)，properties._sz = zh(SUBJECTO)
 * 未收录者置空字符串（前端回退英文）。就地修改，可重复执行。
 * 用法：node tools/add-nz.js
 * ============================================================ */
const fs = require('fs');
const path = require('path');

const DIR = path.join(__dirname, '..', 'data', 'eras');
const zh = JSON.parse(fs.readFileSync(path.join(DIR, 'name-zh.json'), 'utf8'));

/* 数据源勘误（按文件覆盖 name-zh 映射）：
 * Cliopatria 用 "Western Jin" 指整个晋朝（266–420），316 年前为西晋、之后为东晋 */
const CORRECTIONS = {
  'world_376.geojson': { 'Western Jin': '东晋' },
  'world_400.geojson': { 'Western Jin': '东晋' },
}

let total = 0, translated = 0;
const missing = new Map();

for (const f of fs.readdirSync(DIR)) {
  if (!f.endsWith('.geojson')) continue;
  const p = path.join(DIR, f);
  const fc = JSON.parse(fs.readFileSync(p, 'utf8'));
  for (const feat of fc.features) {
    const pr = feat.properties || (feat.properties = {});
    total++;
    const corr = CORRECTIONS[f] || {};
    const nz = corr[pr.NAME] || zh[pr.NAME] || '';
    const sz = zh[pr.SUBJECTO] || '';
    // 外接矩形面积（度²）与重心点：供前端筛选/标注大政权
    let x0 = 180, x1 = -180, y0 = 90, y1 = -90;
    (function walk(c2) {
      if (typeof c2[0] === 'number') {
        if (c2[0] < x0) x0 = c2[0]; if (c2[0] > x1) x1 = c2[0];
        if (c2[1] < y0) y0 = c2[1]; if (c2[1] > y1) y1 = c2[1];
      } else for (const w of c2) walk(w);
    })(feat.geometry.coordinates);
    pr._a = Math.round((x1 - x0) * (y1 - y0));
    pr._c = [Math.round((x0 + x1) / 2 * 100) / 100, Math.round((y0 + y1) / 2 * 100) / 100];
    if (nz) translated++;
    else if (pr.NAME) missing.set(pr.NAME, (missing.get(pr.NAME) || 0) + 1);
    pr._nz = nz;
    pr._sz = sz;
  }
  fs.writeFileSync(p, JSON.stringify(fc));
}

const top = [...missing.entries()].sort((a, b) => b[1] - a[1]).slice(0, 25);
console.log(`特征总数 ${total}，已译 ${translated}（${(translated / total * 100).toFixed(1)}%）`);
console.log('未译高频 Top25:');
for (const [n, c] of top) console.log(`  #${c} ${n}`);
