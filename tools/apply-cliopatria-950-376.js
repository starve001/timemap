// 新增两个时代切片（数据源：Cliopatria / Seshat Global History Databank, CC BY 4.0）：
//   world_950  五代十国形势（后汉·辽·后蜀·南唐·楚·南汉·吴越·荆南·大理等）
//   world_376  十六国形势（前秦统一北方，与东晋对峙）
// 做法与 apply-cliopatria-1200.js 一致：以最近的 historical-basemaps 切片为底，
// 整块移除过时/失实的东亚要素，加入 Cliopatria 的 Type=POLITY 要素，不改写任何坐标。
// 每次运行都从底本重建目标文件，天然幂等。
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const ERAS = path.join(ROOT, 'data', 'eras');
const CLIO = path.join(__dirname, 'cliopatria', 'cliopatria_polities_only.geojson');
const NAME_ZH = path.join(ERAS, 'name-zh.json');
const SOURCE = 'Cliopatria / Seshat Global History Databank (CC BY 4.0)';

// 中文名直接写入 name-zh.json，由 tools/add-nz.js 统一注入 _nz 并计算 _a/_c
const ZH_ADD = {
  'Later Han': '后汉', 'Liao Dynasty': '辽', 'Later Shu': '后蜀',
  // 源数据名 Southern Wu，但 947–959 年江南实为南唐（吴亡于 937 年），显示名从史实
  'Southern Wu': '南唐',
  'Southern Chu': '楚', 'Southern Han': '南汉', 'Wuyue': '吴越', 'Jingnan': '荆南',
  'Kingdom of Dali': '大理', 'Ganzhou Kingdom': '甘州回鹘', 'Qocho Kingdom': '高昌回鹘',
  'Kingdom of Khotan': '于阗', 'Heian Japan': '日本', 'Tamna': '耽罗',
  'Kara-Khanids': '喀喇汗国', 'Oghuz Turks': '乌古斯',
  'Kimek-Kipchak confederation': '基马克-钦察联盟',
  'Former Qin': '前秦',
  // 源数据名 Western Jin（Wikipedia: Jin dynasty 266-420），373–382 年阶段实为东晋
  'Western Jin': '东晋',
  'Former Liang': '前凉', 'Protectorate of the Western Regions': '西域长史府',
  'Tuyuhun': '吐谷浑', 'Goguryeo': '高句丽', 'Baekje': '百济', 'Dongye': '东濊',
  'Jinhan': '辰韩', 'Byeonhan': '弁韩', 'Wusun': '乌孙'
};

const SLICES = [
  {
    target: 'world_950.geojson', base: 'world_900.geojson', year: 950,
    // 950 年已不存或形状失实的底本要素（唐 907 亡、南诏 937 为大理所代、渤海 926 亡于辽、
    // 新罗 935 亡于高丽、回鹘已分裂为甘州/高昌等、契丹 947 年已称辽）
    remove: ['Tang Empire', 'Nan Chao', 'Khitans', 'Balhae', 'Silla', 'Ouighurs',
      'Tibetan Empire', 'Yamato', 'Hainan', 'Karluks', 'Oghuz Turks'],
    pick: [
      ['Later Han', { capital: '东京开封府', type: 'dynasty', region: 'china' }],
      ['Liao Dynasty', { capital: '上京临潢府', type: 'dynasty', region: 'china' }],
      ['Later Shu', { capital: '成都', type: 'dynasty', region: 'china' }],
      ['Southern Wu', { capital: '江宁府（金陵）', type: 'dynasty', region: 'china' }],
      ['Southern Chu', { capital: '潭州（长沙）', type: 'dynasty', region: 'china' }],
      ['Southern Han', { capital: '兴王府（广州）', type: 'dynasty', region: 'china' }],
      ['Wuyue', { capital: '杭州', type: 'dynasty', region: 'china' }],
      ['Jingnan', { capital: '江陵', type: 'dynasty', region: 'china' }],
      ['Kingdom of Dali', { capital: '大理', type: 'dynasty', region: 'china' }],
      ['Ganzhou Kingdom', { capital: '甘州（张掖）', type: 'polity', region: 'central_asia' }],
      ['Qocho Kingdom', { capital: '高昌（吐鲁番）', type: 'polity', region: 'central_asia' }],
      ['Kingdom of Khotan', { capital: '于阗', type: 'polity', region: 'central_asia' }],
      ['Tibetans', { capital: '无（分裂时期）', type: 'polity', region: 'tibet' }],
      ['Yenisei Kyrgyz', { capital: '无固定都城', type: 'polity', region: 'central_asia' }],
      ['Heian Japan', { capital: '京都（平安京）', type: 'dynasty', region: 'japan' }],
      ['Goryeo', { capital: '开京', type: 'dynasty', region: 'korea' }],
      ['Tamna', { capital: '无固定城邑', type: 'polity', region: 'korea' }],
      ['Kara-Khanids', { capital: '八剌沙衮', type: 'dynasty', region: 'central_asia' }],
      ['Oghuz Turks', { capital: '无固定都城', type: 'polity', region: 'central_asia' }],
      ['Kimek-Kipchak confederation', { capital: '无固定都城', type: 'polity', region: 'central_asia' }]
    ]
  },
  {
    target: 'world_376.geojson', base: 'world_400.geojson', year: 376,
    // 底本为 400 年形势：晋/十六国为泛称大块需拆分；北凉 397 年才建立，376 年不存在；
    // 高句丽/百济/新罗/加耶换用 Cliopatria 同期几何；海南并入东晋
    remove: ['Jin', 'Sixteen Kingdoms', 'Northern Liang', 'Koguryo', 'Paekche',
      'Silla', 'Gaya', 'Hainan'],
    pick: [
      ['Former Qin', { capital: '长安', type: 'dynasty', region: 'china' }],
      ['Western Jin', { capital: '建康（今南京）', type: 'dynasty', region: 'china' }],
      ['Former Liang', { capital: '姑臧（今武威）', type: 'dynasty', region: 'china' }],
      ['Protectorate of the Western Regions', { capital: '海头', type: 'polity', region: 'central_asia' }],
      ['Tuyuhun', { capital: '无固定都城（游牧）', type: 'polity', region: 'tibet' }],
      ['Goguryeo', { capital: '国内城（今集安）', type: 'dynasty', region: 'korea' }],
      ['Baekje', { capital: '汉城', type: 'dynasty', region: 'korea' }],
      ['Dongye', { capital: '无固定都城', type: 'polity', region: 'korea' }],
      ['Jinhan', { capital: '无固定都城（辰韩诸部）', type: 'polity', region: 'korea' }],
      ['Byeonhan', { capital: '无固定都城（弁韩诸部）', type: 'polity', region: 'korea' }],
      ['Tamna', { capital: '无固定城邑', type: 'polity', region: 'korea' }],
      ['Wusun', { capital: '赤谷城', type: 'polity', region: 'central_asia' }]
    ]
  }
];

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

console.log('parsing Cliopatria (158MB)...');
const t0 = Date.now();
const clio = JSON.parse(fs.readFileSync(CLIO, 'utf8'));
console.log(`parsed in ${Date.now() - t0}ms, ${clio.features.length} records`);

for (const s of SLICES) {
  const base = JSON.parse(fs.readFileSync(path.join(ERAS, s.base), 'utf8'));
  const removeSet = new Set(s.remove);
  const removed = base.features.filter(f => removeSet.has(f.properties.NAME)).map(f => f.properties.NAME);
  const fc = { type: 'FeatureCollection', features: base.features.filter(f => !removeSet.has(f.properties.NAME)) };
  const missingRemove = [...removeSet].filter(n => !removed.includes(n));
  if (missingRemove.length) console.warn(`WARN ${s.target}: 底本中未找到 ${missingRemove.join(', ')}`);

  const picked = [];
  for (const [name, meta] of s.pick) {
    const hits = clio.features.filter(f =>
      f.properties.Name === name && f.properties.Type === 'POLITY' &&
      f.properties.FromYear <= s.year && s.year <= f.properties.ToYear);
    if (hits.length !== 1) {
      console.error(`ERROR ${s.target}: ${name} 命中 ${hits.length} 条（期望 1），中止（不写入）`);
      process.exit(1);
    }
    picked.push([hits[0], meta]);
  }

  for (const [f, meta] of picked) {
    const p = f.properties;
    const geom = simplifyGeom(f.geometry);
    if (!geom) { console.error(`ERROR ${s.target}: ${p.Name} 几何简化后为空，中止`); process.exit(1); }
    fc.features.push({
      type: 'Feature',
      properties: {
        NAME: p.Name,
        _nz: ZH_ADD[p.Name] || '',
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

  const outPath = path.join(ERAS, s.target);
  fs.writeFileSync(outPath, JSON.stringify(fc));
  console.log(`${s.target}: 底本 ${s.base} 移除 [${removed.join(', ')}]，加入 ${picked.length} 个 Cliopatria 政权，共 ${fc.features.length} 个要素，${(fs.statSync(outPath).size / 1024).toFixed(0)}KB`);
}

// 更新中文名映射（add-nz.js 依据它注入 _nz）
const zh = JSON.parse(fs.readFileSync(NAME_ZH, 'utf8'));
for (const [k, v] of Object.entries(ZH_ADD)) zh[k] = v;
fs.writeFileSync(NAME_ZH, JSON.stringify(zh, null, 1));
console.log(`name-zh.json 新增/更新 ${Object.keys(ZH_ADD).length} 条`);
