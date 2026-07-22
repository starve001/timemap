# 中国时序地图 · ChronoMap CN

> 以时间轴 + 交互地图探索中国五千年历史疆域变迁

在线浏览从夏商周到清末共 19 个朝代/时期的历史地图，底图叠加谭其骧《中国历史地图集》数字化栅格瓦片，支持朝代切换、城市标记、历史事件浏览。事件稀少，更为关键是很多地图缺失相应的geojson文件等相应数据；原来想做一个时序世界地图，但开源的geojson更是少之又少，为数不多的几个历史地图错误严重。希望看到的高手能拯救一下

![技术栈](https://img.shields.io/badge/Next.js-16-black) ![技术栈](https://img.shields.io/badge/MapLibre_GL-4-green) ![技术栈](https://img.shields.io/badge/TypeScript-5-blue) ![License](https://img.shields.io/badge/License-MIT-grey)

---

## 截图预览

启动后可看到：顶部导航栏 + 全屏历史地图 + 右侧信息面板 + 底部朝代时间轴。

---

## 快速开始

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 浏览器打开 http://localhost:3000
```

环境要求：Node.js 18+、npm 9+

---

## 功能特性

- **19 个朝代/时期**：夏 → 商 → 西周 → 春秋 → 战国 → 秦 → 西汉 → 东汉 → 三国 → 西晋 → 东晋 → 南北朝 → 隋 → 唐 → 五代十国 → 北宋 → 南宋 → 元 → 明 → 清
- **历史栅格瓦片**：叠加中研院 WMTS 服务提供的谭其骧历史地图
- **现代底图**：OpenFreeMap Bright 矢量瓦片，包含道路/河流/地形
- **朝代时间轴**：底部可拖拽的时间轴，点击切换朝代
- **信息面板**：右侧显示朝代简介、重大事件、统计数据
- **城市标记**：历代都城与重要城市在地图上标注
- **键盘导航**：支持方向键切换朝代
- **对比模式**：左右分屏对比不同时期疆域
- **明暗主题**：支持亮/暗主题切换

---

## 数据来源与致谢

本项目使用的历史地理数据均来自公开学术资源，在此向以下机构和学者致谢：

### 1. 历史地图栅格瓦片

| 项目 | 说明 |
|------|------|
| **谭其骧《中国历史地图集》** | 中国历史地图权威著作，本项目使用的数字化栅格瓦片基于此 |
| **中央研究院 GIS 专题中心（中研院 WMTS）** | 提供谭其骧地图集的在线 WMTS 瓦片服务 |
| 服务地址 | https://gis.sinica.edu.tw/ccts/wmts |
| 使用方式 | GoogleMapsCompatible TileMatrixSet（XYZ 方案） |
| 许可 | 学术研究/教育用途，非商业 |

### 2. 现代底图

| 项目 | 说明 |
|------|------|
| **OpenFreeMap** | 免费矢量瓦片服务，无需 API Key |
| 服务地址 | https://tiles.openfreemap.org/styles/bright |
| 数据基础 | OpenStreetMap |
| 许可 | Open Database License (ODbL) |

### 3. 朝代与事件数据

| 数据 | 来源 | 说明 |
|------|------|------|
| 朝代信息 | 公开历史资料整理 | 朝代名称、起止年份、都城、简介 |
| 历史事件 | 公开历史资料整理 | 各朝代重大事件（战争/政治/文化/经济/科技） |
| 城市坐标 | 公开地理数据 | 历代都城与现代城市经纬度 |

### 4. 字体

| 字体 | 来源 |
|------|------|
| Noto Sans SC | Google Fonts |
| Noto Serif SC | Google Fonts |

> **注意**：历史地图瓦片的版权属于中研院及谭其骧先生，本项目仅作为学术展示用途调用其在线 WMTS 服务，不下载/分发瓦片数据。

---

## AI 操作声明

> **本项目使用 AI 辅助开发，以下说明 AI 参与的部分**

### AI 参与的工作

| 部分 | AI 参与程度 | 说明 |
|------|------------|------|
| **项目架构设计** | AI 生成 | `中国时序地图平台方案.md` 为 AI 生成的整体方案文档 |
| **前端代码** | AI 生成 | 全部 React 组件、样式、状态管理代码由 AI 编写 |
| **WMTS 瓦片对接** | AI 生成 | 朝代 ID 到 WMTS Layer ID 的映射由 AI 调研并编写 |
| **朝代/事件数据** | AI 辅助整理 | 历史数据由 AI 基于公开资料整理，可能存在误差 |
| **城市坐标数据** | AI 辅助 | 经纬度由 AI 根据公开地理数据估算 |
| **README 文档** | AI 生成 | 本文档由 AI 撰写 |
| **数据获取策略文档** | AI 生成 | `docs/数据获取策略.md` 为 AI 调研整理 |

### 人工参与的工作

| 部分 | 说明 |
|------|------|
| **需求定义** | 人工提出项目目标和功能需求 |
| **方向决策** | 人工决定技术选型、数据来源 |
| **效果审核** | 人工审阅 AI 产出的效果并反馈 |
| **质量把关** | 人工验证历史数据准确性 |

### 使用须知

- 历史疆域数据存在学术争议，本项目的地图仅作示意展示用途
- 朝代起止年份、事件描述可能存在偏差，请以权威史料为准
- 如需用于学术研究，请参考原始数据来源
- 欢迎提交 Issue 勘误

---

## 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Next.js | 16.2 | 全栈框架（App Router） |
| React | 18.3 | UI 库 |
| TypeScript | 5.6 | 类型安全 |
| MapLibre GL JS | 4.7 | 地图渲染引擎 |
| Zustand | 5.0 | 状态管理 |
| Tailwind CSS | 3.4 | 样式系统 |
| Framer Motion | 11.11 | 动画过渡 |
| D3.js | 7.9 | 数据可视化 |

---

## 项目结构

```
mapcn/
├── app/                    # Next.js App Router
│   ├── layout.tsx          # 根布局
│   ├── page.tsx            # 首页
│   └── globals.css         # 全局样式
├── components/
│   ├── map/
│   │   └── HistoryMap.tsx  # 历史地图组件（WMTS 瓦片叠加）
│   ├── timeline/
│   │   └── Timeline.tsx    # 朝代时间轴
│   └── ui/
│       ├── Sidebar.tsx     # 右侧信息面板
│       ├── ThemeProvider.tsx# 主题切换
│       └── KeyboardNav.tsx # 键盘导航
├── data/
│   ├── dynasties.ts        # 19 个朝代数据
│   ├── events/events.ts    # 历史事件数据
│   └── geojson/territories.ts # 城市坐标
├── lib/
│   ├── store.ts            # Zustand 状态管理
│   └── utils.ts            # 工具函数
├── types/
│   └── index.ts            # TypeScript 类型定义
├── docs/
│   └── 数据获取策略.md      # 数据源调研文档
├── 中国时序地图平台方案.md  # 整体方案设计文档
├── next.config.mjs
├── package.json
├── tailwind.config.js
└── tsconfig.json
```

---

## 开发命令

```bash
npm run dev     # 启动开发服务器（热更新）
npm run build   # 构建生产包
npm run start   # 启动生产服务器
npm run lint    # 代码检查
```

---

## 开源许可

本项目代码采用 [MIT License](LICENSE) 开源。

历史地图瓦片数据的版权属于中研院及谭其骧《中国历史地图集》相关权利人，本项目仅调用其在线服务，不包含/分发瓦片数据本身。使用时请遵守相应数据源的使用条款。

---

## 参考资源

- [中研院 GIS 专题中心](https://gis.sinica.edu.tw/ccts)
- [OpenFreeMap](https://openfreemap.org/)
- [MapLibre GL JS](https://maplibre.org/)
- [CHGIS 中国历史地理信息系统](https://chgis.fairbank.fas.harvard.edu/)
- [CBDB 中国历代人物传记资料库](https://projects.iq.harvard.edu/cbdb)

---

> 本项目为个人学习项目，不保证历史数据的完全准确性，欢迎交流讨论与勘误。
