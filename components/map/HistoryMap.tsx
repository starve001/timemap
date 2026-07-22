'use client';

import { useEffect, useRef, useState } from 'react';
import { useHistoryStore } from '@/lib/store';
import { dynasties } from '@/data/dynasties';
import { cities } from '@/data/geojson/territories';
import { historyEvents } from '@/data/events/events';
import { findDynasty, formatYear } from '@/lib/utils';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

// ─── 中研院 WMTS 历史地图瓦片 ───
// 数据来源：谭其骧《中国历史地图集》数字化版本
// 服务地址：https://gis.sinica.edu.tw/ccts/wmts
// 使用 GoogleMapsCompatible TileMatrixSet（XYZ 方案，z/x/y 从上到下）
const WMTS_TILE_BASE = 'https://gis.sinica.edu.tw/ccts/file-exists.php';

// 朝代 ID → WMTS Layer ID 映射
const DYNASTY_WMTS_MAP: Record<string, string | null> = {
  xia: null,                    // 夏朝无对应瓦片
  shang: 'shang',               // 商時期地圖
  zhou: 'Xijhou',               // 西周時期地圖
  spring_autumn: 'spring_autumn', // 春秋時期地圖
  warring_states: 'warring_states', // 戰國時期地圖
  qin: 'bc0210',                // 秦代歷史地圖(前210)
  han: 'bc0007',                // 西漢歷史地圖(前7)
  han_east: 'ad0140',           // 東漢歷史地圖(140)
  three: 'ad0262',              // 三國歷史地圖(262)
  jin: 'ad0281',                // 西晉歷史地圖(281)
  jin_east: 'ad0382',           // 東晉歷史地圖(382)
  nansouth: 'ad0497',          // 南北朝歷史地圖(497)
  sui: 'ad0612',                // 隋代歷史地圖(612)
  tang: 'ad0741',               // 唐代歷史地圖(741)
  five_dynasties: null,         // 五代十国：无对应 WMTS 瓦片
  song: 'ad1111',               // 北宋歷史地圖(1111)
  song_south: 'ad1208',         // 南宋歷史地圖(1208)
  yuan: 'ad1330',               // 元代歷史地圖(1330)
  ming: 'ad1582',               // 明代歷史地圖(1582)
  qing: 'ad1820',               // 清代歷史地圖(1820)
};

function getWmtsTiles(layerId: string): string[] {
  return [`${WMTS_TILE_BASE}?img=${layerId}-png-{z}-{x}-{y}`];
}

// 历史地图瓦片透明度（让底图河流/地形透过来）
const RASTER_OPACITY = 0.78;

export default function HistoryMap() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const firstSymbolRef = useRef<string | undefined>(undefined);
  const { map: mapState, selectEvent } = useHistoryStore();
  const [loaded, setLoaded] = useState(false);
  const [mapLoading, setMapLoading] = useState(true);
  const [mapError, setMapError] = useState(false);

  const currentDynasty = findDynasty(dynasties, mapState.currentDynastyId);

  // 初始化地图
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const m = new maplibregl.Map({
      container: containerRef.current,
      // OpenFreeMap Bright：免费矢量瓦片，无需 API Key
      // 包含现代道路、河流、地形框架
      style: 'https://tiles.openfreemap.org/styles/bright',
      center: [108.94, 34.34],
      zoom: 3.5,
      attributionControl: {
        compact: true,
        customAttribution:
          '历史地图 © <a href="https://gis.sinica.edu.tw/ccts" target="_blank">中研院·谭其骧历史地图集</a> · 底图 © <a href="https://openfreemap.org" target="_blank">OpenFreeMap</a>',
      },
    });

    // 加载超时检测
    const loadTimeout = setTimeout(() => {
      setMapLoading(false);
    }, 15000);

    m.on('error', () => {
      // 不立即标记为错误（单个瓦片加载失败不应阻止地图使用）
      console.warn('Map tile error occurred');
    });

    m.on('load', () => {
      clearTimeout(loadTimeout);

      // 找到第一个 symbol 图层，历史图层插入到它之前
      // 这样底图的道路标签会在历史地图之上，保持可读性
      const styleLayers = m.getStyle().layers;
      for (const layer of styleLayers) {
        if (layer.type === 'symbol') {
          firstSymbolRef.current = layer.id;
          break;
        }
      }

      // ── 历史地图栅格瓦片层 ──
      const initialLayerId = DYNASTY_WMTS_MAP[mapState.currentDynastyId];
      if (initialLayerId) {
        m.addSource('historical-map', {
          type: 'raster',
          tiles: getWmtsTiles(initialLayerId),
          tileSize: 256,
          maxzoom: 10,
        });
        m.addLayer({
          id: 'historical-map-layer',
          type: 'raster',
          source: 'historical-map',
          paint: {
            'raster-opacity': RASTER_OPACITY,
          },
        }, firstSymbolRef.current);
      }


      // ── 城市标记 ──
      m.addSource('cities', { type: 'geojson', data: cities });
      m.addLayer({
        id: 'cities-circle',
        type: 'circle',
        source: 'cities',
        paint: {
          'circle-radius': ['match', ['get', 'type'], 'capital', 8, 5],
          'circle-color': ['match', ['get', 'type'], 'capital', '#C43A31', '#b8860b'],
          'circle-stroke-width': 2,
          'circle-stroke-color': '#ffffff',
        },
      }, firstSymbolRef.current);

      m.addLayer({
        id: 'cities-label',
        type: 'symbol',
        source: 'cities',
        layout: {
          'text-field': ['get', 'name'],
          'text-size': ['match', ['get', 'type'], 'capital', 13, 10],
          'text-offset': [0, -1.5],
          'text-anchor': 'bottom',
          // OpenFreeMap 内置字体，支持 CJK
          'text-font': ['Noto Sans Regular'],
        },
        paint: {
          'text-color': '#3d3d3d',
          'text-halo-color': '#ffffff',
          'text-halo-width': 1.5,
        },
      }, firstSymbolRef.current);

      // ── 事件标记 ──
      const dynastyEvents = historyEvents.filter(
        (e) => e.dynastyId === mapState.currentDynastyId,
      );
      const eventFeatures = dynastyEvents.map((e) => ({
        type: 'Feature' as const,
        properties: { id: e.id, title: e.title, category: e.category },
        geometry: { type: 'Point' as const, coordinates: e.location },
      }));

      m.addSource('events', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: eventFeatures },
      });

      m.addLayer({
        id: 'events-circle',
        type: 'circle',
        source: 'events',
        paint: {
          'circle-radius': 6,
          'circle-color': [
            'match', ['get', 'category'],
            'war', '#C43A31',
            'politics', '#b8860b',
            'culture', '#5B8C5A',
            'technology', '#4A6B8B',
            '#b8860b',
          ],
          'circle-stroke-width': 2,
          'circle-stroke-color': '#ffffff',
        },
      }, firstSymbolRef.current);

      m.addLayer({
        id: 'events-label',
        type: 'symbol',
        source: 'events',
        layout: {
          'text-field': ['get', 'title'],
          'text-size': 10,
          'text-offset': [0, 1.5],
          'text-anchor': 'top',
          'text-max-width': 8,
          'text-font': ['Noto Sans Regular'],
        },
        paint: {
          'text-color': '#6b6b6b',
          'text-halo-color': '#ffffff',
          'text-halo-width': 1.5,
        },
      }, firstSymbolRef.current);

      setLoaded(true);
      setMapLoading(false);
    });

    mapRef.current = m;

    return () => {
      clearTimeout(loadTimeout);
      m.remove();
      mapRef.current = null;
    };
  }, []);

  // 朝代切换 → 更新历史地图瓦片 + 城市 + 事件
  useEffect(() => {
    if (!loaded || !mapRef.current || !currentDynasty) return;

    const m = mapRef.current;
    const wmtsLayerId = DYNASTY_WMTS_MAP[currentDynasty.id];

    // 移除旧的历史地图瓦片层
    if (m.getLayer('historical-map-layer')) {
      m.removeLayer('historical-map-layer');
    }
    if (m.getSource('historical-map')) {
      m.removeSource('historical-map');
    }

    // 添加新的历史地图瓦片层
    if (wmtsLayerId) {
      m.addSource('historical-map', {
        type: 'raster',
        tiles: getWmtsTiles(wmtsLayerId),
        tileSize: 256,
        maxzoom: 10,
      });
      m.addLayer({
        id: 'historical-map-layer',
        type: 'raster',
        source: 'historical-map',
        paint: {
          'raster-opacity': RASTER_OPACITY,
        },
      }, firstSymbolRef.current);
    }

    // 过滤城市（显示当前朝代 + 所有都城）
    const cityFilter: maplibregl.FilterSpecification = [
      'any',
      ['==', ['get', 'dynasty'], currentDynasty.id],
      ['==', ['get', 'type'], 'capital'],
    ];
    m.setFilter('cities-circle', cityFilter);
    m.setFilter('cities-label', cityFilter);

    // 更新事件数据
    const eventFeatures = historyEvents
      .filter((e) => e.dynastyId === currentDynasty.id)
      .map((e) => ({
        type: 'Feature' as const,
        properties: { id: e.id, title: e.title, category: e.category },
        geometry: { type: 'Point' as const, coordinates: e.location },
      }));

    const eventSource = m.getSource('events') as maplibregl.GeoJSONSource | undefined;
    if (eventSource) {
      eventSource.setData({
        type: 'FeatureCollection',
        features: eventFeatures,
      });
    }

    // 飞到都城
    m.flyTo({
      center: currentDynasty.capitalCoords,
      zoom: 4,
      duration: 1200,
      essential: true,
    });
  }, [loaded, mapState.currentDynastyId, currentDynasty]);

  // 事件点击交互
  useEffect(() => {
    if (!loaded || !mapRef.current) return;

    const m = mapRef.current;

    const onEventClick = (
      e: maplibregl.MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] },
    ) => {
      if (e.features && e.features.length > 0) {
        const id = e.features[0].properties?.id;
        if (id) selectEvent(id);
      }
    };

    m.on('click', 'events-circle', onEventClick);

    const onEnter = () => {
      m.getCanvas().style.cursor = 'pointer';
    };
    const onLeave = () => {
      m.getCanvas().style.cursor = '';
    };

    m.on('mouseenter', 'events-circle', onEnter);
    m.on('mouseleave', 'events-circle', onLeave);

    return () => {
      m.off('click', 'events-circle', onEventClick);
      m.off('mouseenter', 'events-circle', onEnter);
      m.off('mouseleave', 'events-circle', onLeave);
    };
  }, [loaded, selectEvent]);

  return (
    <div className="relative w-full h-full">
      <div ref={containerRef} className="w-full h-full" />

      {/* 加载中提示 */}
      {mapLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-silk/80 z-20">
          <div className="flex flex-col items-center gap-4">
            {/* 旋转加载圈 */}
            <div className="relative w-12 h-12">
              <div className="absolute inset-0 rounded-full border-2 border-bamboo" />
              <div
                className="absolute inset-0 rounded-full border-2 border-transparent animate-spin"
                style={{ borderTopColor: currentDynasty?.color || '#C43A31' }}
              />
            </div>
            <div className="font-serif text-sm text-ink-500">
              正在加载{currentDynasty?.name || ''}地图...
            </div>
          </div>
        </div>
      )}

      {/* 错误提示 */}
      {mapError && (
        <div className="absolute inset-0 flex items-center justify-center bg-silk/90 z-20">
          <div className="text-center">
            <div className="text-cinnabar font-serif text-lg">地图加载失败</div>
            <div className="text-ink-500 text-sm mt-2">请检查网络连接后刷新页面</div>
          </div>
        </div>
      )}

      {/* 朝代角标 */}
      {currentDynasty && (
        <div className="absolute top-4 left-4 z-10 select-none">
          <div
            className="bg-white/90 backdrop-blur-sm border border-bamboo rounded-xl px-5 py-3 shadow-lg"
          >
            <div className="flex items-center gap-2">
              <span
                className="inline-block w-2.5 h-2.5 rounded-full"
                style={{ background: currentDynasty.color }}
              />
              <span
                className="font-serif text-2xl font-bold tracking-wide"
                style={{ color: currentDynasty.color }}
              >
                {currentDynasty.name}
              </span>
            </div>
            <div className="text-xs text-ink-500 mt-1 tabular-nums">
              {formatYear(currentDynasty.startYear)} — {formatYear(currentDynasty.endYear)}
              {'  ·  '}共 {currentDynasty.endYear - currentDynasty.startYear} 年
            </div>
            {currentDynasty.capital && (
              <div className="text-[10px] text-ink-300 mt-0.5">
                都城：{currentDynasty.capital}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
