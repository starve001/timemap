#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/build-basemap.py — 构建同源自托管 Natural Earth 暗色古风自然底图资产

产物（输出至 data/basemap/）：
  1. natural-earth.geojson      1:50m 纯自然矢量（陆地 / 200m 海深 / 湖泊 / 大河[裁除中国历史河网区] / 15° 经纬网）
  2. relief/{z}/{x}/{y}.webp    z0–z4 512px Web 墨卡托暗色古风地形晕渲瓦片（341 张，基于 GRAY_50M_SR_OB）

全部数据源来自 Natural Earth (Public Domain)，下载包缓存在 .tmp-basemap-src/（已 gitignore）。
用法：python tools/build-basemap.py [--force]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
import requests
import shapefile
from PIL import Image, ImageDraw
from scipy.ndimage import map_coordinates

Image.MAX_IMAGE_PIXELS = None

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / ".tmp-basemap-src"
OUT_DIR = ROOT / "data" / "basemap"
RELIEF_DIR = OUT_DIR / "relief"

SOURCES = {
    "ne_50m_land.zip": "https://naciscdn.org/naturalearth/50m/physical/ne_50m_land.zip",
    "ne_50m_lakes.zip": "https://naciscdn.org/naturalearth/50m/physical/ne_50m_lakes.zip",
    "ne_50m_rivers_lake_centerlines.zip": "https://naciscdn.org/naturalearth/50m/physical/ne_50m_rivers_lake_centerlines.zip",
    "ne_10m_bathymetry_K_200.zip": "https://naciscdn.org/naturalearth/10m/physical/ne_10m_bathymetry_K_200.zip",
    "GRAY_50M_SR_OB.zip": "https://naciscdn.org/naturalearth/50m/raster/GRAY_50M_SR_OB.zip",
}

# 中国历史水系核心裁除区（避免现代黄河/长江/淮河/珠江与 data/geography.json 冲突）
CN_RIVER_EXCLUDE_BOXES = (
    (113.2, 32.0, 123.0, 40.5),  # 黄淮下游区（保留河套/陕晋中上游至郑州外接处）
    (104.5, 22.0, 123.0, 33.5),  # 长江中下游 / 汉水 / 珠江区
)


def download_all(force: bool) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": "MAPDEX-Basemap-Builder/1.0"})
    for name, url in SOURCES.items():
        dst = CACHE_DIR / name
        if dst.exists() and dst.stat().st_size > 0 and not force:
            print(f"[cache] {name} ({dst.stat().st_size / 1024:.1f} KB)", flush=True)
            continue
        print(f"[fetch] {url} -> {dst}", flush=True)
        tmp = dst.with_suffix(".zip.part")
        if tmp.exists():
            tmp.unlink()
        ok = False
        for attempt in range(1, 4):
            try:
                with session.get(url, stream=True, timeout=(15, 60)) as r:
                    r.raise_for_status()
                    with open(tmp, "wb") as f:
                        for chunk in r.iter_content(chunk_size=1 << 16):
                            if chunk:
                                f.write(chunk)
                ok = True
                break
            except Exception as exc:
                print(f"        requests attempt {attempt} failed: {exc}", flush=True)
        if not ok:
            res = subprocess.run(
                ["curl.exe", "-fL", "-C", "-", "--retry", "8", "--retry-all-errors", "--retry-delay", "2", "--connect-timeout", "15", "--speed-limit", "2000", "--speed-time", "30", "-o", str(tmp), url],
                check=False,
            )
            if res.returncode != 0:
                raise RuntimeError(f"Failed to download {url}")
        tmp.replace(dst)
        print(f"        saved {dst.stat().st_size / 1024:.1f} KB", flush=True)


def extract_zip(zip_name: str) -> Path:
    src = CACHE_DIR / zip_name
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
    proj_x = a[0] + t * dx
    proj_y = a[1] + t * dy
    return math.hypot(p[0] - proj_x, p[1] - proj_y)


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


def ring_area(ring: list[tuple[float, float]] | list[list[float]]) -> float:
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
    if len(cleaned) < 2:
        return None
    return cleaned


def clean_polygon_geom(geom: dict, tol: float, decimals: int, min_outer_area: float = 0.0) -> dict | None:
    gtype = geom.get("type")
    coords = geom.get("coordinates") or []
    if gtype == "Polygon":
        polys = [coords]
    elif gtype == "MultiPolygon":
        polys = coords
    else:
        return None

    kept_polys: list[list[list[list[float]]]] = []
    for poly in polys:
        if not poly:
            continue
        outer = simplify_ring(poly[0], tol, decimals, min_area=min_outer_area)
        if not outer:
            continue
        holes = []
        for h in poly[1:]:
            ch = simplify_ring(h, tol, decimals, min_area=0.0)
            if ch:
                holes.append(ch)
        kept_polys.append([outer] + holes)

    if not kept_polys:
        return None
    if len(kept_polys) == 1:
        return {"type": "Polygon", "coordinates": kept_polys[0]}
    return {"type": "MultiPolygon", "coordinates": kept_polys}


def point_in_ring(lon: float, lat: float, ring: list) -> bool:
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def point_in_geom(lon: float, lat: float, geom: dict) -> bool:
    gtype = geom.get("type")
    coords = geom.get("coordinates") or []
    polys = [coords] if gtype == "Polygon" else (coords if gtype == "MultiPolygon" else [])
    for poly in polys:
        if not poly:
            continue
        if point_in_ring(lon, lat, poly[0]):
            in_hole = any(point_in_ring(lon, lat, h) for h in poly[1:])
            if not in_hole:
                return True
    return False


def in_cn_river_exclude(lon: float, lat: float) -> bool:
    for min_x, min_y, max_x, max_y in CN_RIVER_EXCLUDE_BOXES:
        if min_x <= lon <= max_x and min_y <= lat <= max_y:
            return True
    return False


def split_river_coords(coords: list) -> list[list]:
    segments: list[list] = []
    cur: list = []
    for pt in coords:
        if in_cn_river_exclude(pt[0], pt[1]):
            if len(cur) >= 2:
                segments.append(cur)
            cur = []
        else:
            cur.append(pt)
    if len(cur) >= 2:
        segments.append(cur)
    return segments


def build_graticules() -> list[dict]:
    feats: list[dict] = []
    # 经线：-180 到 180 每 15°（避开重复 180，画 -165..180）
    for lon in range(-165, 181, 15):
        coords = [[round(float(lon), 1), round(float(lat), 1)] for lat in range(-80, 81, 5)]
        feats.append({"type": "Feature", "properties": {"k": "grat"}, "geometry": {"type": "LineString", "coordinates": coords}})
    # 纬线：-75 到 75 每 15°
    for lat in range(-75, 76, 15):
        coords = [[round(float(lon), 1), round(float(lat), 1)] for lon in range(-180, 181, 5)]
        feats.append({"type": "Feature", "properties": {"k": "grat"}, "geometry": {"type": "LineString", "coordinates": coords}})
    return feats


def build_vector_geojson() -> tuple[list[dict], bool]:
    features: list[dict] = []

    # 1. ne_50m_land
    land_shp = find_shp(extract_zip("ne_50m_land.zip"))
    land_raw: list[dict] = []
    with shapefile.Reader(str(land_shp)) as sf:
        for sr in sf.iterShapeRecords():
            if sr.shape.shapeType == shapefile.NULL or not sr.shape.points:
                continue
            geom = sr.shape.__geo_interface__
            land_raw.append(geom)
            cg = clean_polygon_geom(geom, tol=0.02, decimals=3, min_outer_area=0.0)
            if cg:
                features.append({"type": "Feature", "properties": {"k": "land"}, "geometry": cg})
    print(f"[vec] land features: {sum(1 for f in features if f['properties']['k'] == 'land')}")

    # 2. ne_10m_bathymetry_K_200
    k200_shp = find_shp(extract_zip("ne_10m_bathymetry_K_200.zip"))
    k200_geoms: list[dict] = []
    with shapefile.Reader(str(k200_shp)) as sf:
        for sr in sf.iterShapeRecords():
            if sr.shape.shapeType == shapefile.NULL or not sr.shape.points:
                continue
            geom = sr.shape.__geo_interface__
            k200_geoms.append(geom)
            cg = clean_polygon_geom(geom, tol=0.15, decimals=2, min_outer_area=0.4)
            if cg:
                features.append({"type": "Feature", "properties": {"k": "shelf"}, "geometry": cg})
    pac_in_k200 = any(point_in_geom(-150.0, 0.0, g) for g in k200_geoms)
    ys_in_k200 = any(point_in_geom(125.0, 35.0, g) for g in k200_geoms)
    eu_in_k200 = any(point_in_geom(10.0, 50.0, g) for g in k200_geoms)
    print(f"[vec] shelf/K_200 features: {sum(1 for f in features if f['properties']['k'] == 'shelf')}")
    print(f"[check] K_200 contains Pacific(-150,0)={pac_in_k200}, YellowSea(125,35)={ys_in_k200}, Europe(10,50)={eu_in_k200}")

    # 3. ne_50m_lakes (scalerank <= 6)
    lakes_shp = find_shp(extract_zip("ne_50m_lakes.zip"))
    with shapefile.Reader(str(lakes_shp)) as sf:
        fields = [f[0].lower() for f in sf.fields[1:]]
        sr_idx = fields.index("scalerank") if "scalerank" in fields else -1
        for sr in sf.iterShapeRecords():
            if sr.shape.shapeType == shapefile.NULL or not sr.shape.points:
                continue
            rank = sr.record[sr_idx] if sr_idx >= 0 else 0
            if rank is not None and float(rank) > 6:
                continue
            cg = clean_polygon_geom(sr.shape.__geo_interface__, tol=0.02, decimals=3, min_outer_area=0.0)
            if cg:
                features.append({"type": "Feature", "properties": {"k": "lake"}, "geometry": cg})
    print(f"[vec] lake features: {sum(1 for f in features if f['properties']['k'] == 'lake')}")

    # 4. ne_50m_rivers_lake_centerlines (scalerank <= 5 + 裁除中国历史河网重叠区)
    rivers_shp = find_shp(extract_zip("ne_50m_rivers_lake_centerlines.zip"))
    with shapefile.Reader(str(rivers_shp)) as sf:
        fields = [f[0].lower() for f in sf.fields[1:]]
        sr_idx = fields.index("scalerank") if "scalerank" in fields else -1
        for sr in sf.iterShapeRecords():
            if sr.shape.shapeType == shapefile.NULL or not sr.shape.points:
                continue
            rank = sr.record[sr_idx] if sr_idx >= 0 else 0
            if rank is not None and float(rank) > 5:
                continue
            geom = sr.shape.__geo_interface__
            gtype = geom.get("type")
            lines = [geom["coordinates"]] if gtype == "LineString" else (geom["coordinates"] if gtype == "MultiLineString" else [])
            out_lines: list[list[list[float]]] = []
            for line in lines:
                for sub in split_river_coords(line):
                    cl = simplify_line(sub, tol=0.02, decimals=3)
                    if cl:
                        out_lines.append(cl)
            if not out_lines:
                continue
            out_geom = {"type": "LineString", "coordinates": out_lines[0]} if len(out_lines) == 1 else {"type": "MultiLineString", "coordinates": out_lines}
            features.append({"type": "Feature", "properties": {"k": "river"}, "geometry": out_geom})
    print(f"[vec] river features: {sum(1 for f in features if f['properties']['k'] == 'river')}")

    # 5. 15° graticules
    grat_feats = build_graticules()
    features.extend(grat_feats)
    print(f"[vec] graticule features: {len(grat_feats)}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    vec_path = OUT_DIR / "natural-earth.geojson"
    fc = {"type": "FeatureCollection", "features": features}
    vec_bytes = json.dumps(fc, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    vec_path.write_bytes(vec_bytes)
    print(f"[out] {vec_path} -> {len(vec_bytes) / 1024:.1f} KB ({len(features)} features)")
    return land_raw, pac_in_k200


def rasterize_land_mask(land_geoms: list[dict], w: int, h: int) -> np.ndarray:
    polys: list[tuple[float, list]] = []
    for g in land_geoms:
        gtype = g.get("type")
        coords = g.get("coordinates") or []
        plist = [coords] if gtype == "Polygon" else (coords if gtype == "MultiPolygon" else [])
        for poly in plist:
            if poly and len(poly[0]) >= 3:
                polys.append((abs(ring_area(poly[0])), poly))
    # 大多边形先画、小岛后画，确保洞内岛屿不会被覆盖
    polys.sort(key=lambda item: item[0], reverse=True)

    mask_img = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask_img)

    def to_px(ring: list) -> list[tuple[float, float]]:
        return [((pt[0] + 180.0) / 360.0 * w, (90.0 - pt[1]) / 180.0 * h) for pt in ring]

    for _, poly in polys:
        draw.polygon(to_px(poly[0]), fill=255)
        for hole in poly[1:]:
            if len(hole) >= 3:
                draw.polygon(to_px(hole), fill=0)

    return np.asarray(mask_img, dtype=np.uint8) > 127


def interp_palette(t: np.ndarray, c0: tuple[int, int, int], c1: tuple[int, int, int], c2: tuple[int, int, int]) -> np.ndarray:
    """将归一化标量 t in [0,1] 分段插值到 3 个 RGB 停靠色（0 -> c0, 0.5 -> c1, 1 -> c2）"""
    t = np.clip(t, 0.0, 1.0)
    out = np.empty((*t.shape, 3), dtype=np.float32)
    low = t <= 0.5
    w_low = np.where(low, t * 2.0, 0.0)[..., None]
    w_high = np.where(~low, (t - 0.5) * 2.0, 0.0)[..., None]
    a0 = np.array(c0, dtype=np.float32)
    a1 = np.array(c1, dtype=np.float32)
    a2 = np.array(c2, dtype=np.float32)
    low_rgb = a0 + (a1 - a0) * w_low
    high_rgb = a1 + (a2 - a1) * w_high
    out = np.where(low[..., None], low_rgb, high_rgb)
    return np.clip(np.rint(out), 0, 255).astype(np.uint8)


def normalize_by_percentiles(vals: np.ndarray, mask: np.ndarray) -> np.ndarray:
    sample = vals[mask]
    p2, p50, p99 = np.percentile(sample, [2.0, 50.0, 99.0])
    print(f"[relief] percentiles (mask count={sample.size}): p2={p2:.1f}, p50={p50:.1f}, p99={p99:.1f}")
    denom_lo = max(p50 - p2, 1e-3)
    denom_hi = max(p99 - p50, 1e-3)
    t = np.where(
        vals <= p50,
        0.5 * (vals - p2) / denom_lo,
        0.5 + 0.5 * (vals - p50) / denom_hi,
    )
    return np.clip(t, 0.0, 1.0)


def build_relief_tiles(land_geoms: list[dict]) -> None:
    folder = extract_zip("GRAY_50M_SR_OB.zip")
    tifs = sorted(folder.rglob("*.tif"))
    if not tifs:
        raise FileNotFoundError(f"No .tif found in {folder}")
    tif_path = tifs[0]
    with Image.open(tif_path) as im:
        print(f"[relief] source {tif_path.name}: size={im.size}, mode={im.mode}")
        gray = np.asarray(im.convert("L"), dtype=np.float32)

    src_h, src_w = gray.shape
    land_mask = rasterize_land_mask(land_geoms, src_w, src_h)

    t_ocean = normalize_by_percentiles(gray, ~land_mask)
    t_land = normalize_by_percentiles(gray, land_mask)

    # 海洋：#060911 -> #0B1322 -> #132238
    ocean_rgb = interp_palette(t_ocean, (6, 9, 17), (11, 19, 34), (19, 34, 56))
    # 陆地：#0D121D -> #171F2E -> #373E4D（带极微暖羊皮山脊高光）
    land_rgb = interp_palette(t_land, (13, 18, 29), (23, 31, 46), (55, 62, 77))

    colored = np.where(land_mask[..., None], land_rgb, ocean_rgb)
    base_img = Image.fromarray(colored, mode="RGB")

    # 生成 z0..z4 512px WebP 瓦片（共 341 张）
    if RELIEF_DIR.exists():
        for root, _, files in os.walk(RELIEF_DIR, topdown=False):
            for fn in files:
                (Path(root) / fn).unlink()
    RELIEF_DIR.mkdir(parents=True, exist_ok=True)

    tile_size = 512
    px = (np.arange(tile_size, dtype=np.float64) + 0.5) / tile_size
    total_files = 0
    total_bytes = 0

    for z in range(0, 5):
        n_tiles = 1 << z
        target_w = min(src_w, max(1024, n_tiles * 1024))
        target_h = target_w // 2
        if target_w == src_w:
            level_arr = colored
        else:
            level_img = base_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            level_arr = np.asarray(level_img, dtype=np.uint8)
        lw, lh = target_w, target_h

        for x in range(n_tiles):
            lon = ((x + px) / n_tiles) * 360.0 - 180.0
            sx = np.clip((lon + 180.0) / 360.0 * lw - 0.5, 0.0, lw - 1.0)
            sx_grid = np.broadcast_to(sx[None, :], (tile_size, tile_size))

            z_x_dir = RELIEF_DIR / str(z) / str(x)
            z_x_dir.mkdir(parents=True, exist_ok=True)

            for y in range(n_tiles):
                merc_n = math.pi - 2.0 * math.pi * ((y + px) / n_tiles)
                lat = np.degrees(np.arctan(np.sinh(merc_n)))
                sy = np.clip((90.0 - lat) / 180.0 * lh - 0.5, 0.0, lh - 1.0)
                sy_grid = np.broadcast_to(sy[:, None], (tile_size, tile_size))

                coords = np.stack([sy_grid, sx_grid], axis=0)
                out_tile = np.empty((tile_size, tile_size, 3), dtype=np.uint8)
                for ch in range(3):
                    out_tile[..., ch] = np.clip(
                        np.rint(map_coordinates(level_arr[..., ch], coords, order=1, mode="nearest", prefilter=False)),
                        0,
                        255,
                    ).astype(np.uint8)

                tile_path = z_x_dir / f"{y}.webp"
                Image.fromarray(out_tile, mode="RGB").save(tile_path, format="WEBP", quality=78, method=4)
                total_files += 1
                total_bytes += tile_path.stat().st_size

        print(f"[relief] z={z} ({n_tiles}x{n_tiles}) done")

    print(f"[out] {RELIEF_DIR} -> {total_files} WebP tiles, total {total_bytes / (1024 * 1024):.2f} MB")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build MAPDEX self-hosted Natural Earth vector & dark relief basemap")
    parser.add_argument("--force", action="store_true", help="Force re-download source zips")
    args = parser.parse_args()

    download_all(force=args.force)
    land_geoms, _ = build_vector_geojson()
    build_relief_tiles(land_geoms)
    return 0


if __name__ == "__main__":
    sys.exit(main())
