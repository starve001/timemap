// 提取 index.html 中的 <script> 块并用 node --check 校验语法
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const re = /<script([^>]*)>([\s\S]*?)<\/script>/g;
let m, i = 0, failed = false;
const tmpDir = path.join(__dirname, '..', '.tmp-check');
fs.mkdirSync(tmpDir, { recursive: true });

while ((m = re.exec(html)) !== null) {
  const isModule = /type="module"/.test(m[1]);
  const src = m[2].trim();
  if (!src) continue;
  i++;
  const file = path.join(tmpDir, `script-${i}${isModule ? '.mjs' : '.cjs'}`);
  fs.writeFileSync(file, src);
  try {
    execFileSync(process.execPath, ['--check', file], { stdio: 'pipe' });
    console.log(`OK   script #${i} (${isModule ? 'module' : 'classic'}, ${src.length} chars)`);
  } catch (e) {
    failed = true;
    console.log(`FAIL script #${i} (${isModule ? 'module' : 'classic'}):`);
    console.log(e.stderr.toString());
  }
}
fs.rmSync(tmpDir, { recursive: true, force: true });
process.exit(failed ? 1 : 0);
