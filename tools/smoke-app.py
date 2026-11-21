# -*- coding: utf-8 -*-
"""MAPDEX 勘绘台运行时冒烟：深链硬标准 + 描图全流程 + 未捕获异常监控"""
import re, sys, time
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8090"
OUT = r"D:\AIworkspace\glm\timemap\.tmp-smoke"
fails, notes = [], []

def check(name, ok, detail=""):
    (notes if ok else fails).append(("PASS" if ok else "FAIL") + " " + name + (" :: " + detail if detail else ""))

import os
proxy = os.environ.get("MAPDEX_PROXY", "")
launch_kw = {"headless": True}
if proxy:
    launch_kw["proxy"] = {"server": proxy}
with sync_playwright() as p:
    try:
        browser = p.chromium.launch(**launch_kw)
    except Exception:
        browser = p.chromium.launch(channel="msedge", **launch_kw)
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    pageerrors = []
    page.on("pageerror", lambda e: pageerrors.append(str(e)))
    cerr = []
    page.on("console", lambda m: cerr.append(m.text) if m.type == "error" else None)

    # ---- 1. 深链加载：安史之乱 755 ----
    page.goto(BASE + "/#y=755&map=4/104/35")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2500)

    num = page.locator("#centerYear .cy-num").inner_text().strip()
    check("铭牌==深链年份755", num == "755", "铭牌=" + num)

    ev = page.locator("#eventPanel").inner_text()
    check("事件栏非空且含755事件", len(ev) > 40 and "安史" in ev, "len=%d" % len(ev))

    page.wait_for_timeout(1000)  # writeHash 400ms 防抖
    m = re.search(r"map=([\d.]+)(?:/|%2F)(-?[\d.]+)(?:/|%2F)(-?[\d.]+)", page.url)
    if m:
        z, lng, lat = float(m.group(1)), float(m.group(2)), float(m.group(3))
        check("地图中心≈深链(±0.6°)", abs(lng - 104) < 0.6 and abs(lat - 35) < 0.6,
              "hash中心=%.2f,%.2f" % (lng, lat))
    else:
        check("回写hash存在map段", False, page.url)

    # ---- 2. 勘绘台开合 ----
    page.click("#edToggle")
    page.wait_for_timeout(600)
    check("ed-on 类已挂", "ed-on" in (page.locator("body").get_attribute("class") or ""))
    check("笔架可见", page.locator(".ed-rail").is_visible())
    page.screenshot(path=OUT + r"\ed-open.png")

    # ---- 3. 取底稿（t 快捷键 + 点选疆域；层挂载/软渲染慢，带重试）----
    page.keyboard.press("t")
    n_items = 0
    last_toast = ""
    for i in range(6):
        page.mouse.click(640, 360)
        page.wait_for_timeout(1800)
        n_items = page.locator(".ed-item").count()
        if n_items >= 1:
            break
        t_el = page.locator(".toast:visible")
        if t_el.count():
            last_toast = t_el.first.inner_text()[:40]
    check("取底稿生成草稿条目", n_items >= 1, "条目=%d 末次toast=%s" % (n_items, last_toast))
    page.screenshot(path=OUT + r"\ed-trace.png")

    # ---- 4. 描线（l 快捷键 + 两点 + Enter）----
    page.keyboard.press("l")
    page.wait_for_timeout(200)
    page.mouse.click(500, 300)
    page.mouse.click(560, 340)
    page.keyboard.press("Enter")
    page.wait_for_timeout(600)
    n_items2 = page.locator(".ed-item").count()
    check("描线收尾入库", n_items2 == n_items + 1, "条目=%d→%d" % (n_items, n_items2))
    page.screenshot(path=OUT + r"\ed-line.png")

    # ---- 5. Esc 退层 / 再 Esc 收台 ----
    page.keyboard.press("Escape")
    page.wait_for_timeout(500)
    body1 = page.locator("body").get_attribute("class") or ""
    page.keyboard.press("Escape")
    page.wait_for_timeout(500)
    body2 = page.locator("body").get_attribute("class") or ""
    check("Esc 收台", "ed-on" not in body2, "before=%s after=%s" % (bool("ed-on" in body1), bool("ed-on" in body2)))
    page.screenshot(path=OUT + r"\ed-closed.png")

    # ---- 6. 收台后主图完好 ----
    page.wait_for_timeout(1200)
    num2 = page.locator("#centerYear .cy-num").inner_text().strip()
    check("收台后铭牌仍=755", num2 == "755", "铭牌=" + num2)

    check("无未捕获异常", not pageerrors, "; ".join(pageerrors[:3]))
    bad_console = [c for c in cerr if re.search(r"ReferenceError|TypeError|is not defined|null", c)]
    check("无致命console错误", not bad_console, "; ".join(bad_console[:3]))

    browser.close()

print("\n".join(notes))
if fails:
    print("\n".join(fails))
    print("SMOKE: FAIL (%d)" % len(fails))
    sys.exit(1)
print("SMOKE: PASS (%d)" % len(notes))
