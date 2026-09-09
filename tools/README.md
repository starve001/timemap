# tools — 数据处理脚本

本项目的数据流水线脚本，均使用 Node.js 运行（`node <script>`，无需安装依赖）。

| 脚本 | 用途 |
|------|------|
| `prepare-eras.js` | 从 Cliopatria 原始数据构建全部版图切片 |
| `rebuild-eras-cliopatria.js` | 重建版图切片（数据源更新后使用） |
| `add-era-slices.js` | 按年份列表补充缺失的切片（如 `node add-era-slices.js 260 570`） |
| `add-nz.js` | 为全部切片注入中文名（读取 `data/eras/name-zh.json` 对照表） |
| `analyze-cliopatria-coverage.js` | 检查政权存续期与切片年份的覆盖缺口 |
| `scan-cliopatria.js` / `inspect-cliopatria.js` / `dump-east.js` | 数据源探查与东亚政权检查 |
| `apply-cliopatria-1200.js` / `apply-cliopatria-950-376.js` | 特定时期切片的数据修正 |
| `check-syntax.js` | 前端脚本语法检查 |

## 原始数据

`cliopatria/` 目录存放 Cliopatria 原始数据的说明（[README.md](./cliopatria/README.md)）。原始 GeoJSON（约 165 MB）因体积原因未入库，从 [Cliopatria 仓库](https://github.com/Seshat-Global-History-Databank/cliopatria) 下载 `cliopatria.geojson.zip` 解压后，重命名为 `cliopatria/cliopatria_polities_only.geojson` 即可运行上述脚本。
