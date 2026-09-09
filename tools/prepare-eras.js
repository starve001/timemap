/* ============================================================
 * tools/prepare-eras.js — 下载 aourednik/historical-basemaps 的
 * 分时代政权版图 GeoJSON，简化（去冗余字段/坐标降精度/去重复点）
 * 后输出到 data/eras/，并生成 index.json 清单
 * 数据源：https://github.com/aourednik/historical-basemaps (GPL-3.0)
 * 用法：node tools/prepare-eras.js
 * ============================================================ */
const fs = require('fs');
const path = require('path');
const https = require('https');

const DIR = path.join(__dirname, '..');
const OUT = path.join(DIR, 'data', 'eras');
fs.mkdirSync(OUT, { recursive: true });

/* 覆盖 mapdex 时间轴（-3000 ~ 2000）的年代序列 */
const ERAS = [-3000, -2000, -1500, -1000, -700, -500, -400, -323, -300, -200, -100, -1,
  100, 200, 300, 376, 400, 500, 600, 700, 800, 900, 950, 1000, 1100, 1200, 1279, 1300, 1400, 1492,
  1500, 1530, 1600, 1650, 1700, 1715, 1783, 1800, 1815, 1880, 1900, 1914, 1920, 1930,
  1938, 1945, 1960, 1994, 2000];

const fileFor = y => y < 0 ? `world_bc${-y}.geojson` : `world_${y}.geojson`;
const labelFor = y => y < 0 ? `前${-y}年` : `${y}年`;

/* 本地克隆目录（优先）：ERAS_LOCAL=/path/to/hb-clone/geojson node tools/prepare-eras.js */
const LOCAL_DIR = process.env.ERAS_LOCAL || '';

function fetchBuf(url, redirects = 0) {
  return new Promise((resolve, reject) => {
    if (redirects > 4) return reject(new Error('too many redirects'));
    https.get(url, { headers: { 'User-Agent': 'mapdex-prepare/1.0' } }, res => {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        res.resume();
        return resolve(fetchBuf(res.headers.location, redirects + 1));
      }
      if (res.statusCode !== 200) {
        res.resume();
        return reject(new Error(`HTTP ${res.statusCode} for ${url}`));
      }
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => resolve(Buffer.concat(chunks)));
      res.on('error', reject);
    }).on('error', reject);
  });
}

async function fetchWithRetry(url, tries = 4) {
  let lastErr;
  for (let i = 0; i < tries; i++) {
    try { return await fetchBuf(url); }
    catch (e) { lastErr = e; await new Promise(r => setTimeout(r, 1500 * (i + 1))); }
  }
  throw lastErr;
}

/* 字符串 → 稳定哈希（用于版图配色） */
function hash(s) {
  let h = 5381;
  for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) >>> 0;
  return h;
}

const R = Math.round;
const r2 = v => R(v * 100) / 100;

/* 坐标降精度 + 去连续重复点 + 丢弃过小的环 */
function roundCoords(c) {
  if (typeof c === 'number') return r2(c);
  if (Array.isArray(c) && typeof c[0] === 'number') {
    const out = [r2(c[0]), r2(c[1])];
    return out;
  }
  return c.map(roundCoords);
}

function dedupeRing(ring) {
  const out = [];
  for (const pt of ring) {
    if (!out.length || out[out.length - 1][0] !== pt[0] || out[out.length - 1][1] !== pt[1]) {
      out.push(pt);
    }
  }
  if (out.length >= 2 && out[0][0] === out[out.length - 1][0] && out[0][1] === out[out.length - 1][1] && out.length < 5) return [];
  return out.length >= 4 ? out : [];
}

function simplifyGeom(g) {
  const c = roundCoords(g.coordinates);
  // Polygon: coordinates = [环...]，环在深度 0；MultiPolygon: 环在深度 1
  const ringDepth = g.type === 'Polygon' ? 0 : 1;
  const walk = (node, depth) => {
    if (depth === ringDepth) {
      return node.map(dedupeRing).filter(r => r.length);
    }
    return node.map(n => walk(n, depth + 1));
  };
  const coordinates = walk(c, 0);
  // 剔除空环/空多边形（空 poly 会让 geojson-vt 崩溃）
  let cleaned = coordinates;
  if (g.type === 'Polygon') {
    cleaned = coordinates.filter(r => r.length);
  } else if (g.type === 'MultiPolygon') {
    cleaned = coordinates.map(poly => poly.filter(r => r.length)).filter(poly => poly.length);
  }
  const empty = cleaned.length === 0;
  return empty ? null : { type: g.type, coordinates: cleaned };
}

async function main() {
  const manifest = [];
  let totalBytes = 0;
  for (const y of ERAS) {
    const f = fileFor(y);
    const outPath = path.join(OUT, f);
    if (!fs.existsSync(outPath)) {
      let buf;
      const localPath = LOCAL_DIR ? path.join(LOCAL_DIR, f) : '';
      if (localPath && fs.existsSync(localPath)) {
        console.log(`读取本地 ${f} ... `);
        buf = fs.readFileSync(localPath);
      } else {
        const url = `https://raw.githubusercontent.com/aourednik/historical-basemaps/master/geojson/${f}`;
        process.stdout.write(`下载 ${f} ... `);
        buf = await fetchWithRetry(url);
      }
      const fc = JSON.parse(buf.toString('utf8'));
      const feats = [];
      for (const feat of fc.features || []) {
        if (!feat.geometry) continue;
        const g = simplifyGeom(feat.geometry);
        if (!g) continue;
        const p = feat.properties || {};
        const key = String(p.SUBJECTO || p.NAME || '');
        feats.push({
          type: 'Feature',
          geometry: g,
          properties: {
            NAME: String(p.NAME || ''),
            SUBJECTO: String(p.SUBJECTO || ''),
            PARTOF: String(p.PARTOF || ''),
            BP: p.BORDERPRECISION == null ? null : +p.BORDERPRECISION,
            T: String(p.type || ''),
            C: hash(key) % 12, // 12 色分类色板索引（构建期算好）
          },
        });
      }
      const out = JSON.stringify({ type: 'FeatureCollection', features: feats });
      fs.writeFileSync(outPath, out);
      console.log(`${(buf.length / 1024).toFixed(0)}KB → ${(out.length / 1024).toFixed(0)}KB, ${feats.length} 个政权`);
    } else {
      console.log(`已存在 ${f}，跳过下载`);
    }
    const size = fs.statSync(outPath).size;
    totalBytes += size;
    manifest.push({ y, f, l: labelFor(y) });
  }
  const index = {
    credit: '历史政权边界数据 © André Ourednik 与贡献者 (github.com/aourednik/historical-basemaps)，GPL-3.0 许可；源自 Thomas Lessman 等历史地图的数字化',
    eras: manifest,
  };
  fs.writeFileSync(path.join(OUT, 'index.json'), JSON.stringify(index));
  console.log(`\n✓ ${manifest.length} 个年代清单写入 index.json，共 ${(totalBytes / 1024 / 1024).toFixed(1)} MB`);
}

main().catch(e => { console.error('失败:', e.message); process.exit(1); });
