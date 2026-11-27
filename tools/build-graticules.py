#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/build-graticules.py — 生成面向 QGIS 的分级经纬网矢量图层（15° / 5° / 1°）与配套 QML 样式

产物（输出至 data/qgis/，不并入 GitHub Pages 静态站以避免增加前端体积）：
  1. data/qgis/graticules.geojson   WGS 84 (EPSG:4326) 分级经纬网（含 axis / deg / step / special / label / label_zh 字段）
  2. data/qgis/graticules.qml       同名前缀 QGIS 样式（拖入 GeoJSON 自动生效：按比例尺分级显隐 + 沿线度数标注）

用法：python tools/build-graticules.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "qgis"
GEOJSON_PATH = OUT_DIR / "graticules.geojson"
QML_PATH = OUT_DIR / "graticules.qml"

LAT_MIN = -80
LAT_MAX = 80
LON_MIN = -180
LON_MAX = 180


def fmt_lon(deg: int) -> tuple[str, str]:
    if deg == 0:
        return "0°", "本初子午线 0°"
    if abs(deg) == 180:
        return "180°", "180° 经线"
    if deg > 0:
        return f"{deg}°E", f"东经{deg}°"
    return f"{-deg}°W", f"西经{-deg}°"


def fmt_lat(deg: int) -> tuple[str, str]:
    if deg == 0:
        return "0°", "赤道 0°"
    if deg > 0:
        return f"{deg}°N", f"北纬{deg}°"
    return f"{-deg}°S", f"南纬{-deg}°"


def step_tier(deg: int) -> int:
    if deg % 15 == 0:
        return 15
    if deg % 5 == 0:
        return 5
    return 1


def build_features() -> list[dict]:
    feats: list[dict] = []

    # 经线（Meridians）：-180° .. 180°，每 1° 一条；每 1° 置顶点，便于任意投影平滑弯曲及 QGIS 顶点捕捉至整数经纬交点（GCP 配准）
    for lon in range(LON_MIN, LON_MAX + 1, 1):
        tier = step_tier(lon)
        coords = [[lon, lat] for lat in range(LAT_MIN, LAT_MAX + 1, 1)]
        label, label_zh = fmt_lon(lon)
        special = "prime" if lon == 0 else ("antimeridian" if abs(lon) == 180 else "")
        feats.append({
            "type": "Feature",
            "properties": {
                "axis": "lon",
                "deg": lon,
                "step": tier,
                "special": special,
                "label": label,
                "label_zh": label_zh,
            },
            "geometry": {
                "type": "LineString",
                "coordinates": coords,
            },
        })

    # 纬线（Parallels）：-80° .. 80°，每 1° 一条；每 1° 置顶点，与经线精确共用整数交点
    for lat in range(LAT_MIN, LAT_MAX + 1, 1):
        tier = step_tier(lat)
        coords = [[lon, lat] for lon in range(LON_MIN, LON_MAX + 1, 1)]
        label, label_zh = fmt_lat(lat)
        special = "equator" if lat == 0 else ""
        feats.append({
            "type": "Feature",
            "properties": {
                "axis": "lat",
                "deg": lat,
                "step": tier,
                "special": special,
                "label": label,
                "label_zh": label_zh,
            },
            "geometry": {
                "type": "LineString",
                "coordinates": coords,
            },
        })

    return feats


QML_CONTENT = """<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.34.0-Prizren" styleCategories="Symbology|Labeling" labelsEnabled="1">
  <renderer-v2 type="RuleRenderer" symbollevels="0" referencescale="-1" enableorderby="0" forceraster="0">
    <rules key="{8a110001-0000-4000-8000-000000000000}">
      <rule key="{8a110001-0000-4000-8000-000000000001}" label="赤道 / 本初子午线 (0°)" filter="&quot;special&quot; IN ('equator', 'prime')" symbol="0"/>
      <rule key="{8a110001-0000-4000-8000-000000000002}" label="15° 主经纬线" filter="&quot;step&quot; = 15 AND &quot;special&quot; NOT IN ('equator', 'prime')" symbol="1"/>
      <rule key="{8a110001-0000-4000-8000-000000000003}" label="5° 区域经纬线" filter="&quot;step&quot; = 5" scalemindenom="0" scalemaxdenom="45000000" symbol="2"/>
      <rule key="{8a110001-0000-4000-8000-000000000004}" label="1° 精细经纬线" filter="&quot;step&quot; = 1" scalemindenom="0" scalemaxdenom="12000000" symbol="3"/>
    </rules>
    <symbols>
      <symbol type="line" name="0" alpha="0.72" clip_to_extent="1" force_rhr="0">
        <layer class="SimpleLine" enabled="1" locked="0" pass="0">
          <Option type="Map">
            <Option type="QString" name="line_color" value="233,204,133,255"/>
            <Option type="QString" name="line_style" value="solid"/>
            <Option type="QString" name="line_width" value="0.45"/>
            <Option type="QString" name="line_width_unit" value="MM"/>
          </Option>
        </layer>
      </symbol>
      <symbol type="line" name="1" alpha="0.52" clip_to_extent="1" force_rhr="0">
        <layer class="SimpleLine" enabled="1" locked="0" pass="0">
          <Option type="Map">
            <Option type="QString" name="line_color" value="201,162,75,255"/>
            <Option type="QString" name="line_style" value="solid"/>
            <Option type="QString" name="line_width" value="0.32"/>
            <Option type="QString" name="line_width_unit" value="MM"/>
          </Option>
        </layer>
      </symbol>
      <symbol type="line" name="2" alpha="0.44" clip_to_extent="1" force_rhr="0">
        <layer class="SimpleLine" enabled="1" locked="0" pass="0">
          <Option type="Map">
            <Option type="QString" name="line_color" value="127,169,201,255"/>
            <Option type="QString" name="line_style" value="solid"/>
            <Option type="QString" name="line_width" value="0.24"/>
            <Option type="QString" name="line_width_unit" value="MM"/>
          </Option>
        </layer>
      </symbol>
      <symbol type="line" name="3" alpha="0.34" clip_to_extent="1" force_rhr="0">
        <layer class="SimpleLine" enabled="1" locked="0" pass="0">
          <Option type="Map">
            <Option type="QString" name="line_color" value="108,138,166,255"/>
            <Option type="QString" name="line_style" value="dash"/>
            <Option type="QString" name="line_width" value="0.18"/>
            <Option type="QString" name="line_width_unit" value="MM"/>
            <Option type="QString" name="use_custom_dash" value="1"/>
            <Option type="QString" name="customdash" value="1.2;1.2"/>
            <Option type="QString" name="customdash_unit" value="MM"/>
          </Option>
        </layer>
      </symbol>
    </symbols>
  </renderer-v2>
  <labeling type="rule-based">
    <rules key="{8a110002-0000-4000-8000-000000000000}">
      <rule key="{8a110002-0000-4000-8000-000000000001}" description="15° 标注" filter="&quot;step&quot; = 15">
        <settings calloutType="simple">
          <text-style fieldName="label" fontFamily="Microsoft YaHei" fontSize="9.5" fontSizeUnit="Point" fontWeight="600" textColor="233,204,133,255" textOpacity="0.92" isExpression="0">
            <text-buffer bufferDraw="1" bufferSize="0.9" bufferSizeUnits="MM" bufferColor="10,14,24,255" bufferOpacity="0.88"/>
          </text-style>
          <placement placement="2" repeatDistance="110" repeatDistanceUnits="MM" dist="1.2" distUnits="MM" priority="7"/>
          <rendering scaleVisibility="0" labelPerPart="0" obstacle="0"/>
        </settings>
      </rule>
      <rule key="{8a110002-0000-4000-8000-000000000002}" description="5° 标注" filter="&quot;step&quot; = 5" scalemindenom="0" scalemaxdenom="45000000">
        <settings calloutType="simple">
          <text-style fieldName="label" fontFamily="Microsoft YaHei" fontSize="8.5" fontSizeUnit="Point" fontWeight="500" textColor="168,205,232,255" textOpacity="0.88" isExpression="0">
            <text-buffer bufferDraw="1" bufferSize="0.8" bufferSizeUnits="MM" bufferColor="10,14,24,255" bufferOpacity="0.86"/>
          </text-style>
          <placement placement="2" repeatDistance="95" repeatDistanceUnits="MM" dist="1.0" distUnits="MM" priority="5"/>
          <rendering scaleVisibility="1" scaleMin="0" scaleMax="45000000" labelPerPart="0" obstacle="0"/>
        </settings>
      </rule>
      <rule key="{8a110002-0000-4000-8000-000000000003}" description="1° 标注" filter="&quot;step&quot; = 1" scalemindenom="0" scalemaxdenom="10000000">
        <settings calloutType="simple">
          <text-style fieldName="label" fontFamily="Microsoft YaHei" fontSize="8" fontSizeUnit="Point" fontWeight="400" textColor="148,180,208,255" textOpacity="0.82" isExpression="0">
            <text-buffer bufferDraw="1" bufferSize="0.7" bufferSizeUnits="MM" bufferColor="10,14,24,255" bufferOpacity="0.82"/>
          </text-style>
          <placement placement="2" repeatDistance="85" repeatDistanceUnits="MM" dist="0.8" distUnits="MM" priority="3"/>
          <rendering scaleVisibility="1" scaleMin="0" scaleMax="10000000" labelPerPart="0" obstacle="0"/>
        </settings>
      </rule>
    </rules>
  </labeling>
</qgis>
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    feats = build_features()
    fc = {
        "type": "FeatureCollection",
        "name": "MAPDEX Graded Graticules (15/5/1 deg)",
        "features": feats,
    }
    GEOJSON_PATH.write_text(json.dumps(fc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    QML_PATH.write_text(QML_CONTENT.strip() + "\n", encoding="utf-8")

    n15 = sum(1 for f in feats if f["properties"]["step"] == 15)
    n5 = sum(1 for f in feats if f["properties"]["step"] == 5)
    n1 = sum(1 for f in feats if f["properties"]["step"] == 1)
    kb = GEOJSON_PATH.stat().st_size / 1024.0
    print(f"[qgis] {GEOJSON_PATH} -> {len(feats)} lines (15°:{n15}, 5°:{n5}, 1°:{n1}), {kb:.1f} KB")
    print(f"[qgis] {QML_PATH} written (auto-loaded by QGIS with same basename)")


if __name__ == "__main__":
    main()
