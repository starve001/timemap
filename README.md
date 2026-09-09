# MAPDEX — 世界历史时序地图

一个交互式**世界历史地图**：拖动时间轴即可查看从公元前 221 年到公元 1918 年的全球政权版图演变，并同步呈现同期历史事件。全部政权中文标注、可追溯数据源。

## 功能特性

- **时间轴播放 / 拖动**：年份按 5 年粒度推进，自动切换对应年代的全球版图切片
- **政权版图图层**：全部政权中文标注，按控制类型区分图层（实控疆域 / 势力范围 / 殖民与附属）
- **历史事件时间线**：右侧事件栏支持 ±100 年 / ±50 年 / 精确到当年 三档粒度，点击事件可在地图上定位
- **年份跳转**：在搜索框输入年份（如 `-221`、`1492`、`前221年`、`bc221`）回车，直达该年世界局势
- **政权筛选**：按类别（帝国 / 王国 / 汗国 / 共和国等）与区域过滤显示
- **数据可溯源**：每个政权均携带起止年份、首都、类别、来源等属性字段

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | 原生 HTML + JavaScript + MapLibre GL JS（单文件应用） |
| 后端 | Java 21 + Spring Boot 3.5（REST API + 静态资源托管） |
| 数据 | 56 个版图切片（GeoJSON）+ 事件库（JSON），派生自 Cliopatria / Seshat |

## 快速开始

### 环境要求

- JDK 21（无 Maven 亦可，构建脚本自带阿里云镜像配置）

### 方式一：脚本启动（Windows）

双击 `mapstart.bat`，首次运行自动构建并启动服务，浏览器自动打开 <http://127.0.0.1:8090>

### 方式二：手动构建运行

```bash
cd server
mvn -s maven-settings.xml clean package
java -jar target/mapdex-server.jar
```

打开 <http://127.0.0.1:8090>

## 目录结构

```
mapdex/
├── server/                  # Spring Boot 后端
│   ├── src/main/java/       # API 控制器与数据加载（com.mapdex.server）
│   ├── src/main/resources/  # 前端静态页 + application.properties
│   ├── pom.xml              # Maven 配置
│   └── build.bat            # Windows 构建脚本
├── data/                    # 运行时数据
│   ├── eras/                # 56 个版图切片（world_*.geojson）+ 中文名对照表
│   └── cities.json          # 城市数据
├── events.json              # 历史事件库（224 条，公元前 221 年 ~ 公元 1918 年）
├── tools/                   # 数据处理脚本（切片构建 / 中文名注入 / 数据校验）
│   └── cliopatria/          # 数据源说明（原始数据体积过大未入库，见下）
└── mapstart.bat             # 一键启动脚本
```

## 数据来源与授权

- 全部政权版图数据派生自 **[Cliopatria](https://github.com/Seshat-Global-History-Databank/cliopatria)**（Seshat 全球历史数据库，覆盖 3400 BCE – 2024 CE 全球政区），遵循 **CC BY 4.0** 许可
- 原始数据 `cliopatria_polities_only.geojson`（约 165 MB）因超出 GitHub 单文件限制未随仓库分发；需要重新构建切片时，请从 [Cliopatria 仓库](https://github.com/Seshat-Global-History-Databank/cliopatria) 或 [Zenodo](https://zenodo.org/records/13363121) 下载后放入 `tools/cliopatria/` 目录
- 历史事件为人工整理编写
- 本仓库代码采用 MIT 许可；派生数据遵循上游 CC BY 4.0

## 致谢

[Cliopatria / Seshat Global History Databank](https://seshatdatabank.info/) — 全球历史政区开源数据集
