#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/build-qin-han-eras.py — 构建先秦/秦汉至东汉（-221 ~ 200 CE，重点精修汉代西域与河西走廊）高精度版图切片与西域名城

核心改进：
1. 加密关键历史节点切片：
   -221 (秦并六国) -> -210 (秦平岭南收河套极盛) -> -206 (楚汉十八诸侯) -> -200 (汉初白登·冒顿控西域)
   -> -140 (汉武初·张骞西行前) -> -115 (霍去病开河西四郡·断匈奴右臂) -> -100 (平南越朝鲜·贰师伐大宛)
   -> -60 (郑吉设西域都护府) -> -1 (西汉极盛·汉匈和亲) -> 15 (王莽新朝·西域断绝)
   -> 40 (光武中兴·莎车霸南道) -> 100 (班超定西域·东汉极盛) -> 150 (班勇西域长史府·鲜卑崛起) -> 200 (建安官渡群雄·西域分立)
2. 基于真实 Terrarium z6 地形高程矩阵提取自然盆地与山前绿洲带（塔里木盆地南北道、吐鲁番哈密盆地、
   河西走廊、伊犁河谷伊塞克湖、费尔干纳盆地），结合 Natural Earth 1:10m 海岸线裁剪，告别生硬折线与海岸错位；
3. 恢复并落地三层控制语义（properties.ctrl）：
   - "direct"       实控州郡 / 独立王国（实心着色 + 实线边界）
   - "protectorate" 都护府 / 长史府 / 僮仆都尉军政统辖区（斜纹半透明 + 虚线金边，内部绿洲城邦可独立点选）
   - "tributary"    内附藩属（如东汉河套南匈奴）
4. 彻底修复 Cliopatria 上游将费尔干纳『大宛 (Dayuan)』误写为 "Great Yuan" 并错链至元朝的乌龙，补齐全部译名与西域名城。
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import shapefile
from PIL import Image
from scipy.ndimage import gaussian_filter, map_coordinates
from shapely.geometry import GeometryCollection, MultiPolygon, Point, Polygon, box, mapping, shape
from shapely.ops import unary_union
from shapely.validation import make_valid

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".tmp-basemap-src"
ERAS_DIR = ROOT / "data" / "eras"
CITIES_PATH = ROOT / "data" / "cities.json"
NAME_ZH_PATH = ERAS_DIR / "name-zh.json"

TARGET_YEARS = [-221, -210, -206, -200, -140, -115, -100, -60, -1, 15, 40, 100, 150, 200]

ERA_LABELS = {
    -221: "前221年",
    -210: "前210年",
    -206: "前206年",
    -200: "前200年",
    -140: "前140年",
    -115: "前115年",
    -100: "前100年",
    -60: "前60年",
    -1: "前1年",
    15: "公元15年",
    40: "公元40年",
    100: "100年",
    150: "公元150年",
    200: "200年",
}


def file_for(y: int) -> str:
    return f"world_bc{-y}.geojson" if y < 0 else f"world_{y}.geojson"


def hash_name(s: str) -> int:
    h = 0
    for ch in s:
        h = ((h * 31 + ord(ch)) & 0xFFFFFFFF)
    return h


# ==================== 1. 加载亚洲 DEM 网格并提取真实地形盆地轮廓 ====================

def build_asia_dem_grid() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    拼接 .tmp-basemap-src/terrarium_raw/6/{41..56}/{18..29}.png (50.625°E..140.625°E, 11.18°N..55.78°N)，
    重采样到规则经纬度网格 (dlon=0.05°, dlat=0.05°)，用于提取贴合山麓等高线的历史政区/绿洲几何。
    """
    x0, x1 = 41, 56
    y0, y1 = 18, 29
    w = (x1 - x0 + 1) * 256
    h = (y1 - y0 + 1) * 256
    merc = np.zeros((h, w), dtype=np.float32)
    for tx in range(x0, x1 + 1):
        for ty in range(y0, y1 + 1):
            p = CACHE / "terrarium_raw" / "6" / str(tx) / f"{ty}.png"
            with Image.open(p) as im:
                rgb = np.asarray(im.convert("RGB"), dtype=np.float32)
            elev = (rgb[..., 0] * 256.0 + rgb[..., 1] + rgb[..., 2] / 256.0) - 32768.0
            ox = (tx - x0) * 256
            oy = (ty - y0) * 256
            merc[oy : oy + 256, ox : ox + 256] = elev

    lons = np.arange(52.0, 139.01, 0.05, dtype=np.float32)
    lats = np.arange(13.0, 55.01, 0.05, dtype=np.float32)
    n_tiles = 64.0
    px_x = ((lons + 180.0) / 360.0 * n_tiles - x0) * 256.0 - 0.5
    lat_rad = np.radians(lats)
    px_y = ((1.0 - np.log(np.tan(lat_rad) + 1.0 / np.cos(lat_rad)) / math.pi) * 0.5 * n_tiles - y0) * 256.0 - 0.5

    gx = np.broadcast_to(px_x[None, :], (len(lats), len(lons)))
    gy = np.broadcast_to(px_y[:, None], (len(lats), len(lons)))
    grid = map_coordinates(merc, np.stack([gy, gx], axis=0), order=1, mode="nearest", prefilter=False)
    grid_smooth = gaussian_filter(grid, sigma=1.35)
    return lons, lats, grid_smooth


def contour_mask_to_poly(lons: np.ndarray, lats: np.ndarray, field: np.ndarray, threshold: float, mode: str = "le", clip_poly=None, min_area: float = 0.15):
    """用等高线追踪将布尔地形场转为自然圆润的 Shapely 多边形"""
    arr = field.astype(np.float32) if mode == "raw" else ((threshold - field) if mode == "le" else (field - threshold))
    fig, ax = plt.subplots()
    cs = ax.contourf(lons, lats, arr, levels=[0.0, 1e9])
    plt.close(fig)
    polys = []
    for segs in cs.allsegs[0]:
        if len(segs) >= 4:
            p = make_valid(Polygon(segs))
            if not p.is_empty:
                polys.append(p)
    if not polys:
        return Polygon()
    merged = unary_union(polys)
    if clip_poly is not None:
        merged = merged.intersection(clip_poly)
    return clean_poly(merged, min_area=min_area)


def smooth_ctrl_poly(pts: list[tuple[float, float]]) -> Polygon:
    """将控制点多边形用三次样条平滑为自然地理边界"""
    n = len(pts)
    out = []
    for i in range(n):
        p0 = pts[(i - 1) % n]
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n]
        for s in range(5):
            t = s / 5.0
            t2, t3 = t * t, t * t * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append((x, y))
    return clean_poly(Polygon(out), min_area=0.02)


def clean_poly(g, tol: float = 0.025, min_area: float = 0.03):
    if g is None or g.is_empty:
        return Polygon()
    g = make_valid(g)
    parts = []
    def collect(geom):
        if isinstance(geom, Polygon):
            if geom.area >= min_area:
                ext = geom.exterior
                holes = [h for h in geom.interiors if Polygon(h).area >= min_area * 1.5]
                parts.append(Polygon(ext, holes))
        elif isinstance(geom, (MultiPolygon, GeometryCollection)):
            for sub in geom.geoms:
                collect(sub)
    collect(g)
    if not parts:
        return Polygon()
    u = unary_union(parts)
    if tol > 0:
        u = make_valid(u.simplify(tol, preserve_topology=True))
    parts2 = []
    def collect2(geom):
        if isinstance(geom, Polygon) and geom.area >= min_area:
            parts2.append(geom)
        elif isinstance(geom, (MultiPolygon, GeometryCollection)):
            for sub in geom.geoms:
                collect2(sub)
    collect2(u)
    if not parts2:
        return Polygon()
    return parts2[0] if len(parts2) == 1 else MultiPolygon(parts2)


def load_east_asia_10m_land():
    shp = CACHE / "unpacked" / "ne_10m_land" / "ne_10m_land.shp"
    clip_b = box(60.0, 14.0, 138.0, 56.0)
    polys = []
    with shapefile.Reader(str(shp)) as sf:
        for sr in sf.iterShapes():
            if not sr.bbox:
                continue
            if sr.bbox[2] < 60.0 or sr.bbox[0] > 138.0 or sr.bbox[3] < 14.0 or sr.bbox[1] > 56.0:
                continue
            g = make_valid(shape(sr.__geo_interface__)).intersection(clip_b)
            if not g.is_empty:
                polys.append(g)
    return clean_poly(unary_union(polys), tol=0.015, min_area=0.02)


def to_geojson_geom(g) -> dict | None:
    g = clean_poly(g, tol=0.018, min_area=0.025)
    if g.is_empty:
        return None
    m = mapping(g)
    def rnd(c):
        if isinstance(c[0], (int, float)):
            return [round(float(c[0]), 3), round(float(c[1]), 3)]
        out = [rnd(x) for x in c]
        if out and isinstance(out[0][0], (int, float)):
            dedup = []
            for pt in out:
                if not dedup or dedup[-1] != pt:
                    dedup.append(pt)
            if len(dedup) >= 3 and dedup[0] != dedup[-1]:
                dedup.append(list(dedup[0]))
            return dedup if len(dedup) >= 4 else []
        return [x for x in out if x]

    coords = rnd(m["coordinates"])
    if m["type"] == "Polygon":
        coords = [r for r in coords if len(r) >= 4]
        cand = {"type": "Polygon", "coordinates": coords} if coords else None
    else:
        coords = [[r for r in poly if len(r) >= 4] for poly in coords]
        coords = [poly for poly in coords if poly]
        if not coords:
            return None
        cand = {"type": "Polygon", "coordinates": coords[0]} if len(coords) == 1 else {"type": "MultiPolygon", "coordinates": coords}
    if not cand:
        return None
    chk = make_valid(shape(cand))
    if chk.is_empty:
        return None
    return cand


def compute_bbox_meta(geom_dict: dict) -> tuple[int, list[float]]:
    x0, x1, y0, y1 = 180.0, -180.0, 90.0, -90.0
    def walk(c):
        nonlocal x0, x1, y0, y1
        if isinstance(c[0], (int, float)):
            x, y = float(c[0]), float(c[1])
            if x < x0: x0 = x
            if x > x1: x1 = x
            if y < y0: y0 = y
            if y > y1: y1 = y
        else:
            for sub in c:
                walk(sub)
    walk(geom_dict["coordinates"])
    area_deg2 = max(1, int(round((x1 - x0) * (y1 - y0))))
    center = [round((x0 + x1) * 0.5, 2), round((y0 + y1) * 0.5, 2)]
    return area_deg2, center


# ==================== 2. 构建地形贴合的历史地理单元库 ====================

def build_terrain_templates(lons: np.ndarray, lats: np.ndarray, elev: np.ndarray, land_ea):
    tpl = {}

    # 费尔干纳盆地（大宛 Dayuan）：天山与阿赖山环抱的天然盆地 (elev < 2350m)
    fergana_clip = smooth_ctrl_poly([
        (69.3, 40.1), (70.3, 41.35), (71.8, 41.85), (73.45, 41.25),
        (73.55, 40.25), (72.3, 39.75), (70.6, 39.75),
    ])
    tpl["dayuan"] = contour_mask_to_poly(lons, lats, elev, 2450.0, "le", fergana_clip, min_area=0.3)

    # 伊犁河谷 + 伊塞克湖盆地（乌孙西迁后王庭故地）
    wusun_west_clip = smooth_ctrl_poly([
        (74.2, 42.1), (75.2, 44.5), (78.2, 45.4), (81.8, 44.9),
        (83.6, 43.7), (82.2, 42.6), (79.5, 41.9), (76.5, 41.8),
    ])
    tpl["wusun_ili"] = contour_mask_to_poly(lons, lats, elev, 3250.0, "le", wusun_west_clip, min_area=0.5)

    # 先秦/秦末乌孙故地（敦煌祁连西端，与月氏比邻）
    tpl["wusun_early"] = smooth_ctrl_poly([
        (91.8, 40.2), (92.5, 41.6), (95.0, 41.8), (95.6, 40.5), (94.2, 39.6), (92.4, 39.6),
    ])

    # 河西走廊（祁连山北麓走廊带延伸衔接陇西/金城郡 elev < 2850m，确保与关中本土无缝贯通）
    hexi_clip = smooth_ctrl_poly([
        (93.6, 39.5), (94.2, 41.3), (97.5, 41.4), (100.8, 40.8),
        (104.2, 39.2), (106.6, 36.8), (106.4, 34.8), (103.5, 35.4),
        (101.5, 36.8), (99.2, 37.9), (96.0, 38.9),
    ])
    tpl["hexi"] = contour_mask_to_poly(lons, lats, elev, 2950.0, "le", hexi_clip, min_area=0.5)

    # 先秦秦汉之际月氏故地（居敦煌祁连间，含河西走廊中段至哈密东）
    yuezhi_early_clip = smooth_ctrl_poly([
        (93.2, 42.6), (96.5, 42.4), (100.8, 41.2), (103.6, 38.6),
        (102.2, 37.3), (98.8, 38.4), (95.4, 39.5), (93.0, 40.8),
    ])
    tpl["yuezhi_hexi"] = contour_mask_to_poly(lons, lats, elev, 2900.0, "le", yuezhi_early_clip, min_area=0.5)

    # 塔里木盆地（天山南麓—葱岭东麓—昆仑北麓 elev < 2450m）+ 吐鲁番哈密车师盆地
    tarim_clip = smooth_ctrl_poly([
        (74.4, 39.6), (76.2, 41.2), (80.2, 42.1), (84.5, 42.4), (88.8, 42.2),
        (92.8, 41.4), (93.6, 39.8), (91.8, 38.4), (88.2, 37.2), (83.5, 36.4),
        (79.2, 36.5), (76.2, 37.5), (74.6, 38.6),
    ])
    tarim_basin = contour_mask_to_poly(lons, lats, elev, 2500.0, "le", tarim_clip, min_area=1.0)

    turpan_clip = smooth_ctrl_poly([
        (87.6, 42.2), (88.2, 44.2), (91.5, 44.3), (94.8, 43.5),
        (95.0, 42.1), (91.8, 41.6), (89.0, 41.8),
    ])
    turpan_basin = contour_mask_to_poly(lons, lats, elev, 2300.0, "le", turpan_clip, min_area=0.4)

    # 塔克拉玛干无人流沙腹地（扣除后即得南北两道真实山前绿洲环带！）
    taklamakan_sand = smooth_ctrl_poly([
        (78.6, 39.2), (80.5, 40.05), (83.8, 40.25), (86.8, 39.95),
        (87.6, 39.15), (85.8, 38.25), (82.5, 37.75), (79.6, 38.05),
    ])
    oasis_belt = clean_poly(unary_union([tarim_basin, turpan_basin]).difference(taklamakan_sand), min_area=0.15)

    # 西域七大核心绿洲城邦群（贴合南北两道山前绿洲扇与河谷）
    oasis_defs = {
        "shanshan": smooth_ctrl_poly([(87.0, 36.8), (87.4, 40.85), (92.8, 41.2), (93.5, 39.5), (91.2, 37.4)]),  # 楼兰/鄯善（含且末精绝东段）
        "khotan": smooth_ctrl_poly([(78.6, 36.1), (79.0, 38.4), (84.2, 38.5), (87.0, 37.2), (83.5, 36.0)]),     # 于阗（含扜弥渠勒精绝西）
        "yarkant": smooth_ctrl_poly([(75.6, 37.0), (76.8, 39.1), (79.2, 38.9), (78.8, 36.8), (76.8, 36.7)]),    # 莎车（含皮山叶城）
        "shule": smooth_ctrl_poly([(74.2, 38.7), (74.8, 40.5), (78.5, 40.4), (78.2, 38.9), (75.5, 38.5)]),      # 疏勒（喀什噶尔绿洲）
        "kucha": smooth_ctrl_poly([(78.3, 40.1), (79.2, 42.2), (84.6, 42.4), (84.8, 40.3), (81.2, 40.1)]),      # 龟兹（含姑墨温宿轮台西）
        "yanqi": smooth_ctrl_poly([(84.5, 40.4), (84.6, 42.5), (88.4, 42.3), (88.8, 40.6), (86.2, 40.4)]),      # 焉耆（含危须尉犁博斯腾湖）
        "jushi": smooth_ctrl_poly([(87.8, 41.9), (88.2, 44.3), (94.8, 43.6), (94.9, 42.0), (90.5, 41.7)]),      # 车师前后国（交河高昌务涂谷）
    }
    used = Polygon()
    for key, mask_p in oasis_defs.items():
        g = clean_poly(oasis_belt.intersection(mask_p).difference(used), tol=0.02, min_area=0.08)
        tpl[key] = g
        used = unary_union([used, g])

    # 东汉建武年间莎车王贤称霸西域南道版图
    tpl["yarkant_hegemon"] = clean_poly(unary_union([tpl["yarkant"], tpl["khotan"], tpl["shule"]]), tol=0.02, min_area=0.2)

    # 西域都护府（西汉神爵二年 -60 ~ 新莽 13，及东汉班超 91 ~ 107）：统辖南北两道及车师全境，西抵葱岭巴尔喀什东南
    prot_hull = smooth_ctrl_poly([
        (73.6, 39.2), (74.8, 41.0), (78.8, 42.2), (83.8, 42.8), (88.0, 44.0),
        (93.8, 43.4), (93.85, 39.4), (91.5, 37.4), (86.8, 36.4), (81.2, 36.1),
        (76.8, 36.8), (74.4, 37.9),
    ])
    tpl["protectorate_full"] = clean_poly(prot_hull.difference(tpl["wusun_ili"]).difference(tpl["dayuan"]), tol=0.025, min_area=1.0)

    # 西域长史府（东汉班勇 123 ~ 175 屯柳中）：务实统辖塔里木盆地与车师六国
    changshi_hull = smooth_ctrl_poly([
        (75.0, 39.3), (76.5, 40.9), (80.5, 42.0), (85.2, 42.4), (88.2, 43.6),
        (93.85, 43.2), (93.85, 39.5), (91.0, 37.5), (86.2, 36.5), (80.5, 36.3), (76.6, 37.2),
    ])
    tpl["protectorate_changshi"] = clean_poly(changshi_hull, tol=0.025, min_area=1.0)

    # 匈奴僮仆都尉（冒顿至宣帝前 -200 ~ -61）：居焉耆危须尉犁间赋税诸国
    tongpu_hull = smooth_ctrl_poly([
        (75.5, 39.5), (78.0, 41.5), (83.5, 42.5), (88.0, 44.0), (93.8, 43.5),
        (93.5, 40.0), (89.5, 38.8), (84.0, 39.8), (78.5, 39.5),
    ])
    tpl["xiongnu_tongpu"] = clean_poly(tongpu_hull, tol=0.03, min_area=1.0)

    # 康居（锡尔河中游塔什干—塔拉斯草原绿洲带）
    tpl["kangju"] = smooth_ctrl_poly([
        (64.2, 41.5), (63.8, 44.6), (67.5, 46.2), (72.2, 45.2),
        (73.8, 43.2), (71.5, 41.6), (68.5, 40.6), (65.8, 40.8),
    ])

    # 西羌诸部（河曲—青海湖—湟水高原）
    tpl["qiang"] = smooth_ctrl_poly([
        (95.2, 35.0), (96.5, 37.6), (99.8, 37.8), (102.6, 36.4),
        (103.2, 34.2), (100.8, 32.8), (97.2, 33.4),
    ])

    # 滇国（滇池云贵高原中部）与 夜郎（黔中北盘江乌江流域）与 东瓯（浙南瓯江）
    tpl["dian"] = smooth_ctrl_poly([
        (101.2, 24.0), (101.6, 25.8), (103.8, 26.0), (104.4, 24.5), (102.8, 23.5),
    ])
    tpl["yelang"] = smooth_ctrl_poly([
        (104.6, 25.2), (105.2, 27.6), (108.0, 27.9), (108.6, 26.0), (106.8, 24.8),
    ])
    tpl["dongou"] = clean_poly(smooth_ctrl_poly([
        (119.2, 27.2), (119.4, 28.8), (121.8, 28.9), (121.6, 27.1),
    ]).intersection(land_ea), tol=0.02, min_area=0.1)

    # 东胡（西辽河—呼伦贝尔—大兴安岭）与 夫余（松嫩平原）与 乌桓（辽西西拉木伦）
    tpl["donghu"] = smooth_ctrl_poly([
        (115.5, 41.8), (116.2, 46.8), (120.5, 49.5), (124.8, 47.8),
        (124.5, 43.2), (120.8, 41.2), (117.5, 41.0),
    ])
    tpl["buyeo"] = smooth_ctrl_poly([
        (123.2, 43.2), (123.6, 46.8), (127.8, 47.2), (128.6, 44.2), (125.8, 42.8),
    ])
    tpl["wuhuan"] = smooth_ctrl_poly([
        (116.8, 40.8), (117.5, 43.6), (121.8, 43.8), (122.2, 41.4), (119.2, 40.5),
    ])

    # 秦始皇北收河南地（河套九原郡）与南平百越（南海、桂林、象三郡）增量区
    tpl["qin_hetao"] = smooth_ctrl_poly([
        (106.4, 37.8), (106.8, 41.1), (110.2, 41.1), (111.6, 40.2), (111.2, 38.2), (108.5, 37.4),
    ])
    tpl["qin_lingnan"] = clean_poly(smooth_ctrl_poly([
        (105.2, 18.2), (105.8, 22.8), (108.5, 25.6), (112.5, 25.8),
        (116.8, 24.8), (117.5, 22.0), (110.5, 19.8), (106.8, 17.8),
    ]).intersection(land_ea), tol=0.02, min_area=0.2)

    # 海南岛（汉武帝元封元年置珠崖、儋耳二郡）
    tpl["hainan"] = clean_poly(box(108.5, 18.0, 111.2, 20.2).intersection(land_ea), tol=0.015, min_area=0.1)

    return tpl


# ==================== 3. Cliopatria 提取与分年代精修合成 ====================

def load_cliopatria_polities() -> list[dict]:
    clio_path = CACHE / "cliopatria.geojson"
    raw = json.loads(clio_path.read_text(encoding="utf-8"))
    out = []
    for f in raw["features"]:
        p = f.get("properties") or {}
        if p.get("Type") != "POLITY":
            continue
        if p.get("Components") or str(p.get("Name", "")).startswith("("):
            continue
        out.append(f)
    return out


def query_clio_poly(pols: list[dict], name: str, year: int):
    for f in pols:
        p = f["properties"]
        if p["Name"] == name and p["FromYear"] <= year <= p["ToYear"]:
            return clean_poly(shape(f["geometry"]), tol=0.02, min_area=0.03)
    return Polygon()


def make_feat(
    name_en: str,
    name_zh: str,
    geom,
    start_y: int,
    end_y: int,
    capital: str = "",
    ptype: str = "polity",
    ctrl: str = "direct",
    subject_to: str = "",
    region: str = "East & Central Asia",
    wiki: str = "",
    wikidata: str = "",
    source: str = "MAPDEX 秦汉西域精修层（基于《史记》《汉书·西域传》考据 + DEM 地形等高线与 Cliopatria CC BY 4.0）",
) -> dict | None:
    gd = to_geojson_geom(geom)
    if not gd:
        return None
    area_deg2, center = compute_bbox_meta(gd)
    return {
        "type": "Feature",
        "properties": {
            "NAME": name_en,
            "C": hash_name(name_zh or name_en) % 12,
            "name": name_en,
            "start_year": start_y,
            "end_year": end_y,
            "capital": capital,
            "type": ptype,
            "ctrl": ctrl,
            "SUBJECTO": subject_to,
            "region": region,
            "event": "",
            "source": source,
            "wikipedia": wiki,
            "wikidata": wikidata,
            "_a": area_deg2,
            "_c": center,
            "_nz": name_zh,
            "_sz": subject_to,
        },
        "geometry": gd,
    }


def add_tarim_oasis_states(feats: list[dict], tpl: dict, year: int, subject_to: str = "", hegemon_yarkant: bool = False) -> None:
    """注入西域南北两道七大核心绿洲城郭国"""
    if year >= -77:
        ss_en, ss_zh, ss_cap, ss_sy = "Shanshan", "鄯善", "扜泥城", -77
    else:
        ss_en, ss_zh, ss_cap, ss_sy = "Loulan", "楼兰", "楼兰城", -221

    items = [
        (ss_en, ss_zh, tpl["shanshan"], ss_sy, 448, ss_cap, "Shanshan", "Q1193691"),
        ("Jushi", "车师", tpl["jushi"], -221, 450, "交河城", "Jushi_Kingdom", "Q1372186"),
        ("Yanqi", "焉耆", tpl["yanqi"], -221, 648, "员渠城", "Yanqi", "Q1369771"),
        ("Kucha", "龟兹", tpl["kucha"], -221, 648, "延城", "Kucha", "Q847985"),
    ]
    if hegemon_yarkant:
        items.append(("Yarkant", "莎车", tpl["yarkant_hegemon"], -221, 87, "莎车城", "Yarkant_Kingdom", "Q10934334"))
    else:
        items.extend([
            ("Khotan", "于阗", tpl["khotan"], -221, 1006, "西城", "Kingdom_of_Khotan", "Q912365"),
            ("Yarkant", "莎车", tpl["yarkant"], -221, 600, "莎车城", "Yarkant_Kingdom", "Q10934334"),
            ("Shule", "疏勒", tpl["shule"], -221, 650, "疏勒城", "Shule_Kingdom", "Q2575039"),
        ])

    for en, zh, g, sy, ey, cap, wk, wd in items:
        f = make_feat(
            en, zh, g, sy, ey, capital=cap, ptype="oasis-kingdom",
            ctrl="direct", subject_to=subject_to, region="Western Regions", wiki=wk, wikidata=wd,
        )
        if f:
            feats.append(f)


def build_slice(year: int, pols: list[dict], tpl: dict, land_ea, zh_dict: dict) -> list[dict]:
    # 1. 取 Cliopatria 当年全球要素，剔除被我们精修接管的东亚/西域重叠记录
    REPLACE_NAMES_BY_YEAR: dict[int, set[str]] = {
        -221: {"Qin", "Qi", "Minyue", "Yuezhi", "Great Yuan"},
        -210: {"Qin Dynasty", "Minyue", "Yuezhi", "Great Yuan"},
        -206: {"Great Yuan", "Yuezhi"},
        -200: {"Han Dynasty", "Nanyue", "Minyue", "Xiongnu", "Yuezhi", "Wusun", "Great Yuan"},
        -140: {"Han Dynasty", "Nanyue", "Minyue", "Xiongnu", "Wusun", "Great Yuan"},
        -115: {"Han Dynasty", "Nanyue", "Minyue", "Xiongnu", "Wusun", "Great Yuan"},
        -100: {"Han Dynasty", "Xiongnu", "Wusun", "Great Yuan"},
        -60:  {"Han Dynasty", "Xiongnu", "Wusun", "Great Yuan"},
        -1:   {"Han Dynasty", "Xiongnu", "Wusun", "Great Yuan"},
        15:   {"Xin Dynasty", "Han Dynasty", "Xiongnu", "Wusun", "Great Yuan"},
        40:   {"Han Dynasty", "Xiongnu", "Wusun", "Great Yuan"},
        100:  {"Han Dynasty", "Southern Xiongnu", "Xiongnu", "Wusun", "Great Yuan"},
        150:  {"Han Dynasty", "Protectorate of the Western Regions", "Wusun", "Xianbei"},
        200:  {"Han Dynasty", "Cao Cao", "Protectorate of the Western Regions", "Wusun"},
    }
    skip = REPLACE_NAMES_BY_YEAR.get(year, set())

    base_feats: list[dict] = []
    for f in pols:
        p = f["properties"]
        if not (p["FromYear"] <= year <= p["ToYear"]):
            continue
        nm = p["Name"]
        if nm in skip:
            continue
        g = clean_poly(shape(f["geometry"]), tol=0.02, min_area=0.03)
        if g.is_empty:
            continue
        # 若在东亚沿海（如楚汉十八诸侯、朝鲜半岛诸国），与 1:10m 陆地海岸线取交以消除锯齿出海
        minx, miny, maxx, maxy = g.bounds
        if minx >= 95.0 and maxx <= 135.0 and miny >= 15.0 and maxy <= 46.0:
            g_land = clean_poly(g.intersection(land_ea), tol=0.02, min_area=0.025)
            if not g_land.is_empty:
                g = g_land

        nz = zh_dict.get(nm, "")
        if nm == "Great Yuan":
            nm_out, nz, wk, wd, cap = "Dayuan", "大宛", "Dayuan", "Q1059959", "贵山城"
        else:
            nm_out, wk, wd, cap = nm, p.get("Wikipedia", ""), p.get("Wikidata", ""), ""
            if nm == "Western Chu": cap = "彭城"
            elif nm == "Han" and year == -206: cap = "南郑"

        feat = make_feat(
            nm_out, nz, g, p["FromYear"], p["ToYear"],
            capital=cap, ptype="polity", ctrl="direct", region="",
            wiki=wk, wikidata=wd, source="Cliopatria / Seshat Global History Databank (CC BY 4.0)",
        )
        if feat:
            base_feats.append(feat)

    # 2. 构建东亚与西域精修要素（按实控优先级做拓扑互斥裁切，保证零重叠）
    reg_direct: list[tuple[str, str, object, int, int, str, str, str, str]] = []
    reg_overlay: list[dict] = []
    oasis_subject = ""
    hegemon_yarkant = False

    # 预取常用 Cliopatria 基准多边形
    han_core_early = query_clio_poly(pols, "Han Dynasty", -140)
    han_with_south = query_clio_poly(pols, "Han Dynasty", -100)
    han_peak_raw = query_clio_poly(pols, "Han Dynasty", -36)
    korea_4_cmd = clean_poly(han_peak_raw.intersection(box(123.5, 37.5, 129.2, 42.8)).intersection(land_ea), tol=0.02)
    east_of_yumen = box(93.75, 15.0, 135.0, 50.0)

    if year == -221:
        qin_221 = clean_poly(unary_union([
            query_clio_poly(pols, "Qin", -221),
            query_clio_poly(pols, "Qi", -221),
        ]).intersection(land_ea), tol=0.02)
        minyue = clean_poly(query_clio_poly(pols, "Minyue", -221).intersection(land_ea), tol=0.02)
        nanyue_pre = clean_poly(tpl["qin_lingnan"].difference(qin_221).difference(minyue), tol=0.02)
        xiongnu_early = smooth_ctrl_poly([
            (96.5, 41.6), (98.5, 46.8), (105.0, 48.5), (113.5, 47.2),
            (115.6, 43.2), (113.8, 40.6), (109.5, 39.2), (105.5, 39.8), (101.2, 41.2),
        ])
        reg_direct.extend([
            ("Qin Dynasty", "秦朝", qin_221, -221, -206, "咸阳", "empire", "Qin_dynasty", "Q7183"),
            ("Minyue", "闽越", minyue, -334, -110, "东冶", "kingdom", "Minyue", "Q837158"),
            ("Baiyue", "岭南百越", nanyue_pre, -350, -214, "番禺", "tribal-confederacy", "Baiyue", "Q699904"),
            ("Dian Kingdom", "滇国", tpl["dian"], -278, -109, "滇池", "kingdom", "Dian_Kingdom", "Q1208982"),
            ("Yelang", "夜郎", tpl["yelang"], -300, -27, "夜郎邑", "kingdom", "Yelang", "Q1151621"),
            ("Xiongnu", "匈奴", xiongnu_early, -240, 48, "头曼城", "khaganate", "Xiongnu", "Q188836"),
            ("Donghu", "东胡", tpl["donghu"], -600, -206, "乌桓山", "confederacy", "Donghu_people", "Q1142862"),
            ("Buyeo", "夫余", tpl["buyeo"], -239, 494, "夫余城", "kingdom", "Buyeo", "Q28044"),
            ("Yuezhi", "月氏", tpl["yuezhi_hexi"], -350, -162, "昭武（张掖）", "nomadic-kingdom", "Yuezhi", "Q204797"),
            ("Wusun", "乌孙", tpl["wusun_early"], -300, -162, "敦煌祁连间", "nomadic-kingdom", "Wusun", "Q634420"),
            ("Dayuan", "大宛", tpl["dayuan"], -250, 260, "贵山城", "kingdom", "Dayuan", "Q1059959"),
            ("Kangju", "康居", tpl["kangju"], -250, 320, "卑阗城", "kingdom", "Kangju", "Q1062004"),
            ("Western Qiang", "西羌", tpl["qiang"], -300, 220, "赐支河曲", "tribal-confederacy", "Qiang_people", "Q841362"),
        ])

    elif year == -210:
        qin_peak = clean_poly(unary_union([
            query_clio_poly(pols, "Qin Dynasty", -210),
            tpl["qin_hetao"],
            tpl["qin_lingnan"],
        ]).intersection(land_ea), tol=0.02)
        minyue = clean_poly(query_clio_poly(pols, "Minyue", -210).intersection(land_ea).difference(tpl["qin_lingnan"]), tol=0.02)
        qin_peak = clean_poly(qin_peak.difference(minyue), tol=0.02)
        xiongnu_210 = smooth_ctrl_poly([
            (96.0, 42.0), (98.0, 47.8), (105.5, 49.8), (114.2, 48.2),
            (115.6, 43.5), (112.8, 41.3), (106.5, 41.3), (101.5, 41.6),
        ])
        reg_direct.extend([
            ("Qin Dynasty", "秦朝", qin_peak, -221, -206, "咸阳", "empire", "Qin_dynasty", "Q7183"),
            ("Minyue", "闽越", minyue, -334, -110, "东冶", "kingdom", "Minyue", "Q837158"),
            ("Dian Kingdom", "滇国", tpl["dian"], -278, -109, "滇池", "kingdom", "Dian_Kingdom", "Q1208982"),
            ("Yelang", "夜郎", tpl["yelang"], -300, -27, "夜郎邑", "kingdom", "Yelang", "Q1151621"),
            ("Xiongnu", "匈奴", xiongnu_210, -240, 48, "龙城", "khaganate", "Xiongnu", "Q188836"),
            ("Donghu", "东胡", tpl["donghu"], -600, -206, "乌桓山", "confederacy", "Donghu_people", "Q1142862"),
            ("Buyeo", "夫余", tpl["buyeo"], -239, 494, "夫余城", "kingdom", "Buyeo", "Q28044"),
            ("Yuezhi", "月氏", tpl["yuezhi_hexi"], -350, -162, "昭武（张掖）", "nomadic-kingdom", "Yuezhi", "Q204797"),
            ("Wusun", "乌孙", tpl["wusun_early"], -300, -162, "敦煌祁连间", "nomadic-kingdom", "Wusun", "Q634420"),
            ("Dayuan", "大宛", tpl["dayuan"], -250, 260, "贵山城", "kingdom", "Dayuan", "Q1059959"),
            ("Kangju", "康居", tpl["kangju"], -250, 320, "卑阗城", "kingdom", "Kangju", "Q1062004"),
            ("Western Qiang", "西羌", tpl["qiang"], -300, 220, "赐支河曲", "tribal-confederacy", "Qiang_people", "Q841362"),
        ])

    elif year == -206:
        reg_direct.extend([
            ("Dian Kingdom", "滇国", tpl["dian"], -278, -109, "滇池", "kingdom", "Dian_Kingdom", "Q1208982"),
            ("Yelang", "夜郎", tpl["yelang"], -300, -27, "夜郎邑", "kingdom", "Yelang", "Q1151621"),
            ("Buyeo", "夫余", tpl["buyeo"], -239, 494, "夫余城", "kingdom", "Buyeo", "Q28044"),
            ("Yuezhi", "月氏", tpl["yuezhi_hexi"], -350, -162, "昭武", "nomadic-kingdom", "Yuezhi", "Q204797"),
            ("Wusun", "乌孙", tpl["wusun_early"], -300, -162, "敦煌祁连间", "nomadic-kingdom", "Wusun", "Q634420"),
            ("Dayuan", "大宛", tpl["dayuan"], -250, 260, "贵山城", "kingdom", "Dayuan", "Q1059959"),
            ("Kangju", "康居", tpl["kangju"], -250, 320, "卑阗城", "kingdom", "Kangju", "Q1062004"),
            ("Western Qiang", "西羌", tpl["qiang"], -300, 220, "赐支河曲", "tribal-confederacy", "Qiang_people", "Q841362"),
        ])

    elif year == -200:
        whan = clean_poly(query_clio_poly(pols, "Han Dynasty", -200).intersection(land_ea).difference(tpl["dongou"]), tol=0.02)
        nanyue = clean_poly(query_clio_poly(pols, "Nanyue", -200).intersection(land_ea), tol=0.02)
        minyue = clean_poly(query_clio_poly(pols, "Minyue", -200).intersection(land_ea).difference(tpl["dongou"]), tol=0.02)
        xiongnu_200 = clean_poly(unary_union([query_clio_poly(pols, "Xiongnu", -200), tpl["hexi"]]).difference(whan).difference(tpl["wusun_ili"]), tol=0.025)
        yuezhi_mig = clean_poly(query_clio_poly(pols, "Yuezhi", -200).difference(tpl["wusun_ili"]).difference(tpl["protectorate_full"]).difference(xiongnu_200), tol=0.025)
        reg_direct.extend([
            ("Western Han", "西汉", whan, -202, 8, "长安", "empire", "Western_Han", "Q7209"),
            ("Nanyue", "南越国", nanyue, -204, -111, "番禺", "kingdom", "Nanyue", "Q827040"),
            ("Minyue", "闽越", minyue, -334, -110, "东冶", "kingdom", "Minyue", "Q837158"),
            ("Dong'ou", "东瓯", tpl["dongou"], -192, -138, "东瓯城", "kingdom", "Dong%27ou", "Q1241366"),
            ("Dian Kingdom", "滇国", tpl["dian"], -278, -109, "滇池", "kingdom", "Dian_Kingdom", "Q1208982"),
            ("Yelang", "夜郎", tpl["yelang"], -300, -27, "夜郎邑", "kingdom", "Yelang", "Q1151621"),
            ("Xiongnu", "匈奴", xiongnu_200, -209, 48, "龙城（单于庭）", "khaganate", "Xiongnu", "Q188836"),
            ("Wusun", "乌孙", tpl["wusun_ili"], -177, 430, "赤谷城", "kingdom", "Wusun", "Q634420"),
            ("Dayuan", "大宛", tpl["dayuan"], -250, 260, "贵山城", "kingdom", "Dayuan", "Q1059959"),
            ("Kangju", "康居", tpl["kangju"], -250, 320, "卑阗城", "kingdom", "Kangju", "Q1062004"),
            ("Buyeo", "夫余", tpl["buyeo"], -239, 494, "夫余城", "kingdom", "Buyeo", "Q28044"),
            ("Western Qiang", "西羌", tpl["qiang"], -300, 220, "赐支河曲", "tribal-confederacy", "Qiang_people", "Q841362"),
        ])
        if not yuezhi_mig.is_empty:
            reg_direct.append(("Greater Yuezhi", "大月氏", yuezhi_mig, -177, 30, "伊犁—妫水迁徙带", "nomadic-kingdom", "Yuezhi", "Q204797"))
        oasis_subject = "匈奴僮仆都尉"
        f_tp = make_feat(
            "Xiongnu Slave Commandant", "匈奴僮仆都尉辖区", tpl["xiongnu_tongpu"],
            -177, -60, capital="焉耆危须间", ptype="protectorate", ctrl="protectorate",
            subject_to="匈奴", region="Western Regions", wiki="Xiongnu", wikidata="Q188836",
        )
        if f_tp:
            reg_overlay.append(f_tp)

    elif year == -140:
        whan = clean_poly(han_core_early.intersection(land_ea).difference(tpl["dongou"]), tol=0.02)
        nanyue = clean_poly(query_clio_poly(pols, "Nanyue", -140).intersection(land_ea), tol=0.02)
        minyue = clean_poly(query_clio_poly(pols, "Minyue", -120).intersection(land_ea).difference(tpl["dongou"]), tol=0.02)
        xiongnu_140 = clean_poly(unary_union([query_clio_poly(pols, "Xiongnu", -140), tpl["hexi"]]).difference(whan).difference(tpl["wusun_ili"]), tol=0.025)
        reg_direct.extend([
            ("Western Han", "西汉", whan, -202, 8, "长安", "empire", "Western_Han", "Q7209"),
            ("Nanyue", "南越国", nanyue, -204, -111, "番禺", "kingdom", "Nanyue", "Q827040"),
            ("Minyue", "闽越", minyue, -334, -110, "东冶", "kingdom", "Minyue", "Q837158"),
            ("Dong'ou", "东瓯", tpl["dongou"], -192, -138, "东瓯城", "kingdom", "Dong%27ou", "Q1241366"),
            ("Dian Kingdom", "滇国", tpl["dian"], -278, -109, "滇池", "kingdom", "Dian_Kingdom", "Q1208982"),
            ("Yelang", "夜郎", tpl["yelang"], -300, -27, "夜郎邑", "kingdom", "Yelang", "Q1151621"),
            ("Xiongnu", "匈奴", xiongnu_140, -209, 48, "龙城（单于庭）", "khaganate", "Xiongnu", "Q188836"),
            ("Wusun", "乌孙", tpl["wusun_ili"], -177, 430, "赤谷城", "kingdom", "Wusun", "Q634420"),
            ("Dayuan", "大宛", tpl["dayuan"], -250, 260, "贵山城", "kingdom", "Dayuan", "Q1059959"),
            ("Kangju", "康居", tpl["kangju"], -250, 320, "卑阗城", "kingdom", "Kangju", "Q1062004"),
            ("Buyeo", "夫余", tpl["buyeo"], -239, 494, "夫余城", "kingdom", "Buyeo", "Q28044"),
            ("Western Qiang", "西羌", tpl["qiang"], -300, 220, "赐支河曲", "tribal-confederacy", "Qiang_people", "Q841362"),
        ])
        oasis_subject = "匈奴僮仆都尉"
        f_tp = make_feat(
            "Xiongnu Slave Commandant", "匈奴僮仆都尉辖区", tpl["xiongnu_tongpu"],
            -177, -60, capital="焉耆危须间", ptype="protectorate", ctrl="protectorate",
            subject_to="匈奴", region="Western Regions", wiki="Xiongnu", wikidata="Q188836",
        )
        if f_tp:
            reg_overlay.append(f_tp)

    elif year == -115:
        # 前121霍去病夺河西走廊，断匈奴右臂；南越(-111)、闽越(-110)、卫满朝鲜(-108)尚存
        whan_115 = clean_poly(unary_union([
            han_core_early,
            tpl["hexi"],
            tpl["qin_hetao"],
        ]).intersection(land_ea), tol=0.02)
        nanyue = clean_poly(query_clio_poly(pols, "Nanyue", -115).intersection(land_ea).difference(whan_115), tol=0.02)
        minyue = clean_poly(query_clio_poly(pols, "Minyue", -115).intersection(land_ea).difference(whan_115), tol=0.02)
        xiongnu_115 = clean_poly(query_clio_poly(pols, "Xiongnu", -100).difference(whan_115).difference(tpl["wusun_ili"]).difference(tpl["protectorate_full"]), tol=0.025)
        reg_direct.extend([
            ("Western Han", "西汉", whan_115, -202, 8, "长安", "empire", "Western_Han", "Q7209"),
            ("Nanyue", "南越国", nanyue, -204, -111, "番禺", "kingdom", "Nanyue", "Q827040"),
            ("Minyue", "闽越", minyue, -334, -110, "东冶", "kingdom", "Minyue", "Q837158"),
            ("Dian Kingdom", "滇国", tpl["dian"], -278, -109, "滇池", "kingdom", "Dian_Kingdom", "Q1208982"),
            ("Yelang", "夜郎", tpl["yelang"], -300, -27, "夜郎邑", "kingdom", "Yelang", "Q1151621"),
            ("Xiongnu", "匈奴", xiongnu_115, -209, 48, "漠北单于庭", "khaganate", "Xiongnu", "Q188836"),
            ("Wusun", "乌孙", tpl["wusun_ili"], -177, 430, "赤谷城", "kingdom", "Wusun", "Q634420"),
            ("Dayuan", "大宛", tpl["dayuan"], -250, 260, "贵山城", "kingdom", "Dayuan", "Q1059959"),
            ("Kangju", "康居", tpl["kangju"], -250, 320, "卑阗城", "kingdom", "Kangju", "Q1062004"),
            ("Wuhuan", "乌桓", tpl["wuhuan"], -206, 207, "乌桓山", "confederacy", "Wuhuan", "Q854099"),
            ("Buyeo", "夫余", tpl["buyeo"], -239, 494, "夫余城", "kingdom", "Buyeo", "Q28044"),
            ("Western Qiang", "西羌", tpl["qiang"], -300, 220, "赐支河曲", "tribal-confederacy", "Qiang_people", "Q841362"),
        ])

    elif year == -100:
        # 汉武帝平南越、灭卫满朝鲜置汉四郡、开西南夷、贰师伐大宛后轮台渠犁屯田
        whan_100 = clean_poly(unary_union([
            han_with_south.intersection(east_of_yumen),
            tpl["hexi"],
            korea_4_cmd,
            tpl["hainan"],
        ]).intersection(land_ea), tol=0.02)
        xiongnu_100 = clean_poly(query_clio_poly(pols, "Xiongnu", -100).difference(whan_100).difference(tpl["wusun_ili"]).difference(tpl["protectorate_full"]), tol=0.025)
        reg_direct.extend([
            ("Western Han", "西汉", whan_100, -202, 8, "长安", "empire", "Western_Han", "Q7209"),
            ("Xiongnu", "匈奴", xiongnu_100, -209, 48, "漠北单于庭", "khaganate", "Xiongnu", "Q188836"),
            ("Wusun", "乌孙", tpl["wusun_ili"], -177, 430, "赤谷城", "kingdom", "Wusun", "Q634420"),
            ("Dayuan", "大宛", tpl["dayuan"], -250, 260, "贵山城", "kingdom", "Dayuan", "Q1059959"),
            ("Kangju", "康居", tpl["kangju"], -250, 320, "卑阗城", "kingdom", "Kangju", "Q1062004"),
            ("Wuhuan", "乌桓", tpl["wuhuan"], -206, 207, "乌桓山", "confederacy", "Wuhuan", "Q854099"),
            ("Buyeo", "夫余", tpl["buyeo"], -239, 494, "夫余城", "kingdom", "Buyeo", "Q28044"),
            ("Western Qiang", "西羌", tpl["qiang"], -300, 220, "赐支河曲", "tribal-confederacy", "Qiang_people", "Q841362"),
        ])

    elif year in (-60, -1):
        # 神爵二年(-60)郑吉始任西域都护，治乌垒城：东侧为西汉实控郡国，西侧为西域都护府统辖区
        whan_direct = clean_poly(unary_union([
            han_peak_raw.intersection(east_of_yumen),
            tpl["hexi"],
            tpl["hainan"] if year == -60 else Polygon(),
        ]).intersection(land_ea), tol=0.02)
        xn_raw = query_clio_poly(pols, "Xiongnu", year)
        xn_clean = clean_poly(xn_raw.difference(whan_direct).difference(tpl["protectorate_full"]).difference(tpl["wusun_ili"]), tol=0.025)
        xn_ctrl = "tributary" if year == -1 else "direct"
        xn_sub = "西汉" if year == -1 else ""
        reg_direct.extend([
            ("Western Han", "西汉", whan_direct, -202, 8, "长安", "empire", "Western_Han", "Q7209"),
            ("Wusun", "乌孙", tpl["wusun_ili"], -177, 430, "赤谷城", "kingdom", "Wusun", "Q634420"),
            ("Dayuan", "大宛", tpl["dayuan"], -250, 260, "贵山城", "kingdom", "Dayuan", "Q1059959"),
            ("Kangju", "康居", tpl["kangju"], -250, 320, "卑阗城", "kingdom", "Kangju", "Q1062004"),
            ("Buyeo", "夫余", tpl["buyeo"], -239, 494, "夫余城", "kingdom", "Buyeo", "Q28044"),
            ("Western Qiang", "西羌", tpl["qiang"], -300, 220, "赐支河曲", "tribal-confederacy", "Qiang_people", "Q841362"),
        ])
        f_xn = make_feat(
            "Xiongnu", "匈奴（呼韩邪附汉）" if year == -1 else "匈奴", xn_clean,
            -209, 48, capital="单于庭", ptype="khaganate", ctrl=xn_ctrl, subject_to=xn_sub,
            wiki="Xiongnu", wikidata="Q188836",
        )
        if f_xn:
            reg_overlay.append(f_xn)

        oasis_subject = "西域都护府"
        f_prot = make_feat(
            "Protectorate of the Western Regions", "西域都护府",
            clean_poly(tpl["protectorate_full"].difference(whan_direct), tol=0.02),
            -60, 16, capital="乌垒城", ptype="protectorate", ctrl="protectorate",
            subject_to="西汉", region="Western Regions",
            wiki="Protectorate_of_the_Western_Regions", wikidata="Q1194805",
        )
        if f_prot:
            reg_overlay.append(f_prot)

    elif year == 15:
        # 王莽新朝天凤二年：焉耆攻杀都护但钦，西域断绝，匈奴复盛
        xin = clean_poly(unary_union([
            query_clio_poly(pols, "Xin Dynasty", 15).intersection(east_of_yumen),
            tpl["hexi"],
        ]).intersection(land_ea), tol=0.02)
        xn_15 = clean_poly(query_clio_poly(pols, "Xiongnu", 15).difference(xin).difference(tpl["wusun_ili"]).difference(tpl["protectorate_full"]), tol=0.025)
        reg_direct.extend([
            ("Xin Dynasty", "新朝", xin, 9, 23, "常安（长安）", "empire", "Xin_dynasty", "Q504769"),
            ("Xiongnu", "匈奴", xn_15, -209, 48, "单于庭", "khaganate", "Xiongnu", "Q188836"),
            ("Wusun", "乌孙", tpl["wusun_ili"], -177, 430, "赤谷城", "kingdom", "Wusun", "Q634420"),
            ("Dayuan", "大宛", tpl["dayuan"], -250, 260, "贵山城", "kingdom", "Dayuan", "Q1059959"),
            ("Kangju", "康居", tpl["kangju"], -250, 320, "卑阗城", "kingdom", "Kangju", "Q1062004"),
            ("Buyeo", "夫余", tpl["buyeo"], -239, 494, "夫余城", "kingdom", "Buyeo", "Q28044"),
            ("Western Qiang", "西羌", tpl["qiang"], -300, 220, "赐支河曲", "tribal-confederacy", "Qiang_people", "Q841362"),
        ])

    elif year == 40:
        # 东汉光武帝建武十六年：闭玉门关休养生息，莎车王贤称霸西域南道
        ehan_40 = clean_poly(unary_union([
            query_clio_poly(pols, "Han Dynasty", 40).intersection(east_of_yumen),
            tpl["hexi"],
        ]).intersection(land_ea), tol=0.02)
        xn_40 = clean_poly(query_clio_poly(pols, "Xiongnu", 40).difference(ehan_40).difference(tpl["wusun_ili"]).difference(tpl["protectorate_full"]), tol=0.025)
        reg_direct.extend([
            ("Eastern Han", "东汉", ehan_40, 25, 220, "洛阳", "empire", "Eastern_Han", "Q7209"),
            ("Xiongnu", "匈奴", xn_40, -209, 48, "单于庭", "khaganate", "Xiongnu", "Q188836"),
            ("Wusun", "乌孙", tpl["wusun_ili"], -177, 430, "赤谷城", "kingdom", "Wusun", "Q634420"),
            ("Dayuan", "大宛", tpl["dayuan"], -250, 260, "贵山城", "kingdom", "Dayuan", "Q1059959"),
            ("Kangju", "康居", tpl["kangju"], -250, 320, "卑阗城", "kingdom", "Kangju", "Q1062004"),
            ("Buyeo", "夫余", tpl["buyeo"], -239, 494, "夫余城", "kingdom", "Buyeo", "Q28044"),
            ("Western Qiang", "西羌", tpl["qiang"], -300, 220, "赐支河曲", "tribal-confederacy", "Qiang_people", "Q841362"),
        ])
        hegemon_yarkant = True

    elif year == 100:
        # 东汉永元十二年：窦宪破北匈奴、班超任西域都护驻龟兹它乾城、南匈奴内附河套美稷
        ehan_100 = clean_poly(unary_union([
            query_clio_poly(pols, "Han Dynasty", 100).intersection(east_of_yumen),
            tpl["hexi"],
        ]).intersection(land_ea), tol=0.02)
        sxn = clean_poly(query_clio_poly(pols, "Southern Xiongnu", 100), tol=0.02)
        ehan_100 = clean_poly(ehan_100.difference(sxn), tol=0.02)
        nxn = clean_poly(query_clio_poly(pols, "Xiongnu", 100).difference(ehan_100).difference(tpl["protectorate_full"]).difference(tpl["wusun_ili"]), tol=0.025)
        reg_direct.extend([
            ("Eastern Han", "东汉", ehan_100, 25, 220, "洛阳", "empire", "Eastern_Han", "Q7209"),
            ("Northern Xiongnu", "北匈奴", nxn, 48, 155, "金微山北", "khaganate", "Northern_Xiongnu", "Q188836"),
            ("Wusun", "乌孙", tpl["wusun_ili"], -177, 430, "赤谷城", "kingdom", "Wusun", "Q634420"),
            ("Dayuan", "大宛", tpl["dayuan"], -250, 260, "贵山城", "kingdom", "Dayuan", "Q1059959"),
            ("Kangju", "康居", tpl["kangju"], -250, 320, "卑阗城", "kingdom", "Kangju", "Q1062004"),
            ("Buyeo", "夫余", tpl["buyeo"], -239, 494, "夫余城", "kingdom", "Buyeo", "Q28044"),
            ("Western Qiang", "西羌", tpl["qiang"], -300, 220, "赐支河曲", "tribal-confederacy", "Qiang_people", "Q841362"),
        ])
        f_sxn = make_feat(
            "Southern Xiongnu", "南匈奴", sxn, 48, 216, capital="美稷",
            ptype="tributary-khaganate", ctrl="tributary", subject_to="东汉",
            wiki="Southern_Xiongnu", wikidata="Q1193532",
        )
        if f_sxn:
            reg_overlay.append(f_sxn)

        oasis_subject = "西域都护府"
        f_prot = make_feat(
            "Protectorate of the Western Regions", "西域都护府",
            clean_poly(tpl["protectorate_full"].difference(ehan_100), tol=0.02),
            91, 107, capital="它乾城（龟兹）", ptype="protectorate", ctrl="protectorate",
            subject_to="东汉", region="Western Regions",
            wiki="Protectorate_of_the_Western_Regions", wikidata="Q1194805",
        )
        if f_prot:
            reg_overlay.append(f_prot)

    elif year == 150:
        # 东汉和平元年：班勇复通西域后改设西域长史府屯柳中；北方檀石槐鲜卑汗国崛起
        ehan_150 = clean_poly(unary_union([
            query_clio_poly(pols, "Han Dynasty", 150).intersection(east_of_yumen),
            tpl["hexi"],
        ]).intersection(land_ea), tol=0.02)
        xianbei_150 = clean_poly(unary_union([
            query_clio_poly(pols, "Xianbei", 197),  # 檀石槐统一漠北东西万四千里轮廓
        ]).difference(ehan_150).difference(tpl["protectorate_changshi"]).difference(tpl["wusun_ili"]).difference(tpl["buyeo"]), tol=0.025)
        reg_direct.extend([
            ("Eastern Han", "东汉", ehan_150, 25, 220, "洛阳", "empire", "Eastern_Han", "Q7209"),
            ("Xianbei Confederation", "鲜卑（檀石槐汗国）", xianbei_150, 147, 181, "弹汗山", "khaganate", "Xianbei_state", "Q1368098"),
            ("Wusun", "乌孙", tpl["wusun_ili"], -177, 430, "赤谷城", "kingdom", "Wusun", "Q634420"),
            ("Dayuan", "大宛", tpl["dayuan"], -250, 260, "贵山城", "kingdom", "Dayuan", "Q1059959"),
            ("Kangju", "康居", tpl["kangju"], -250, 320, "卑阗城", "kingdom", "Kangju", "Q1062004"),
            ("Buyeo", "夫余", tpl["buyeo"], -239, 494, "夫余城", "kingdom", "Buyeo", "Q28044"),
            ("Western Qiang", "西羌", tpl["qiang"], -300, 220, "赐支河曲", "tribal-confederacy", "Qiang_people", "Q841362"),
        ])
        oasis_subject = "西域长史府"
        f_cs = make_feat(
            "Chief Officialdom of the Western Regions", "西域长史府",
            clean_poly(tpl["protectorate_changshi"].difference(ehan_150), tol=0.02),
            123, 175, capital="柳中", ptype="protectorate", ctrl="protectorate",
            subject_to="东汉", region="Western Regions",
            wiki="Chief_Official_of_the_Western_Regions", wikidata="Q1194805",
        )
        if f_cs:
            reg_overlay.append(f_cs)

    elif year == 200:
        # 建安五年（200）官渡之战汉末州牧群雄割据（基于东汉总陆域按山川州界自然切分，并彻底移除失真的西域长史府残块）
        ehan_land = clean_poly(unary_union([
            query_clio_poly(pols, "Han Dynasty", 200).intersection(east_of_yumen),
            query_clio_poly(pols, "Cao Cao", 200),
            tpl["hexi"],
        ]).intersection(land_ea), tol=0.02)

        warlord_zones = [
            ("Yuan Shao", "袁绍", 191, 207, "邺城", "Yuan_Shao", "Q313333", smooth_ctrl_poly([
                (110.2, 35.4), (110.5, 40.8), (119.5, 41.2), (121.2, 37.8), (118.2, 36.2), (114.6, 35.2),
            ])),
            ("Gongsun Du", "公孙度（辽东）", 189, 238, "襄平", "Gongsun_Du", "Q706798", smooth_ctrl_poly([
                (119.3, 39.5), (120.2, 42.8), (128.8, 42.5), (127.8, 37.4), (121.0, 38.5),
            ])),
            ("Cao Cao", "曹操（奉汉帝）", 196, 220, "许昌", "Cao_Cao", "Q171328", smooth_ctrl_poly([
                (109.8, 33.4), (110.2, 35.5), (114.8, 35.3), (118.5, 36.4), (122.8, 37.8),
                (121.8, 32.5), (116.5, 31.8), (113.2, 32.8),
            ])),
            ("Sun Quan", "孙权（江东）", 195, 229, "吴（京口）", "Sun_Quan", "Q204077", smooth_ctrl_poly([
                (115.6, 29.8), (116.5, 32.4), (122.5, 32.5), (122.5, 24.5), (116.8, 24.5), (114.8, 26.8),
            ])),
            ("Liu Biao", "刘表（荆州）", 190, 208, "襄阳", "Liu_Biao", "Q334101", smooth_ctrl_poly([
                (108.8, 25.2), (109.6, 33.2), (113.5, 33.0), (116.0, 30.2), (114.8, 25.3),
            ])),
            ("Zhang Lu", "张鲁（汉中）", 191, 215, "南郑", "Zhang_Lu", "Q559560", smooth_ctrl_poly([
                (105.6, 32.2), (106.2, 34.0), (109.8, 33.8), (109.5, 31.8),
            ])),
            ("Ma Teng & Han Sui", "马腾·韩遂（凉州）", 189, 214, "姑臧 / 金城", "Ma_Teng", "Q470107", smooth_ctrl_poly([
                (93.5, 38.5), (94.0, 41.8), (106.8, 39.5), (109.8, 35.2), (109.6, 33.8), (104.2, 33.8), (99.0, 37.2),
            ])),
            ("Liu Zhang", "刘璋（益州）", 194, 214, "成都", "Liu_Zhang_(warlord)", "Q468724", smooth_ctrl_poly([
                (99.5, 22.8), (101.8, 32.8), (106.0, 32.6), (109.6, 31.8), (108.8, 25.8), (104.8, 22.8),
            ])),
            ("Shi Xie", "士燮（交州）", 187, 226, "龙编 / 广信", "Shi_Xie", "Q715416", smooth_ctrl_poly([
                (104.0, 16.5), (105.0, 25.4), (117.2, 25.2), (117.5, 19.0), (108.5, 16.5),
            ])),
        ]
        claimed_han = Polygon()
        for w_en, w_zh, sy, ey, cap, wk, wd, zone in warlord_zones:
            piece = clean_poly(ehan_land.intersection(zone).difference(claimed_han), tol=0.02, min_area=0.15)
            if not piece.is_empty:
                claimed_han = unary_union([claimed_han, piece])
                reg_direct.append((w_en, w_zh, piece, sy, ey, cap, "warlord", wk, wd))

        reg_direct.extend([
            ("Wusun", "乌孙", tpl["wusun_ili"], -177, 430, "赤谷城", "kingdom", "Wusun", "Q634420"),
            ("Dayuan", "大宛", tpl["dayuan"], -250, 260, "贵山城", "kingdom", "Dayuan", "Q1059959"),
            ("Kangju", "康居", tpl["kangju"], -250, 320, "卑阗城", "kingdom", "Kangju", "Q1062004"),
            ("Buyeo", "夫余", tpl["buyeo"], -239, 494, "夫余城", "kingdom", "Buyeo", "Q28044"),
            ("Western Qiang", "西羌", tpl["qiang"], -300, 220, "赐支河曲", "tribal-confederacy", "Qiang_people", "Q841362"),
        ])

    # 3. 合并现有全球要素占用的陆地，确保新注入的直辖要素与安息/贵霜/高句丽等零重叠
    occ_list = [make_valid(shape(f["geometry"])).buffer(0) for f in base_feats if f["properties"].get("ctrl", "direct") == "direct"]
    occupied = make_valid(unary_union([x for x in occ_list if not x.is_empty])) if occ_list else Polygon()
    direct_feats: list[dict] = []
    for en, zh, g, sy, ey, cap, ptype, wk, wd in reg_direct:
        g = make_valid(g).buffer(0)
        # 大国（秦、汉、新、匈奴、楚汉诸侯）优先保留完整边界，周边小部落避让大国
        if en in ("Qin Dynasty", "Western Han", "Xin Dynasty", "Eastern Han", "Cao Cao", "Yuan Shao", "Sun Quan", "Liu Biao", "Liu Zhang"):
            g_clean = clean_poly(g, tol=0.02, min_area=0.05)
        else:
            g_clean = clean_poly(g.difference(occupied), tol=0.02, min_area=0.05)
        if g_clean.is_empty:
            continue
        occupied = make_valid(unary_union([occupied, make_valid(g_clean).buffer(0)]))
        feat = make_feat(en, zh, g_clean, sy, ey, capital=cap, ptype=ptype, ctrl="direct", wiki=wk, wikidata=wd)
        if feat:
            direct_feats.append(feat)

    # 4. 先放实控大国与全球底盘，再放都护/羁縻统辖层，最后放绿洲城郭国（点选时可精准命中绿洲城邦，空白处命中都护府！）
    all_feats = base_feats + direct_feats + reg_overlay
    add_tarim_oasis_states(all_feats, tpl, year, subject_to=oasis_subject, hegemon_yarkant=hegemon_yarkant)
    return all_feats


def update_name_zh() -> dict:
    zh = json.loads(NAME_ZH_PATH.read_text(encoding="utf-8"))
    updates = {
        "Great Yuan": "大宛",
        "Dayuan": "大宛",
        "Qin Dynasty": "秦朝",
        "Western Han": "西汉",
        "Xin Dynasty": "新朝",
        "Eastern Han": "东汉",
        "Western Chu": "西楚",
        "Yong": "雍",
        "Sai": "塞",
        "Zhai": "翟",
        "Henan": "河南",
        "Hán": "韩",
        "Yin": "殷",
        "Dai": "代",
        "Chang-shan": "常山",
        "Jiujiang": "九江",
        "Linjiang": "临江",
        "Jiaodong": "胶东",
        "Jibei": "济北",
        "Liaodong": "辽东",
        "Dong'ou": "东瓯",
        "Baiyue": "岭南百越",
        "Dian Kingdom": "滇国",
        "Yelang": "夜郎",
        "Donghu": "东胡",
        "Wuhuan": "乌桓",
        "Buyeo": "夫余",
        "Western Qiang": "西羌",
        "Greater Yuezhi": "大月氏",
        "Northern Xiongnu": "北匈奴",
        "Xianbei Confederation": "鲜卑",
        "Protectorate of the Western Regions": "西域都护府",
        "Chief Officialdom of the Western Regions": "西域长史府",
        "Xiongnu Slave Commandant": "匈奴僮仆都尉辖区",
        "Loulan": "楼兰",
        "Shanshan": "鄯善",
        "Khotan": "于阗",
        "Yarkant": "莎车",
        "Shule": "疏勒",
        "Kucha": "龟兹",
        "Yanqi": "焉耆",
        "Jushi": "车师",
        "Kangju": "康居",
        "Yuan Shao": "袁绍",
        "Sun Quan": "孙权",
        "Liu Biao": "刘表",
        "Liu Zhang": "刘璋",
        "Zhang Lu": "张鲁",
        "Ma Teng & Han Sui": "马腾·韩遂",
        "Gongsun Du": "公孙度",
        "Shi Xie": "士燮",
        "Indo-Parthians": "印度-帕提亚王国",
        "Kanva Dynasty": "甘婆王朝",
        "Mahameghavahana Dynasty": "摩诃梅伽跋诃那王朝",
        "Trưng sisters": "二征起义",
        "Italian City-States": "意大利城邦",
        "Rhodes": "罗得岛",
        "Molossians": "摩罗西亚",
        "Ankhwennefer": "上埃及起义政权",
    }
    zh.update(updates)
    NAME_ZH_PATH.write_text(json.dumps(zh, ensure_ascii=False, indent=2), encoding="utf-8")
    return zh


def enrich_qin_han_cities() -> None:
    cities = json.loads(CITIES_PATH.read_text(encoding="utf-8"))
    by_name = {c["name"]: c for c in cities}

    # 给广州补充南越王都角色，平壤补充卫满朝鲜与乐浪郡治角色
    if "广州" in by_name:
        roles = by_name["广州"].setdefault("roles", [])
        if not any(r[3] == "南越国" for r in roles):
            roles.append([-204, -111, 3, "南越国"])
    if "平壤" in by_name:
        by_name["平壤"]["from"] = min(by_name["平壤"].get("from", -108), -194)
        roles = by_name["平壤"].setdefault("roles", [])
        if not any("卫满" in r[3] for r in roles):
            roles.insert(0, [-194, -108, 3, "卫满朝鲜"])

    new_cities = [
        # 河西四郡与阳关玉门关
        {"name": "武威", "en": "Wuwei (Guzang)", "lng": 102.64, "lat": 37.93, "from": -121, "base": 2, "roles": [[189, 214, 2, "凉州"], [301, 376, 3, "前凉"]]},
        {"name": "张掖", "en": "Zhangye", "lng": 100.45, "lat": 38.93, "from": -121, "base": 1, "roles": [[-221, -162, 2, "月氏昭武"]]},
        {"name": "酒泉", "en": "Jiuquan", "lng": 98.51, "lat": 39.74, "from": -121, "base": 1, "roles": []},
        {"name": "玉门关", "en": "Yumen Pass", "lng": 93.89, "lat": 40.35, "from": -111, "to": 900, "base": 1, "roles": [[-111, 220, 2, "汉西域门户"]]},
        # 西域都护/长史与绿洲王治
        {"name": "乌垒城", "en": "Wulei", "lng": 84.25, "lat": 41.78, "from": -60, "to": 110, "base": 2, "roles": [[-60, 16, 3, "西域都护府"]]},
        {"name": "龟兹", "en": "Kucha", "lng": 82.96, "lat": 41.72, "from": -221, "to": 1400, "base": 2, "roles": [[91, 107, 3, "东汉西域都护"], [648, 790, 3, "安西都护府"]]},
        {"name": "疏勒", "en": "Kashgar", "lng": 75.99, "lat": 39.47, "from": -221, "base": 2, "roles": [[-221, 650, 2, "疏勒国"]]},
        {"name": "于阗", "en": "Khotan", "lng": 79.92, "lat": 37.11, "from": -221, "base": 2, "roles": [[-221, 1006, 2, "于阗国"]]},
        {"name": "莎车", "en": "Yarkant", "lng": 77.25, "lat": 38.42, "from": -221, "base": 1, "roles": [[33, 61, 2, "莎车称霸"]]},
        {"name": "楼兰", "en": "Loulan", "lng": 89.92, "lat": 40.52, "from": -221, "to": 400, "base": 2, "roles": [[-221, -77, 2, "楼兰国"]]},
        {"name": "扜泥（鄯善）", "en": "Shanshan (Ruoqiang)", "lng": 88.17, "lat": 39.02, "from": -77, "to": 600, "base": 1, "roles": [[-77, 448, 2, "鄯善国"]]},
        {"name": "焉耆", "en": "Yanqi", "lng": 86.56, "lat": 42.06, "from": -221, "to": 1200, "base": 1, "roles": [[-221, 648, 2, "焉耆国"]]},
        {"name": "交河（车师）", "en": "Jiaohe (Turpan)", "lng": 89.06, "lat": 42.95, "from": -221, "to": 1380, "base": 2, "roles": [[-221, 450, 2, "车师前国"], [866, 1283, 3, "高昌回鹘"]]},
        {"name": "柳中", "en": "Liuzhong", "lng": 89.65, "lat": 42.84, "from": 123, "to": 330, "base": 1, "roles": [[123, 175, 3, "西域长史府"]]},
        {"name": "伊吾卢", "en": "Yiwulu (Hami)", "lng": 93.51, "lat": 42.83, "from": 73, "base": 1, "roles": [[73, 220, 2, "宜禾都尉"]]},
        # 西域外围与草原重镇
        {"name": "赤谷城", "en": "Chigu (Wusun)", "lng": 78.15, "lat": 42.32, "from": -165, "to": 430, "base": 2, "roles": [[-165, 430, 3, "乌孙王庭"]]},
        {"name": "贵山城", "en": "Guishan (Khujand/Kasan)", "lng": 71.55, "lat": 41.25, "from": -221, "to": 500, "base": 2, "roles": [[-221, 260, 3, "大宛王治"]]},
        {"name": "单于庭（龙城）", "en": "Longcheng", "lng": 102.85, "lat": 47.45, "from": -209, "to": 91, "base": 2, "roles": [[-209, 89, 3, "匈奴帝国"]]},
        # 秦汉中原重镇补充
        {"name": "彭城", "en": "Pengcheng (Xuzhou)", "lng": 117.18, "lat": 34.26, "from": -221, "base": 2, "roles": [[-206, -202, 3, "西楚都城"]]},
        {"name": "邺城", "en": "Ye", "lng": 114.36, "lat": 36.32, "from": -221, "to": 580, "base": 2, "roles": [[204, 220, 3, "魏公都"], [335, 370, 3, "后赵/前燕"], [534, 577, 3, "东魏/北齐"]]},
        {"name": "许昌", "en": "Xuchang", "lng": 113.85, "lat": 34.03, "from": -221, "base": 1, "roles": [[196, 220, 3, "汉献帝都许"]]},
    ]
    for nc in new_cities:
        if nc["name"] not in by_name:
            cities.append(nc)

    CITIES_PATH.write_text(json.dumps(cities, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"[cities] updated {CITIES_PATH} -> total {len(cities)} historical cities")


def main() -> None:
    print("[1/4] Updating name-zh.json translations & fixing Dayuan ('Great Yuan')...")
    zh_dict = update_name_zh()

    print("[2/4] Building Asia DEM grid & 1:10m coastline templates...")
    lons, lats, elev = build_asia_dem_grid()
    land_ea = load_east_asia_10m_land()
    tpl = build_terrain_templates(lons, lats, elev, land_ea)

    print("[3/4] Loading Cliopatria & generating 14 precision Pre-Qin to Eastern Han slices...")
    pols = load_cliopatria_polities()

    idx_path = ERAS_DIR / "index.json"
    idx = json.loads(idx_path.read_text(encoding="utf-8"))
    existing_map = {e["y"]: e for e in idx["eras"]}

    for y in TARGET_YEARS:
        feats = build_slice(y, pols, tpl, land_ea, zh_dict)
        fn = file_for(y)
        out_p = ERAS_DIR / fn
        out_p.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        existing_map[y] = {"y": y, "f": fn, "l": ERA_LABELS[y]}
        prot_cnt = sum(1 for f in feats if f["properties"].get("ctrl") in ("protectorate", "tributary"))
        print(f"  ✓ {fn.ljust(20)} ({ERA_LABELS[y].ljust(6)}): {len(feats):3d} polities ({prot_cnt} protectorate/tributary) | {out_p.stat().st_size / 1024:.1f} KB")

    idx["credit"] = "历史政权边界数据 © Seshat Global History Databank / Cliopatria (CC BY 4.0) · 秦汉及西域分层疆域与绿洲城邦经《史记》《汉书·西域传》考据并结合 Natural Earth / Terrarium DEM 地形精修"
    idx["eras"] = [existing_map[k] for k in sorted(existing_map.keys())]
    idx_path.write_text(json.dumps(idx, ensure_ascii=False), encoding="utf-8")
    print(f"[index] {idx_path} now has {len(idx['eras'])} slices")

    print("[4/4] Enriching data/cities.json with Hexi Corridor & Western Regions capitals...")
    enrich_qin_han_cities()


if __name__ == "__main__":
    main()
