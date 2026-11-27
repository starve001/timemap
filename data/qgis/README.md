# MAPDEX QGIS 辅助参考图层

本目录存放面向桌面 GIS（QGIS）的辅助编辑资源，不打包进 GitHub Pages 静态站点（网页端由前端按视口动态渲染经纬网，零额外体积）。

## 包含文件

- `graticules.geojson` — 全球 `WGS 84 (EPSG:4326)` 分级经纬网（经度 `-180° ~ 180°`，纬度 `-80° ~ 80°`），每条线每隔 `1°` 置顶点（所有整数经纬交点均可直接用 QGIS 顶点捕捉，配合 Georeferencer 做「从画布取点」GCP 配准零误差），按 `step` 字段分为三档：
  - `15`：主经纬线（含赤道 `0°`、本初子午线 `0°`、180° 经线），全比例尺可见
  - `5`：区域经纬线，放大至 `1:45,000,000` 以内自动显示（适合东亚/中亚/丝路全览）
  - `1`：精细经纬线，放大至 `1:12,000,000` 以内自动显示（适合河西走廊/西域绿洲/关中精修）
- `graticules.qml` — 与 GeoJSON 同名的 QGIS 样式文件。**直接把 `graticules.geojson` 拖进 QGIS 画布，样式、比例尺分级显隐和度数标注会自动生效**。

## 属性字段

| 字段 | 说明 | 示例 |
|---|---|---|
| `axis` | 轴向：`lon` 经线 / `lat` 纬线 | `lon` |
| `deg` | 整数度数（西经、南纬为负） | `105` |
| `step` | 分级档位：`15` / `5` / `1` | `15` |
| `special` | 特殊线标记：`equator` / `prime` / `antimeridian` / 空 | `equator` |
| `label` | 紧凑度数标注（默认显示） | `105°E`、`35°N`、`0°` |
| `label_zh` | 中文标注（可在 QGIS 标注设置中随时切换） | `东经105°`、`北纬35°` |

## 在 QGIS 中配合 MAPDEX 数据使用

1. 打开 QGIS，建议先将项目坐标系设为 `EPSG:4326`（编辑原始经纬度）或 `EPSG:3857`（与网页 MapLibre 视角一致）。
2. 将以下仓库文件直接拖入图层面板，并把 `graticules` 置顶：
   - `data/qgis/graticules.geojson`（置顶参考网格，可按需开启捕捉）
   - `data/cities.json` / `data/geography.json` / `data/eras/world_*.geojson`
   - `data/basemap/natural-earth.geojson`（底图陆地/海岸/水系）
3. 如需在画布四周边框显示实时刻度，也可同时开启 QGIS 原生菜单：**视图 → 装饰 → 网格（View → Decorations → Grid）**。

## 重新生成

```bash
python tools/build-graticules.py
```
