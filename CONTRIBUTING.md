# 贡献数据：描一段墙、添一座关隘

MAPDEX 的版图切片来自 [Cliopatria](https://github.com/Seshat-Global-History-Databank/cliopatria)，粗且全球一致，但**细部不是它的强项**——长城描到哪一年、某个关隘落在哪个沟口、一段河道改易后的走向，这些得靠人照着图册和实地记录一笔一笔描。这里收的就是这类增量。

不需要你会 Git 命令行。地图打开就能画。

## 三步

1. 打开 <https://starve001.github.io/timemap/app/>，点右侧控制组最下面的 **✎（勘绘台）**。
2. 时间轴拖到你要描的年代，左边挑工具：
   - **取底稿**——单击当前年代的政权疆域，把它拓成石青虚线的描摹底，照着描；
   - **描线**（墙、道、河）、**描面**（疆域、城垣）、**落点**（关隘、城址）；
   - **挪点**——拖顶点，在线上单击补点，双击线上删点；
   - **擦除**——单击去掉一条。
   描完按 **Enter** 收尾（面按起点闭合，**Esc** 撤掉描到一半的）。
3. 右边校勘卡填 GitHub 用户名、名称、起止年、依据。没有红字就能 **导出**，或者直接 **递呈**。

草稿存在你自己浏览器里，关掉页面不会丢。

## 两条交回路线

**一键递呈（推荐）**：卡里点「递呈 GitHub」，按提示粘一把只管你自己 fork 的 fine-grained token（Contents: Read and write）。之后建 fork、开分支、写文件都替你做完，最后在 GitHub 预填好的 PR 页面点一下 **Create pull request**。

> 为什么要留最后一下：GitHub 的权限模型不允许浏览器里的 token 往别人仓库开 PR（会 403），所以 token 只用来写你自己的 fork。它只存在页面内存里，刷新即失，也不会发往 GitHub 之外的任何地方。

**手工**：点「导出」拿到 `<用户名>-<日期>.geojson`，然后：

1. 在 <https://github.com/starve001/timemap> 点 Fork；
2. 进自己 fork 的 `contributions/`，没有这个目录就新建一个，名字用你的 GitHub 用户名；
3. 把文件拖进去 → Commit → 回上游发 PR。

两条路最后都要过同一道门禁，所以先本地跑一遍更省事：

```bash
node tools/validate-contribution.js contributions/你的用户名/xxx.geojson
```

## 文件长什么样

顶层是 `FeatureCollection`，每条要素的 `properties` 字段：

| 字段 | 必填 | 说明 |
|------|------|------|
| `name` | ✓ | 60 字内，比如「明长城·宣府镇段」 |
| `kind` | ✓ | `wall` 长城 / `pass` 关隘 / `polity` 政权疆域 / `route` 道路水系 / `site` 城址事件点 / `misc` 其他 |
| `start_year` `end_year` | ✓ | 整数，公元前用负数（`-221`）；要和本图时间轴 `[-221, 1918]` 有交集，否则哪个年代都不会显示 |
| `source` | ✓ | **你照着什么描的**。图册页码、实测记录、文献条目、可核验的链接都行。这一栏是校勘的唯一抓手，写「凭印象」会被退回 |
| `contributor` | ✓ | 你的 GitHub 用户名，要和所在目录一致 |
| `license` | ✓ | `CC0 1.0` 或 `CC BY 4.0` |
| `traced_on` | ✓ | 描图日期 `YYYY-MM-DD` |
| `note` | | 补充说明，可省 |

几何只收 `Point` / `LineString` / `Polygon`。`MultiPolygon` 请先拆成多条要素——拆开后每条能单独校勘、单独接受或退回。

## 会被拦下来的情况

- 文件不在 `contributions/<你的用户名>/` 下，或 `contributor` 与目录名不一致
- 面的外环首尾不闭合、边自相交（轮廓会打结）
- 顶点超出经纬度范围；单要素 > 1200 点、单文件 > 20000 点或 > 512 KB（一次交一段，别把整条墙线塞一个文件）
- `source` 空着或只有几个字
- 起止年与时间轴无交集
- 带了编辑器内部字段（`_id` / `_open` / `_sel`）——用「导出」生成，别手工拼 JSON

顶点数超过 300 会给提醒但不拦，你自己判断是不是描得太密。

## 许可与署名

你描的是自己的表达，版权归你。提交即授权本仓库在 **CC BY 4.0** 下分发这份几何数据，署名按 `contributor` 字段来。想要更彻底的公共领域就填 `CC0 1.0`。上游 Cliopatria 的 CC BY 4.0 与代码的 MIT 许可见 [README.md](README.md)。

## 审 PR 时看什么

给维护者：

1. **轮廓对不对**——PR 页面看不到图，把分支拉下来 `node tools/build-pages.js` 起个静态站，或者直接看 GeoJSON diff 的坐标串；
2. **依据查不查得到**——`source` 里给的图册页码/条目，手边有就翻一眼；
3. **年代合不合**——`start_year`/`end_year` 与该段的修筑年代是否对得上；
4. 门禁只保证几何合法，**不保证史实正确**。这两件事只有人能判断。

合并后 GitHub Actions 会自动重发 Pages，贡献的数据在 <https://starve001.github.io/timemap/app/> 上按年代出现。
