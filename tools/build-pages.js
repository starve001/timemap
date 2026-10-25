/* ============================================================
 * tools/build-pages.js — 构建 GitHub Pages 静态站点
 * 把后端 REST API 镜像成纯文件目录 site/，前端无需改动即可跑在
 * Pages 上（fetch 都是相对路径，直接对应目录结构）：
 *   api/events            ← events.json
 *   api/cities            ← data/cities.json
 *   api/eras/index.json   ← data/eras/index.json（清单；api/eras 是
 *                            切片目录，文件系统里同名文件与目录不能共存，
 *                            故清单走 /api/eras/index.json，后端同路径兼容）
 *   api/eras/{year}       ← 对应切片（前端只按清单年份请求）
 *   api/ai/config         ← 占位配置（staticDeploy: true，前端据此提示）
 * AI 对话接口在静态部署下不可用，属预期降级。
 * 用法：node tools/build-pages.js（本地与 CI 通用，输出到 site/）
 * ============================================================ */
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const SITE = path.join(ROOT, 'site');
const API = path.join(SITE, 'api');

fs.rmSync(SITE, { recursive: true, force: true });
fs.mkdirSync(path.join(API, 'eras'), { recursive: true });
fs.mkdirSync(path.join(API, 'ai'), { recursive: true });

// 页面：舆图本体放 app/（门户 iframe 与直连均可达），
// 根路径 index.html 是智能跳板 —— GitHub 上只有一个门面（门户），
// 旧的 #y=<年>&map=<z>/<经>/<纬> 深链自动转换为门户全屏舆图深链
fs.mkdirSync(path.join(SITE, 'app'), { recursive: true });
fs.copyFileSync(
  path.join(ROOT, 'server/src/main/resources/static/index.html'),
  path.join(SITE, 'app', 'index.html'));
fs.writeFileSync(path.join(SITE, 'index.html'), `<!DOCTYPE html>
<meta charset="UTF-8">
<title>MAPDEX · 时序地图</title>
<script>
(function () {
  var h = location.hash.replace(/^#/, '');
  var m = h.match(/y=(-?\\d+)&map=([\\d.]+)\\/(-?[\\d.]+)\\/(-?[\\d.]+)/);
  var to = 'portal/';
  if (m) to = 'portal/#/atlas?y=' + m[1] + '&lng=' + m[3] + '&lat=' + m[4] + '&z=' + m[2];
  location.replace(to);
})();
</script>
`);

// REST API → 静态文件
fs.copyFileSync(path.join(ROOT, 'events.json'), path.join(API, 'events'));
// 根路径数据副本：外部门户跨站 fetch 时取 /timemap/events.json 更直观
fs.copyFileSync(path.join(ROOT, 'events.json'), path.join(SITE, 'events.json'));

// 策展门户（影院大堂）：portal/ → site/portal/，与舆图同源
fs.cpSync(path.join(ROOT, 'portal'), path.join(SITE, 'portal'), { recursive: true });
fs.copyFileSync(path.join(ROOT, 'data/cities.json'), path.join(API, 'cities'));
fs.copyFileSync(
  path.join(ROOT, 'data/eras/index.json'),
  path.join(API, 'eras', 'index.json'));

const manifest = JSON.parse(fs.readFileSync(path.join(ROOT, 'data/eras/index.json'), 'utf8'));
let sliceBytes = 0;
for (const e of manifest.eras) {
  const dst = path.join(API, 'eras', String(e.y));
  fs.copyFileSync(path.join(ROOT, 'data/eras', e.f), dst);
  sliceBytes += fs.statSync(dst).size;
}

// AI 配置占位：前端识别 staticDeploy 后提示「AI 助手需本地运行」
fs.writeFileSync(path.join(API, 'ai', 'config'), JSON.stringify({
  configured: false,
  hasKey: false,
  keyMasked: '',
  model: 'glm-4-flash',
  baseUrl: 'https://open.bigmodel.cn/api/paas/v4',
  temperature: 0.3,
  staticDeploy: true,
}));

// 关闭 Jekyll 处理：Pages 不再做任何文件加工
fs.writeFileSync(path.join(SITE, '.nojekyll'), '');

const siteBytes = (function dirSize(dir) {
  let n = 0;
  for (const f of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, f.name);
    n += f.isDirectory() ? dirSize(p) : fs.statSync(p).size;
  }
  return n;
})(SITE);

console.log(`✓ site/ 构建完成：${manifest.eras.length} 个切片（${(sliceBytes / 1e6).toFixed(2)} MB），站点合计 ${(siteBytes / 1e6).toFixed(2)} MB`);
