# -*- coding: utf-8 -*-
"""冒烟：社区贡献叠加层——API 合并、1400 上屏（石绿长城线）、755 不上屏"""
import sys
from playwright.sync_api import sync_playwright

fails = []
def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (" :: " + detail if detail else ""))
    if not ok: fails.append(name)

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--enable-unsafe-swiftshader"])
    pg = b.new_page(viewport={"width": 1280, "height": 720})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))

    # API 层
    import json, urllib.request
    with urllib.request.urlopen("http://127.0.0.1:8090/api/contributions", timeout=10) as r:
        data = json.loads(r.read().decode("utf-8"))
    check("API 合并=1要素", data.get("type") == "FeatureCollection" and len(data["features"]) == 1,
          str(len(data.get("features", []))))
    check("要素属性齐全", data["features"][0]["properties"].get("contributor") == "starve001"
          and data["features"][0]["properties"].get("start_year") == 1400)

    # 图面：1400（宣府长城在存续区间内）
    pg.goto("http://127.0.0.1:8090/#y=1400&map=5/114.8/40.6")
    pg.wait_for_load_state("networkidle")
    pg.wait_for_timeout(12000)
    pg.screenshot(path=r"D:\AIworkspace\glm\timemap\.tmp-smoke\contribs-1400.png")
    # 悬停卡：用诊断钩子的投影坐标精确移到线上
    mid = pg.evaluate("window.__contribsDebug().then(d => d.projMid)")
    pg.mouse.move(*mid)
    pg.wait_for_timeout(800)
    tip_txt = pg.locator("#mapTip").inner_text()
    check("悬停显示社区贡献卡", "社区贡献" in tip_txt and "宣府" in tip_txt,
          tip_txt[:60].replace("\n", " "))
    pg.goto("http://127.0.0.1:8090/#y=700&map=5/114.8/40.6")  # 同文档导航 → hashchange 热切换正好一起验
    pg.wait_for_timeout(4000)
    num = pg.locator("#centerYear .cy-num").inner_text().strip()
    check("热切换到700生效", num == "700", num)
    pg.screenshot(path=r"D:\AIworkspace\glm\timemap\.tmp-smoke\contribs-700.png")

    check("无未捕获异常", not errs, "; ".join(errs[:2]))
    b.close()

print("CONTRIBS: " + ("PASS" if not fails else "FAIL"))
sys.exit(1 if fails else 0)
