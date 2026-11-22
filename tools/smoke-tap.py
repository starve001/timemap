# -*- coding: utf-8 -*-
"""冒烟：浏览态点选政权信息卡（触屏可用性）——点政权钉卡、点空白/Esc 收起。
前置：本机服务已启动（java -jar server/target/mapdex-server.jar）。用法：python tools/smoke-tap.py""""""
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
    pg.goto("http://127.0.0.1:8090/#y=755&map=4/104/35")
    pg.wait_for_load_state("networkidle")
    pg.wait_for_timeout(13000)  # 等 eras-fill 就绪

    def tip():
        t = pg.locator("#mapTip")
        return t.get_attribute("class") or "", t.inner_text()

    # 点唐境（画面中心偏左，避开政权标签）；无头软渲染首帧慢，带重试
    cls, txt = "", ""
    for _ in range(6):
        pg.mouse.click(700, 400)
        pg.wait_for_timeout(1500)
        cls, txt = tip()
        if "show" in cls and "唐" in txt:
            break
    check("点政权出卡", "show" in cls, txt[:60].replace("\n", " "))
    check("卡含政权名与切片", "唐" in txt and "700" in txt, txt[:80].replace("\n", " "))

    # 鼠标移开（悬停收起逻辑不应干掉钉住的卡）
    pg.mouse.move(100, 100)
    pg.wait_for_timeout(600)
    cls2, _ = tip()
    check("移开鼠标卡仍在", "show" in cls2)

    # 点空白（太平洋中部，755 年无政权；Cliopatria 粗粒度多边形下
    # 北冰洋/南海都会撞上政权，只有远太平洋是真空）→ 收起
    pg.mouse.click(1150, 350)
    pg.wait_for_timeout(600)
    cls3, _ = tip()
    check("点空白收卡", "show" not in cls3)

    # 再点政权 → 出卡 → Esc 收起
    pg.mouse.click(700, 400)
    pg.wait_for_timeout(600)
    cls4, _ = tip()
    check("复点出卡", "show" in cls4)
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(500)
    cls5, _ = tip()
    check("Esc收卡", "show" not in cls5)

    check("无未捕获异常", not errs, "; ".join(errs[:2]))
    pg.screenshot(path=r"D:\AIworkspace\glm\timemap\.tmp-smoke\tap-card.png")
    b.close()

print("TAP-CARD: " + ("PASS" if not fails else "FAIL"))
