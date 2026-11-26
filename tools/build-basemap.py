#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/build-basemap.py — 构建同源自托管 1:10m 分级水系自然底图 + Terrarium 高程 DEM 瓦片

产物（输出至 data/basemap/）：
  1. natural-earth.geojson      1:10m 海岸线 / 200m 海深 / 去水库天然湖泊(含古咸海等) / 1:10m 分级水系(精确接管黄河下游) / 15° 经纬网
  2. dem/{z}/{x}/{y}.webp       Terrarium 高程无损 WebP 瓦片（z0–z5 全球全覆盖 + z6–z7 丝路西域与东亚高清区，供 GPU hillshade / color-relief / 3D 地形使用）
  3. relief/{z}/{x}/{y}.webp    z0–z4 512px 基于真实高程设色与多向晕渲的暗色古风兜底瓦片（341 张）

全部数据源来自 Natural Earth 与 AWS Terrarium Elevation Tiles (Public Domain)，缓存在 .tmp-basemap-src/。
用法：python tools/build-basemap.py
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
import zipfile
from pathlib import Path

import numpy as np
import shapefile
from PIL import Image, ImageDraw
from scipy.ndimage import binary_dilation, map_coordinates

Image.MAX_IMAGE_PIXELS = None

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / ".tmp-basemap-src"
DEM_RAW_DIR = CACHE_DIR / "terrarium_raw"
OUT_DIR = ROOT / "data" / "basemap"
RELIEF_DIR = OUT_DIR / "relief"
DEM_OUT_DIR = OUT_DIR / "dem"

# 由 data/geography.json 按年代动态显隐的历史演变湖泊（静态底图不重复绘制现代形态）
TIME_VARYING_LAKE_NAMES = {
    "Hongze Hu",
    "Weishan Hu",
    "Dongting Hu",
    "Poyang Hu",
    "Gaoyou Hu",
    "South Aral Sea",
    "North Aral Sea",
}

# 古咸海 / 乍得湖 / 特斯科科湖（前哥伦布阿兹特克湖岛）在全时间轴 [-221, 1918] 均应取现代干涸前的历史满水岸线
HISTORIC_BASE_LAKE_NAMES = {"Aral Sea", "Lake Chad", "Lake Texcoco"}


def extract_zip(zip_name: str) -> Path:
    src = CACHE_DIR / zip_name
    if not src.exists():
        raise FileNotFoundError(f"Missing cached zip: {src} (run .tmp-basemap-src/fetch_upstream.py first)")
    dst = CACHE_DIR / "unpacked" / src.stem
    if dst.exists() and any(dst.iterdir()):
        return dst
    dst.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(src, "r") as zf:
        zf.extractall(dst)
    return dst


def find_shp(folder: Path) -> Path:
    shps = sorted(folder.rglob("*.shp"))
    if not shps:
        raise FileNotFoundError(f"No .shp found in {folder}")
    return shps[0]


def _perp_dist(p: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    if dx == 0.0 and dy == 0.0:
        return math.hypot(p[0] - a[0], p[1] - a[1])
    t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))


def rdp(pts: list[tuple[float, float]], tol: float) -> list[tuple[float, float]]:
    if tol <= 0.0 or len(pts) <= 2:
        return list(pts)
    n = len(pts)
    keep = bytearray(n)
    keep[0] = 1
    keep[n - 1] = 1
    stack = [(0, n - 1)]
    while stack:
        lo, hi = stack.pop()
        if hi - lo <= 1:
            continue
        a, b = pts[lo], pts[hi]
        max_d = -1.0
        idx = -1
        for i in range(lo + 1, hi):
            d = _perp_dist(pts[i], a, b)
            if d > max_d:
                max_d = d
                idx = i
        if max_d > tol and idx != -1:
            keep[idx] = 1
            stack.append((lo, idx))
            stack.append((idx, hi))
    return [pts[i] for i in range(n) if keep[i]]


def ring_area(ring: list) -> float:
    if len(ring) < 3:
        return 0.0
    s = 0.0
    for i in range(len(ring) - 1):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[i + 1][0], ring[i + 1][1]
        s += x1 * y2 - x2 * y1
    return 0.5 * s


def dedup_and_round(pts: list[tuple[float, float]], decimals: int) -> list[list[float]]:
    out: list[list[float]] = []
    for x, y in pts:
        rx = round(float(x), decimals)
        ry = round(float(y), decimals)
        if not out or out[-1][0] != rx or out[-1][1] != ry:
            out.append([rx, ry])
    return out


def simplify_ring(ring: list, tol: float, decimals: int, min_area: float = 0.0) -> list[list[float]] | None:
    if len(ring) < 4:
        return None
    pts = [(float(p[0]), float(p[1])) for p in ring]
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    if tol > 0.0 and len(pts) > 6:
        mid = len(pts) // 2
        left = rdp(pts[: mid + 1], tol)
        right = rdp(pts[mid:], tol)
        pts = left[:-1] + right
    cleaned = dedup_and_round(pts, decimals)
    if len(cleaned) < 3:
        return None
    if cleaned[0] != cleaned[-1]:
        cleaned.append(list(cleaned[0]))
    if len(cleaned) < 4:
        return None
    if abs(ring_area(cleaned)) <= max(min_area, 1e-9):
        return None
    return cleaned


def simplify_line(line: list, tol: float, decimals: int) -> list[list[float]] | None:
    if len(line) < 2:
        return None
    pts = [(float(p[0]), float(p[1])) for p in line]
    if tol > 0.0 and len(pts) > 2:
        pts = rdp(pts, tol)
    cleaned = dedup_and_round(pts, decimals)
    return cleaned if len(cleaned) >= 2 else None


def clean_polygon_geom(
    geom: dict,
    tol: float,
    decimals: int,
    min_outer_area: float = 0.0,
    polar_opts: tuple[float, int, float] | None = None,
) -> dict | None:
    gtype = geom.get("type")
    coords = geom.get("coordinates") or []
    polys = [coords] if gtype == "Polygon" else (coords if gtype == "MultiPolygon" else [])
    if not polys:
        return None

    kept_polys: list[list[list[list[float]]]] = []
    for poly in polys:
        if not poly:
            continue
        p_tol, p_dec, p_min_a = tol, decimals, min_outer_area
        if polar_opts is not None and poly[0]:
            lats = [float(pt[1]) for pt in poly[0]]
            if min(lats) > 62.0 or max(lats) < -52.0:
                p_tol, p_dec, p_min_a = polar_opts
        outer = simplify_ring(poly[0], p_tol, p_dec, min_area=p_min_a)
        if not outer:
            continue
        holes = []
        for h in poly[1:]:
            ch = simplify_ring(h, p_tol, p_dec, min_area=0.0)
            if ch:
                holes.append(ch)
        kept_polys.append([outer] + holes)

    if not kept_polys:
        return None
    if len(kept_polys) == 1:
        return {"type": "Polygon", "coordinates": kept_polys[0]}
    return {"type": "MultiPolygon", "coordinates": kept_polys}


def is_in_eurasia_focus(bbox: list[float] | tuple[float, ...]) -> bool:
    return bbox[2] >= 50.0 and bbox[0] <= 142.0 and bbox[3] >= 12.0 and bbox[1] <= 56.0


def clip_yellow_river_downstream(coords: list) -> tuple[list[list], list[list]]:
    """
    仅在荥阳桃花峪/广武山 [113.498, 34.965] 截断黄河现代下游（保留河套及晋陕峡谷全段），
    由 data/geography.json 无缝接管历代黄河四道；同时返回现代 1855 现行道精确坐标供下游脚本复用。
    """
    kept_segments: list[list] = []
    modern_downstream: list[list] = []
    cur_keep: list = []
    cur_mod: list = []
    for pt in coords:
        lon, lat = float(pt[0]), float(pt[1])
        is_lower_huang = lon > 113.50 and lat < 39.2
        if is_lower_huang:
            cur_mod.append([round(lon, 3), round(lat, 3)])
            if cur_keep:
                # 把分水点本身也纳入保留段末端，保证与 geography.json 零缝隙衔接
                cur_keep.append([113.498, 34.965])
                if len(cur_keep) >= 2:
                    kept_segments.append(cur_keep)
                cur_keep = []
        else:
            if cur_mod:
                cur_mod.append([round(lon, 3), round(lat, 3)])
                if len(cur_mod) >= 2:
                    modern_downstream.append(cur_mod)
                cur_mod = []
            cur_keep.append(pt)
    if len(cur_keep) >= 2:
        kept_segments.append(cur_keep)
    if len(cur_mod) >= 2:
        modern_downstream.append(cur_mod)
    return kept_segments, modern_downstream


def build_graticules() -> list[dict]:
    feats: list[dict] = []
    for lon in range(-165, 181, 15):
        coords = [[round(float(lon), 1), round(float(lat), 1)] for lat in range(-80, 81, 5)]
        feats.append({"type": "Feature", "properties": {"k": "grat"}, "geometry": {"type": "LineString", "coordinates": coords}})
    for lat in range(-75, 76, 15):
        coords = [[round(float(lon), 1), round(float(lat), 1)] for lon in range(-180, 181, 5)]
        feats.append({"type": "Feature", "properties": {"k": "grat"}, "geometry": {"type": "LineString", "coordinates": coords}})
    return feats


def build_vector_geojson() -> list[dict]:
    features: list[dict] = []

    # 1. ne_10m_land (逐子多边形判定：中低纬保持 1:10m 精细海岸线，高纬极区北极群岛/格陵兰/南极适当简化控体积)
    land_shp = find_shp(extract_zip("ne_10m_land.zip"))
    land_raw: list[dict] = []
    with shapefile.Reader(str(land_shp)) as sf:
        for sr in sf.iterShapeRecords():
            if sr.shape.shapeType == shapefile.NULL or not sr.shape.points:
                continue
            geom = sr.shape.__geo_interface__
            land_raw.append(geom)
            cg = clean_polygon_geom(
                geom,
                tol=0.018,
                decimals=3,
                min_outer_area=0.004,
                polar_opts=(0.065, 2, 0.06),
            )
            if cg:
                features.append({"type": "Feature", "properties": {"k": "land"}, "geometry": cg})
    print(f"[vec] 10m land features: {sum(1 for f in features if f['properties']['k'] == 'land')}")

    # 2. ne_10m_bathymetry_K_200
    k200_shp = find_shp(extract_zip("ne_10m_bathymetry_K_200.zip"))
    with shapefile.Reader(str(k200_shp)) as sf:
        for sr in sf.iterShapeRecords():
            if sr.shape.shapeType == shapefile.NULL or not sr.shape.points:
                continue
            cg = clean_polygon_geom(sr.shape.__geo_interface__, tol=0.14, decimals=2, min_outer_area=0.35)
            if cg:
                features.append({"type": "Feature", "properties": {"k": "shelf"}, "geometry": cg})
    print(f"[vec] shelf/K_200 features: {sum(1 for f in features if f['properties']['k'] == 'shelf')}")

    # 3. ne_10m_lakes (剔除全部现代水库 Reservoir + 剔除由 geography.json 动态接管的历史演变湖泊)
    lakes_shp = find_shp(extract_zip("ne_10m_lakes.zip"))
    removed_reservoirs = 0
    with shapefile.Reader(str(lakes_shp)) as sf:
        fields = [f[0].lower() for f in sf.fields[1:]]
        sr_idx = fields.index("scalerank")
        fc_idx = fields.index("featurecla")
        nm_idx = fields.index("name")
        zh_idx = fields.index("name_zh") if "name_zh" in fields else -1
        for sr in sf.iterShapeRecords():
            if sr.shape.shapeType == shapefile.NULL or not sr.shape.points:
                continue
            fcla = str(sr.record[fc_idx] or "")
            if "reservoir" in fcla.lower():
                removed_reservoirs += 1
                continue
            name = str(sr.record[nm_idx] or "").strip()
            if name in TIME_VARYING_LAKE_NAMES:
                continue
            rank = float(sr.record[sr_idx]) if sr.record[sr_idx] is not None else 0.0
            in_focus = bool(sr.shape.bbox and is_in_eurasia_focus(sr.shape.bbox))
            max_rank = 8.0 if in_focus else 5.0
            if rank > max_rank:
                continue
            tol = 0.01 if in_focus else 0.02
            min_a = 0.0015 if in_focus else 0.008
            cg = clean_polygon_geom(sr.shape.__geo_interface__, tol=tol, decimals=3, min_outer_area=min_a)
            if cg:
                props: dict = {"k": "lake", "sr": int(round(rank))}
                zh_name = str(sr.record[zh_idx] or "").strip() if zh_idx >= 0 else ""
                if zh_name and in_focus and rank <= 6:
                    props["nz"] = zh_name
                features.append({"type": "Feature", "properties": props, "geometry": cg})

    # 3b. 注入 ne_10m_lakes_historic 中的古咸海 / 古乍得湖 / 阿兹特克特斯科科湖（罗布泊放入 geography.json 带中文古名注记）
    hist_lakes_shp = find_shp(extract_zip("ne_10m_lakes_historic.zip"))
    lop_nur_geom = None
    with shapefile.Reader(str(hist_lakes_shp)) as sf:
        fields = [f[0].lower() for f in sf.fields[1:]]
        nm_idx = fields.index("name")
        for sr in sf.iterShapeRecords():
            if sr.shape.shapeType == shapefile.NULL or not sr.shape.points:
                continue
            name = str(sr.record[nm_idx] or "").strip()
            cg = clean_polygon_geom(sr.shape.__geo_interface__, tol=0.008, decimals=3, min_outer_area=0.0)
            if not cg:
                continue
            if name == "Lop Nur":
                lop_nur_geom = cg
            elif name in HISTORIC_BASE_LAKE_NAMES:
                zh_map = {"Aral Sea": "咸海（雷翥海）", "Lake Chad": "古乍得湖", "Lake Texcoco": "特斯科科湖"}
                features.append({
                    "type": "Feature",
                    "properties": {"k": "lake", "sr": 1, "nz": zh_map.get(name, "")},
                    "geometry": cg,
                })
    if lop_nur_geom:
        (CACHE_DIR / "lop_nur_10m.json").write_text(json.dumps(lop_nur_geom, ensure_ascii=False), encoding="utf-8")
    print(f"[vec] 10m lake features: {sum(1 for f in features if f['properties']['k'] == 'lake')} (removed {removed_reservoirs} modern reservoirs)")

    # 4. ne_10m_rivers_lake_centerlines (分级天然水系 + 仅精确截断黄河桃花峪以下现代河段与苏北现代入海水道)
    rivers_shp = find_shp(extract_zip("ne_10m_rivers_lake_centerlines.zip"))
    huang_1855_lines: list[list] = []
    with shapefile.Reader(str(rivers_shp)) as sf:
        fields = [f[0].lower() for f in sf.fields[1:]]
        sr_idx = fields.index("scalerank")
        fc_idx = fields.index("featurecla")
        nm_idx = fields.index("name")
        zh_idx = fields.index("name_zh") if "name_zh" in fields else -1
        for sr in sf.iterShapeRecords():
            if sr.shape.shapeType == shapefile.NULL or not sr.shape.points:
                continue
            fcla = str(sr.record[fc_idx] or "")
            if fcla == "Lake Centerline" or "reservoir" in fcla.lower():
                continue
            name = str(sr.record[nm_idx] or "").strip()
            if name in ("Dam", "Hudi"):
                continue
            rank = float(sr.record[sr_idx]) if sr.record[sr_idx] is not None else 5.0
            in_focus = bool(sr.shape.bbox and is_in_eurasia_focus(sr.shape.bbox))
            max_rank = 9.0 if in_focus else 5.0
            if rank > max_rank:
                continue

            geom = sr.shape.__geo_interface__
            gtype = geom.get("type")
            lines = [geom["coordinates"]] if gtype == "LineString" else (geom["coordinates"] if gtype == "MultiLineString" else [])
            out_lines: list[list[list[float]]] = []
            tol = 0.009 if in_focus else 0.022
            for line in lines:
                if name == "Huang":
                    kept_segs, mod_segs = clip_yellow_river_downstream(line)
                    huang_1855_lines.extend(mod_segs)
                    for sub in kept_segs:
                        cl = simplify_line(sub, tol=0.008, decimals=3)
                        if cl:
                            out_lines.append(cl)
                else:
                    cl = simplify_line(line, tol=tol, decimals=3)
                    if cl:
                        out_lines.append(cl)
            if not out_lines:
                continue
            out_geom = {"type": "LineString", "coordinates": out_lines[0]} if len(out_lines) == 1 else {"type": "MultiLineString", "coordinates": out_lines}
            props = {"k": "river", "sr": max(1, int(round(rank)))}
            zh_name = str(sr.record[zh_idx] or "").strip() if zh_idx >= 0 else ""
            if zh_name and in_focus:
                props["nz"] = zh_name
            features.append({"type": "Feature", "properties": props, "geometry": out_geom})

    if huang_1855_lines:
        # 拼接桃花峪 [113.498, 34.965] 至渤海利津 [119.235, 37.777] 全部被裁下游段，按经度自西向东排序去重，确保零断头
        merged_1855: list[list[float]] = [[113.498, 34.965]]
        all_pts = [pt for seg in huang_1855_lines for pt in seg]
        # 按段首尾经度方向统一为自西向东
        ordered_segs = []
        for seg in huang_1855_lines:
            s = list(seg) if seg[0][0] <= seg[-1][0] else list(reversed(seg))
            ordered_segs.append(s)
        ordered_segs.sort(key=lambda s: s[0][0])
        for s in ordered_segs:
            for pt in s:
                if pt[0] > merged_1855[-1][0] - 0.02 and pt != merged_1855[-1]:
                    merged_1855.append(pt)
        (CACHE_DIR / "huang_1855_10m.json").write_text(json.dumps(merged_1855, ensure_ascii=False), encoding="utf-8")

    print(f"[vec] 10m river features: {sum(1 for f in features if f['properties']['k'] == 'river')}")

    # 5. 15° graticules
    grat_feats = build_graticules()
    features.extend(grat_feats)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    vec_path = OUT_DIR / "natural-earth.geojson"
    fc = {"type": "FeatureCollection", "features": features}
    vec_bytes = json.dumps(fc, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    vec_path.write_bytes(vec_bytes)
    print(f"[out] {vec_path} -> {len(vec_bytes) / (1024 * 1024):.2f} MB ({len(features)} features)")
    return land_raw


def decode_terrarium_png(path: Path) -> np.ndarray:
    with Image.open(path) as im:
        rgb = np.asarray(im.convert("RGB"), dtype=np.float32)
    return (rgb[..., 0] * 256.0 + rgb[..., 1] + rgb[..., 2] / 256.0) - 32768.0


def encode_terrarium_rgb(elev: np.ndarray) -> np.ndarray:
    v = np.clip(elev + 32768.0, 0.0, 65535.996)
    r = np.floor(v / 256.0)
    rem = v - r * 256.0
    g = np.floor(rem)
    b = np.floor((rem - g) * 256.0)
    return np.stack([r, g, b], axis=-1).astype(np.uint8)


def build_dem_webp_tiles(land_mask_4096: np.ndarray) -> np.ndarray:
    """
    将缓存的 Terrarium 高程 PNG 转换为自托管无损 WebP：
    - 海洋像素（经适度海岸缓冲后的非陆地区）压平为 0m（保留吐鲁番/死海等陆地负海拔盆地），
      陆地按缩放级做温和整数米量化（z0..5: 8m，z6..7: 4m），大幅压缩仓库体积而无视觉/坡度损失。
    - z0..z4：全球 341 张
    - z5：全球 1024 张全覆盖（陆地及近海取原生 z5，远洋深海由 z4 插值补齐并压平为 0m，零 404 且单块仅 ~0.1 KB）
    - z6 (x=41..56, y=18..29) & z7 (x=86..111, y=40..56)：丝路西域、中亚与中国高清高程瓦片
    同时返回原始未压平的全球 z4 高程矩阵 (4096x4096 Web Mercator) 供生成含深海等深色的暗色晕渲兜底图使用。
    """
    if DEM_OUT_DIR.exists():
        shutil.rmtree(DEM_OUT_DIR)
    DEM_OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 给陆地掩膜外扩 ~3 像素（4096 栅格下约 25-30 km 海岸缓冲），防止海岸线边缘梯度被截断
    keep_mask_4096 = binary_dilation(land_mask_4096, iterations=3)

    total_files = 0
    total_bytes = 0

    def tile_keep_mask(z: int, x: int, y: int) -> np.ndarray:
        """从 4096x4096 墨卡托陆地缓冲掩膜采样当前 (z, x, y) 256x256 瓦片对应区域"""
        m_size = keep_mask_4096.shape[0]
        n = 1 << z
        u = ((x + (np.arange(256, dtype=np.float32) + 0.5) / 256.0) / n) * m_size
        v = ((y + (np.arange(256, dtype=np.float32) + 0.5) / 256.0) / n) * m_size
        ix = np.clip(u.astype(np.int32), 0, m_size - 1)
        iy = np.clip(v.astype(np.int32), 0, m_size - 1)
        return keep_mask_4096[iy[:, None], ix[None, :]]

    def compress_dem_rgb(elev: np.ndarray, z: int, x: int, y: int) -> np.ndarray:
        mask = tile_keep_mask(z, x, y)
        step = 8.0 if z <= 5 else 4.0
        quant = np.rint(elev / step) * step
        out_elev = np.where(mask, quant, 0.0)
        return encode_terrarium_rgb(out_elev)

    def save_lossless_webp(rgb: np.ndarray, dst: Path) -> None:
        nonlocal total_files, total_bytes
        dst.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(rgb, mode="RGB").save(dst, format="WEBP", lossless=True, quality=90, method=4)
        total_files += 1
        total_bytes += dst.stat().st_size

    # z0..z4 global + stitch raw z4 elevation grid (保留深海真实水深供 relief 使用)
    z4_grid = np.zeros((16 * 256, 16 * 256), dtype=np.float32)
    z4_tiles: dict[tuple[int, int], np.ndarray] = {}

    for z in range(0, 5):
        n = 1 << z
        for x in range(n):
            for y in range(n):
                src = DEM_RAW_DIR / str(z) / str(x) / f"{y}.png"
                elev = decode_terrarium_png(src)
                save_lossless_webp(compress_dem_rgb(elev, z, x, y), DEM_OUT_DIR / str(z) / str(x) / f"{y}.webp")
                if z == 4:
                    z4_tiles[(x, y)] = elev
                    z4_grid[y * 256 : (y + 1) * 256, x * 256 : (x + 1) * 256] = elev
        print(f"[dem] z={z} converted ({n * n} tiles)", flush=True)

    # z5 full 32x32 global (zero 404s anywhere on Earth; 纯海瓦片压平后仅 ~0.1 KB)
    sub_idx = (np.arange(256, dtype=np.float32) + 0.5) * 0.5 - 0.5
    for x in range(32):
        for y in range(32):
            src = DEM_RAW_DIR / "5" / str(x) / f"{y}.png"
            dst = DEM_OUT_DIR / "5" / str(x) / f"{y}.webp"
            if src.exists():
                elev = decode_terrarium_png(src)
                save_lossless_webp(compress_dem_rgb(elev, 5, x, y), dst)
            else:
                parent = z4_tiles[(x >> 1, y >> 1)]
                ox = 128.0 if (x & 1) else 0.0
                oy = 128.0 if (y & 1) else 0.0
                gy = np.broadcast_to((oy + sub_idx)[:, None], (256, 256))
                gx = np.broadcast_to((ox + sub_idx)[None, :], (256, 256))
                up_elev = map_coordinates(parent, np.stack([gy, gx], axis=0), order=1, mode="nearest", prefilter=False)
                save_lossless_webp(compress_dem_rgb(up_elev, 5, x, y), dst)
    print("[dem] z=5 converted (1024 global tiles)", flush=True)

    # z6 & z7 Asia / Silk Road HD DEM tiles
    for z in (6, 7):
        z_src = DEM_RAW_DIR / str(z)
        cnt = 0
        if z_src.exists():
            for x_dir in sorted(z_src.iterdir()):
                if not x_dir.is_dir():
                    continue
                x_val = int(x_dir.name)
                for png in sorted(x_dir.glob("*.png")):
                    y_val = int(png.stem)
                    elev = decode_terrarium_png(png)
                    save_lossless_webp(compress_dem_rgb(elev, z, x_val, y_val), DEM_OUT_DIR / str(z) / x_dir.name / f"{png.stem}.webp")
                    cnt += 1
        print(f"[dem] z={z} HD Asia converted ({cnt} tiles)", flush=True)

    print(f"[out] {DEM_OUT_DIR} -> {total_files} lossless DEM WebP tiles, total {total_bytes / (1024 * 1024):.2f} MB")
    return z4_grid


def rasterize_mercator_land_mask(land_geoms: list[dict], size: int) -> np.ndarray:
    polys: list[tuple[float, list]] = []
    for g in land_geoms:
        gtype = g.get("type")
        coords = g.get("coordinates") or []
        plist = [coords] if gtype == "Polygon" else (coords if gtype == "MultiPolygon" else [])
        for poly in plist:
            if poly and len(poly[0]) >= 3:
                polys.append((abs(ring_area(poly[0])), poly))
    polys.sort(key=lambda item: item[0], reverse=True)

    mask_img = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask_img)

    def to_merc_px(ring: list) -> list[tuple[float, float]]:
        out = []
        for pt in ring:
            lon = max(-180.0, min(180.0, float(pt[0])))
            lat = max(-85.051128, min(85.051128, float(pt[1])))
            x = (lon + 180.0) / 360.0 * size
            lat_rad = math.radians(lat)
            y = (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) * 0.5 * size
            out.append((x, y))
        return out

    for _, poly in polys:
        draw.polygon(to_merc_px(poly[0]), fill=255)
        for hole in poly[1:]:
            if len(hole) >= 3:
                draw.polygon(to_merc_px(hole), fill=0)

    return np.asarray(mask_img, dtype=np.uint8) > 127


def interp_stops(val: np.ndarray, stops: list[tuple[float, tuple[int, int, int]]]) -> np.ndarray:
    xs = np.array([s[0] for s in stops], dtype=np.float32)
    cs = np.array([s[1] for s in stops], dtype=np.float32)
    out = np.empty((*val.shape, 3), dtype=np.float32)
    for ch in range(3):
        out[..., ch] = np.interp(val, xs, cs[:, ch])
    return out


def build_relief_tiles_from_dem(z4_merc_elev: np.ndarray, land_mask: np.ndarray) -> None:
    """
    基于真实数值高程生成暗色古风分层设色 + 多向山体阴影兜底栅格瓦片（z0..z4, 512px）：
    让塔里木盆地、河西走廊、四川盆地、关中平原与天山/昆仑/青藏高原自然形成温润高程层次。
    """

    # 多方位角山体阴影 (NW 315° 主光 + WSW 250° 辅光 + NNE 20° 侧光)
    dy, dx = np.gradient(z4_merc_elev / 2400.0)
    slope = np.arctan(np.hypot(dx, dy) * 2.6)
    aspect = np.arctan2(-dx, dy)

    def shade_dir(az_deg: float, alt_deg: float) -> np.ndarray:
        az = math.radians(az_deg)
        alt = math.radians(alt_deg)
        s = math.sin(alt) * np.cos(slope) + math.cos(alt) * np.sin(slope) * np.cos(az - aspect)
        return np.clip(s, 0.0, 1.0)

    multi_shade = 0.55 * shade_dir(315.0, 38.0) + 0.25 * shade_dir(260.0, 42.0) + 0.20 * shade_dir(25.0, 45.0)
    neutral = math.sin(math.radians(40.0))
    relief_delta = (multi_shade - neutral)

    # 海洋深浅分层设色（深海沟 -> 洋盆 -> 大陆坡 -> 浅海大陆架：典藏深海蓝，与暗金陆地分明对照）
    ocean_stops = [
        (-7500.0, (9, 32, 62)),
        (-4200.0, (13, 45, 84)),
        (-1800.0, (19, 60, 108)),
        (-200.0, (28, 82, 138)),
        (0.0, (37, 102, 162)),
    ]
    # 陆地暗色典藏分层设色（冲积平原青黛 -> 绿洲内陆盆地微暖墨褐 -> 高原冷灰褐 -> 极高山暖金脊霜）
    land_stops = [
        (-80.0, (17, 23, 35)),
        (0.0, (19, 26, 39)),
        (250.0, (23, 31, 44)),
        (900.0, (29, 36, 47)),    # 塔里木 / 河西 / 关中盆地阶地
        (1800.0, (36, 41, 50)),   # 蒙古 / 伊朗 / 黄土高原
        (3200.0, (46, 49, 57)),   # 天山 / 祁连 / 秦岭山脊
        (4800.0, (60, 61, 68)),   # 青藏高原 / 帕米尔葱岭
        (6800.0, (80, 78, 82)),   # 极高山雪线微高光
    ]

    ocean_rgb = interp_stops(z4_merc_elev, ocean_stops)
    land_rgb = interp_stops(z4_merc_elev, land_stops)
    # 叠加多向地形光影：阳坡带极微暖金调，阴坡沉入墨色
    warm_tint = np.array([1.12, 1.03, 0.88], dtype=np.float32)
    land_shaded = land_rgb + (relief_delta[..., None] * 42.0 * warm_tint)
    ocean_shaded = ocean_rgb + (relief_delta[..., None] * 14.0)

    colored = np.clip(np.rint(np.where(land_mask[..., None], land_shaded, ocean_shaded)), 0, 255).astype(np.uint8)
    base_merc_img = Image.fromarray(colored, mode="RGB")

    if RELIEF_DIR.exists():
        shutil.rmtree(RELIEF_DIR)
    RELIEF_DIR.mkdir(parents=True, exist_ok=True)

    tile_size = 512
    total_files = 0
    total_bytes = 0
    for z in range(0, 5):
        n_tiles = 1 << z
        canvas_px = n_tiles * tile_size
        level_img = base_merc_img.resize((canvas_px, canvas_px), Image.Resampling.LANCZOS)
        for x in range(n_tiles):
            z_x_dir = RELIEF_DIR / str(z) / str(x)
            z_x_dir.mkdir(parents=True, exist_ok=True)
            for y in range(n_tiles):
                crop = level_img.crop((x * tile_size, y * tile_size, (x + 1) * tile_size, (y + 1) * tile_size))
                tile_path = z_x_dir / f"{y}.webp"
                crop.save(tile_path, format="WEBP", quality=80, method=4)
                total_files += 1
                total_bytes += tile_path.stat().st_size
        print(f"[relief] z={z} ({n_tiles}x{n_tiles}) done", flush=True)

    print(f"[out] {RELIEF_DIR} -> {total_files} WebP tiles, total {total_bytes / (1024 * 1024):.2f} MB")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build MAPDEX 10m vector, Terrarium DEM & dark hypsometric relief basemap")
    parser.add_argument("--vector-only", action="store_true", help="Only rebuild natural-earth.geojson")
    args = parser.parse_args()

    land_raw = build_vector_geojson()
    if args.vector_only:
        return 0
    land_mask_4096 = rasterize_mercator_land_mask(land_raw, 4096)
    z4_merc_elev = build_dem_webp_tiles(land_mask_4096)
    build_relief_tiles_from_dem(z4_merc_elev, land_mask_4096)
    return 0


if __name__ == "__main__":
    sys.exit(main())
