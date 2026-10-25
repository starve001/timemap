// 合并 events-additions.json 进 events.json：排重（同 ±3 年且名称有重叠）、
// 校验字段合法性、按 (year, name) 排序写回。可重复运行（幂等）。
// 用法：node tools/enrich-events.js [--dry]
const fs = require('fs');
const path = require('path');
const ROOT = path.join(__dirname, '..');
const EVENTS = path.join(ROOT, 'events.json');
const ADD = path.join(__dirname, 'events-additions.json');

const CATS = ['politics', 'military', 'culture', 'economy', 'tech'];
const dry = process.argv.includes('--dry');
const events = JSON.parse(fs.readFileSync(EVENTS, 'utf8'));
const adds = JSON.parse(fs.readFileSync(ADD, 'utf8'));

const overlap = (a, b) => {
  const A = [...a], B = [...b];
  return A.filter(x => B.includes(x)).length >= 2 || a === b;
};
const nameKey = n => n.replace(/[（(].*?[)）]/g, '').replace(/[·《》「」]/g, '').slice(0, 4);

const out = [];
let dup = 0, bad = 0;
for (const a of adds) {
  const errs = [];
  if (!Number.isInteger(a.year) || a.year < -221 || a.year > 1918) errs.push('year');
  if (!CATS.includes(a.cat)) errs.push('cat');
  if (![1, 2, 3].includes(a.importance)) errs.push('importance');
  if (typeof a.name !== 'string' || !a.desc || typeof a.lng !== 'number' || typeof a.lat !== 'number') errs.push('fields');
  if (errs.length) { bad++; console.error('× 字段不合规:', a.name || a.year, errs.join(',')); continue; }
  const clash = events.some(e => Math.abs(e.year - a.year) <= 3 && overlap(nameKey(e.name), nameKey(a.name)));
  if (clash) { dup++; console.error('× 与现有事件近重，跳过:', a.year, a.name); continue; }
  out.push(a);
}

const before = events.length;
const merged = events.concat(out).sort((x, y) => x.year - y.year || x.name.localeCompare(y.name, 'zh'));
if (!dry) fs.writeFileSync(EVENTS, JSON.stringify(merged, null, 1) + '\n', 'utf8');

const cats = {};
merged.forEach(e => cats[e.cat] = (cats[e.cat] || 0) + 1);
console.log(`\n${dry ? '[试运行] ' : ''}现有 ${before} 条 + 新增 ${out.length} 条（排重 ${dup}、不合规 ${bad}）→ 合计 ${merged.length} 条`);
console.log('类别分布:', JSON.stringify(cats));
