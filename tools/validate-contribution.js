/* ============================================================
 * tools/validate-contribution.js — 社区贡献 GeoJSON 的入库门禁
 * 志愿者交回 contributions/<handle>/*.geojson，这里决定能不能合。
 * 页面里的校勘卡只是即时提示，放行判断以本脚本为准：改规则只动这里，
 * 不用重新发一版前端。
 *
 * 用法：
 *   node tools/validate-contribution.js contributions/alice/wall_x.geojson   单个文件
 *   node tools/validate-contribution.js contributions                          整个目录
 *   有错误时退出码 1（CI 据此拦住 PR）
 *
 * 规则出处与字段说明见 CONTRIBUTING.md。
 * ============================================================ */
const fs = require('fs');
const path = require('path');

// 与前端 index.html 的 MIN_YEAR / MAX_YEAR 保持一致（秦统一 ~ 一战结束）
const MIN_YEAR = -221;
const MAX_YEAR = 1918;
const KINDS = ['wall', 'pass', 'polity', 'route', 'site', 'misc'];
const LICENSES = ['CC0 1.0', 'CC BY 4.0'];
const GEOM_TYPES = ['Point', 'LineString', 'Polygon'];
const MAX_BYTES = 512 * 1024;
const VERTS_PER_FEATURE = 1200;
const VERTS_PER_FILE = 20000;
const SOFT_VERTS = 300;
const HANDLE_RE = /^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$/;
const DATE_RE = /^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$/;

/* ---------------- 几何小工具 ---------------- */
function coordList(g) {
  // 取要素的全部顶点（面含所有环）
  if (g.type === 'Point') return [g.coordinates];
  if (g.type === 'LineString') return g.coordinates;
  if (g.type === 'Polygon') return g.coordinates.reduce((a, r) => a.concat(r), []);
  return [];
}
function isCoordPair(c) {
  return Array.isArray(c) && c.length >= 2 && c.every(v => typeof v === 'number' && isFinite(v));
}
function orient(a, b, c) { return (c[1] - a[1]) * (b[0] - a[0]) - (b[1] - a[1]) * (c[0] - a[0]); }
function segSeg(p1, p2, p3, p4) {
  const d1 = orient(p3, p4, p1), d2 = orient(p3, p4, p2), d3 = orient(p1, p2, p3), d4 = orient(p1, p2, p4);
  return ((d1 > 0) !== (d2 > 0)) && ((d3 > 0) !== (d4 > 0));
}
/* 返回 true=自交，null=顶点太多未检 */
function ringSelfIntersects(ring) {
  const n = ring.length - 1; // 末点与首点重合
  if (n < 4) return false;
  if (n > 120) return null;
  for (let i = 0; i < n; i++) {
    for (let j = i + 2; j < n; j++) {
      if (i === 0 && j === n - 1) continue;
      if (segSeg(ring[i], ring[(i + 1) % n], ring[j], ring[(j + 1) % n])) return true;
    }
  }
  return false;
}

/* ---------------- 单文件校验 ---------------- */
function validateFile(absPath) {
  const err = [], warn = [];
  const rel = absPath.replace(/\\/g, '/');

  // 1. 落点：必须在 contributions/<handle>/ 下
  const m = rel.match(/(?:^|\/)contributions\/([^/]+)\/([^/]+)$/);
  if (!m) {
    err.push('文件必须放在 contributions/<GitHub用户名>/ 下，当前路径是 ' + rel);
    return { err, warn };
  }
  const dirHandle = m[1];
  if (!HANDLE_RE.test(dirHandle)) err.push('目录名「' + dirHandle + '」不是合法的 GitHub 用户名。');
  if (!/\.geojson$/.test(m[2])) warn.push('建议用 .geojson 后缀（现在是 ' + m[2].split('.').pop() + '），便于别人一眼认出是什么。');

  // 2. 体积
  let raw;
  try { raw = fs.readFileSync(absPath, 'utf8'); } catch (e) {
    err.push('读不到文件：' + e.message);
    return { err, warn };
  }
  if (Buffer.byteLength(raw, 'utf8') > MAX_BYTES) {
    err.push('文件 ' + Math.round(Buffer.byteLength(raw, 'utf8') / 1024) + ' KB，超过 ' +
      (MAX_BYTES / 1024) + ' KB 上限。一次交一段，别把整条墙线塞进一个文件。');
    return { err, warn };
  }

  // 3. 结构
  let data;
  try { data = JSON.parse(raw); } catch (e) { err.push('不是合法 JSON：' + e.message); return { err, warn }; }
  if (data.type !== 'FeatureCollection') err.push('顶层 type 要是 FeatureCollection，现在是 ' + String(data.type));
  if (!Array.isArray(data.features)) { err.push('缺少 features 数组。'); return { err, warn }; }
  if (!data.features.length) err.push('features 是空的。空文件不用交。');

  let fileVerts = 0;
  const seen = new Set();

  data.features.forEach((f, i) => {
    const tag = '第 ' + (i + 1) + ' 条';
    const p = (f && f.properties) || {};
    const g = f && f.geometry;

    if (!f || f.type !== 'Feature') { err.push(tag + '：type 要是 Feature。'); return; }

    // 内部字段不许外流（编辑器草稿态的 _id / _open / _sel）
    const leaked = Object.keys(p).filter(k => k[0] === '_');
    if (leaked.length) err.push(tag + '：带了编辑器的内部字段 ' + leaked.map(k => '"' + k + '"').join('、') +
      '，导出前应去掉。用勘绘台的「导出」按钮生成，别手工拼。');

    // 几何
    if (!g || !GEOM_TYPES.includes(g.type)) {
      err.push(tag + '：几何类型只收 Point / LineString / Polygon，现在是 ' + String(g && g.type) +
        '。多面（MultiPolygon）请先拆成多条要素。');
      return;
    }
    const verts = coordList(g);
    if (!verts.length || !verts.every(isCoordPair)) {
      err.push(tag + '：coordinates 结构不对，每个顶点得是 [经度, 纬度] 两个有限数字。');
      return;
    }
    const oob = verts.find(c => Math.abs(c[0]) > 180 || Math.abs(c[1]) > 90);
    if (oob) err.push(tag + '：顶点 [' + oob.join(', ') + '] 超出经纬度范围（-180~180 / -90~90）。');

    fileVerts += verts.length;
    if (verts.length > VERTS_PER_FEATURE) {
      err.push(tag + '：' + verts.length + ' 个顶点，超过单要素 ' + VERTS_PER_FEATURE + ' 的上限。放大后分段描。');
    } else if (verts.length > SOFT_VERTS) {
      warn.push(tag + '：' + verts.length + ' 个顶点偏多，' + SOFT_VERTS + ' 以内渲染和校勘都轻快。');
    }

    if (g.type === 'LineString' && verts.length < 2) err.push(tag + '：线不足两个顶点。');
    if (g.type === 'Polygon') {
      g.coordinates.forEach((ring, ri) => {
        const ringName = (ri === 0 ? '外环' : '第 ' + ri + ' 个内环');
        if (ring.length < 4) { err.push(tag + '：' + ringName + '只有 ' + ring.length + ' 点，闭不成环（至少 3 个顶点 + 回到起点）。'); return; }
        const a = ring[0], b = ring[ring.length - 1];
        if (a[0] !== b[0] || a[1] !== b[1]) err.push(tag + '：' + ringName + '首尾不重合，不是闭合环。');
        const hit = ringSelfIntersects(ring);
        if (hit === true) err.push(tag + '：' + ringName + '自相交，轮廓会打结。挪开交叉处再交。');
        else if (hit === null) warn.push(tag + '：' + ringName + '顶点较多，未做自交检查。');
      });
    }

    // 元数据
    const name = String(p.name || '').trim();
    if (!name) err.push(tag + '：缺 name。');
    else if (name.length > 60) err.push(tag + '：name 有 ' + name.length + ' 字，控制在 60 字内。');

    if (!KINDS.includes(p.kind)) err.push(tag + '：kind 要取 ' + KINDS.join(' / ') + ' 之一，现在是 "' + String(p.kind) + '"。');

    if (!Number.isInteger(p.start_year) || !Number.isInteger(p.end_year)) {
      err.push(tag + '：start_year / end_year 要整数（公元前用负数，如 -221），现在是 ' +
        JSON.stringify([p.start_year, p.end_year]) + '。');
    } else {
      if (p.end_year < p.start_year) err.push(tag + '：end_year(' + p.end_year + ') 早于 start_year(' + p.start_year + ')。');
      if (p.end_year < MIN_YEAR || p.start_year > MAX_YEAR) {
        err.push(tag + '：存续区间 [' + p.start_year + ', ' + p.end_year + '] 与本图时间轴 [' +
          MIN_YEAR + ', ' + MAX_YEAR + '] 无交集，画进任何年代都是空白。');
      }
    }

    const src = String(p.source || '').trim();
    if (src.length < 6) err.push(tag + '：source 要写清依据（图册页码 / 实测记录 / 文献条目），现在只有 "' + src + '"。');

    if (!p.contributor) err.push(tag + '：缺 contributor。');
    else if (String(p.contributor) !== dirHandle) {
      err.push(tag + '：contributor 是 "' + p.contributor + '"，但文件在 contributions/' + dirHandle + '/ 下，两边要对上。');
    }

    if (!LICENSES.includes(p.license)) err.push(tag + '：license 要写明 ' + LICENSES.join(' 或 ') + ' 之一。');
    if (!DATE_RE.test(String(p.traced_on || ''))) err.push(tag + '：traced_on 要 YYYY-MM-DD 格式，现在是 "' + String(p.traced_on) + '"。');

    // 疑似重复
    const key = name + '|' + g.type + '|' + JSON.stringify(verts);
    if (seen.has(key)) warn.push(tag + '：与前面某条的名称和几何完全一样，可能是误留。');
    seen.add(key);
  });

  if (fileVerts > VERTS_PER_FILE) err.push('整份文件 ' + fileVerts + ' 个顶点，超过 ' + VERTS_PER_FILE + ' 的上限。拆成多个文件交。');
  return { err, warn };
}

/* ---------------- 收集待检文件 ---------------- */
function collect(target) {
  const st = fs.statSync(target);
  if (st.isFile()) return [target];
  const out = [];
  const walk = dir => fs.readdirSync(dir, { withFileTypes: true }).forEach(e => {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p);
    else if (/\.(geojson|json)$/i.test(e.name) && /contributions/.test(p.replace(/\\/g, '/'))) out.push(p);
  });
  walk(target);
  return out;
}

function main() {
  const args = process.argv.slice(2);
  if (!args.length) {
    console.error('用法：node tools/validate-contribution.js <文件或目录>...');
    process.exit(2);
  }
  let files = [];
  for (const a of args) {
    if (!fs.existsSync(a)) { console.error('路径不存在：' + a); process.exit(2); }
    files = files.concat(collect(a));
  }
  if (!files.length) {
    console.log('没有 contributions/ 下的 GeoJSON 要检。');
    return;
  }

  let bad = 0, soft = 0;
  files.forEach(f => {
    const { err, warn } = validateFile(f);
    const rel = path.relative(process.cwd(), f).replace(/\\/g, '/');
    if (!err.length && !warn.length) { console.log('✓ ' + rel + '  通过'); return; }
    console.log((err.length ? '✗ ' : '! ') + rel);
    err.forEach(e => console.log('    错误  ' + e));
    warn.forEach(w => console.log('    提醒  ' + w));
    if (err.length) bad++;
    soft += warn.length;
  });

  console.log('\n共 ' + files.length + ' 份，' + bad + ' 份不合格，提醒 ' + soft + ' 条。');
  if (bad) {
    console.log('不合格的文件改完再重新提交；规则见 CONTRIBUTING.md。');
    process.exit(1);
  }
}

if (require.main === module) main();
module.exports = { validateFile };
