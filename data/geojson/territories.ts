import type { GeoJSONCollection } from '@/types';

// 疆域数据为简化手绘轮廓，仅用于原型展示
// Phase 2 将替换为 CHGIS 精确数据
export const territories: Record<string, GeoJSONCollection> = {
  han: {
    type: 'FeatureCollection',
    features: [{
      type: 'Feature',
      properties: { name: '汉', year: -202 },
      geometry: {
        type: 'MultiPolygon',
        coordinates: [[[
          [73.5, 39.5], [79.0, 42.0], [85.0, 44.0], [90.0, 45.5], [96.0, 44.0],
          [102.0, 42.5], [107.0, 42.0], [111.0, 41.0], [117.0, 41.5], [121.0, 41.0],
          [124.0, 40.0], [126.0, 41.0], [128.0, 42.0], [130.0, 42.5], [130.5, 42.0],
          [128.0, 38.5], [126.5, 37.5], [124.0, 39.8], [121.5, 39.0], [119.0, 37.5],
          [118.0, 35.0], [117.0, 33.0], [115.0, 31.0], [113.0, 29.0], [111.0, 28.0],
          [109.0, 27.0], [107.0, 26.5], [104.0, 26.0], [101.0, 25.5], [98.0, 24.5],
          [97.0, 23.5], [98.5, 22.0], [101.0, 21.5], [103.0, 22.0], [105.0, 21.5],
          [107.0, 21.0], [108.0, 21.5], [106.0, 20.0], [105.0, 18.5], [108.0, 19.5],
          [109.0, 20.0], [110.0, 21.0], [111.0, 22.5], [112.0, 23.5], [113.0, 24.5],
          [113.5, 26.0], [114.0, 28.0], [115.0, 30.0], [114.5, 32.0], [113.0, 33.0],
          [111.0, 34.5], [109.0, 36.0], [106.0, 37.0], [103.0, 38.0], [100.0, 39.0],
          [96.0, 40.0], [92.0, 40.5], [87.0, 41.0], [82.0, 40.5], [77.0, 39.5],
          [74.0, 39.0], [73.5, 39.5]
        ]]]
      }
    }]
  },

  tang: {
    type: 'FeatureCollection',
    features: [{
      type: 'Feature',
      properties: { name: '唐', year: 669 },
      geometry: {
        type: 'MultiPolygon',
        coordinates: [[[
          [70.0, 40.0], [75.0, 43.0], [80.0, 45.0], [85.0, 47.0], [90.0, 48.0],
          [95.0, 47.0], [100.0, 46.0], [105.0, 45.0], [110.0, 45.0], [115.0, 44.0],
          [120.0, 44.0], [125.0, 45.0], [128.0, 46.0], [130.0, 46.5], [131.0, 45.0],
          [130.0, 43.0], [128.0, 41.0], [126.0, 39.5], [124.0, 39.0], [121.0, 38.0],
          [119.0, 36.5], [118.0, 34.0], [116.0, 32.0], [114.0, 30.0], [112.0, 28.0],
          [110.0, 27.0], [108.0, 26.0], [106.0, 25.0], [103.0, 24.0], [100.0, 23.0],
          [98.0, 22.0], [97.0, 21.0], [98.0, 19.5], [100.0, 18.0], [102.0, 18.5],
          [104.0, 20.0], [106.0, 20.5], [108.0, 21.0], [107.0, 22.5], [105.0, 23.0],
          [103.0, 25.0], [101.0, 27.0], [99.0, 28.0], [97.0, 28.5], [95.0, 29.0],
          [92.0, 28.0], [90.0, 27.5], [88.0, 27.0], [85.0, 28.0], [82.0, 29.0],
          [80.0, 30.0], [78.0, 32.0], [76.0, 34.0], [74.0, 36.0], [72.0, 38.0],
          [70.0, 40.0]
        ]]]
      }
    }]
  },

  song: {
    type: 'FeatureCollection',
    features: [{
      type: 'Feature',
      properties: { name: '宋', year: 1111 },
      geometry: {
        type: 'MultiPolygon',
        coordinates: [[[
          [97.0, 28.0], [99.0, 30.0], [101.0, 32.0], [103.0, 34.0], [105.0, 35.0],
          [107.0, 36.0], [109.0, 37.0], [111.0, 38.0], [113.0, 39.0], [115.0, 39.5],
          [117.0, 39.5], [119.0, 38.5], [120.0, 37.5], [119.0, 35.0], [118.0, 33.0],
          [116.0, 31.0], [114.0, 29.0], [112.0, 27.5], [110.0, 26.0], [108.0, 25.0],
          [106.0, 24.0], [104.0, 23.5], [102.0, 23.0], [100.0, 22.5], [98.0, 23.0],
          [97.0, 24.0], [97.5, 26.0], [97.0, 28.0]
        ]]]
      }
    }]
  },

  yuan: {
    type: 'FeatureCollection',
    features: [{
      type: 'Feature',
      properties: { name: '元', year: 1310 },
      geometry: {
        type: 'MultiPolygon',
        coordinates: [[[
          [73.5, 39.5], [75.0, 45.0], [80.0, 48.0], [85.0, 50.0], [90.0, 51.0],
          [95.0, 52.0], [100.0, 52.0], [105.0, 52.5], [110.0, 52.0], [115.0, 50.0],
          [120.0, 48.0], [125.0, 47.0], [130.0, 46.0], [135.0, 45.0], [138.0, 44.0],
          [140.0, 42.0], [141.0, 40.0], [140.0, 38.0], [138.0, 36.0], [135.0, 34.0],
          [130.0, 32.0], [125.0, 30.0], [120.0, 28.0], [118.0, 27.0], [116.0, 26.0],
          [114.0, 24.0], [112.0, 22.0], [110.0, 20.0], [108.0, 18.0], [106.0, 17.0],
          [105.0, 19.0], [103.0, 20.0], [100.0, 21.0], [98.0, 21.0], [97.0, 23.0],
          [96.0, 25.0], [94.0, 26.0], [92.0, 27.0], [90.0, 27.5], [88.0, 27.0],
          [85.0, 28.0], [82.0, 29.0], [80.0, 30.0], [78.0, 32.0], [76.0, 34.0],
          [74.0, 36.0], [73.5, 39.5]
        ]]]
      }
    }]
  },

  ming: {
    type: 'FeatureCollection',
    features: [{
      type: 'Feature',
      properties: { name: '明', year: 1433 },
      geometry: {
        type: 'MultiPolygon',
        coordinates: [[[
          [73.5, 39.5], [76.0, 42.0], [80.0, 44.0], [85.0, 45.0], [90.0, 45.0],
          [95.0, 44.0], [100.0, 43.0], [105.0, 42.0], [110.0, 42.0], [115.0, 42.5],
          [120.0, 43.0], [125.0, 44.0], [128.0, 45.0], [130.0, 45.5], [131.0, 44.0],
          [130.0, 42.0], [128.0, 40.0], [126.0, 38.5], [124.0, 38.0], [121.0, 37.0],
          [119.0, 35.5], [118.0, 33.0], [116.0, 31.0], [114.0, 29.0], [112.0, 27.0],
          [110.0, 25.0], [108.0, 24.0], [106.0, 23.0], [104.0, 22.5], [102.0, 22.0],
          [100.0, 21.5], [98.0, 22.0], [97.0, 23.5], [97.5, 25.0], [97.0, 27.0],
          [95.0, 28.0], [92.0, 28.0], [90.0, 28.5], [88.0, 28.0], [85.0, 29.0],
          [82.0, 30.0], [80.0, 31.0], [78.0, 33.0], [76.0, 35.0], [74.0, 37.0],
          [73.5, 39.5]
        ]]]
      }
    }]
  },

  qing: {
    type: 'FeatureCollection',
    features: [{
      type: 'Feature',
      properties: { name: '清', year: 1820 },
      geometry: {
        type: 'MultiPolygon',
        coordinates: [[[
          [73.5, 39.5], [75.0, 44.0], [80.0, 48.0], [85.0, 50.0], [90.0, 51.5],
          [95.0, 52.0], [100.0, 52.5], [105.0, 52.5], [110.0, 52.0], [115.0, 50.0],
          [120.0, 48.5], [125.0, 47.5], [130.0, 46.5], [135.0, 45.0], [138.0, 44.0],
          [140.0, 42.5], [141.0, 40.5], [140.0, 38.5], [138.0, 36.5], [135.0, 34.5],
          [132.0, 33.0], [130.0, 31.0], [127.0, 29.0], [124.0, 27.0], [121.0, 25.0],
          [119.0, 23.0], [117.0, 21.0], [115.0, 19.5], [112.0, 18.0], [110.0, 17.5],
          [108.0, 18.5], [106.0, 19.5], [104.0, 20.5], [102.0, 20.0], [100.0, 19.5],
          [98.0, 20.0], [97.0, 22.0], [96.0, 24.0], [94.0, 25.5], [92.0, 26.5],
          [90.0, 27.0], [88.0, 27.0], [85.0, 28.0], [82.0, 29.0], [80.0, 30.0],
          [78.0, 32.0], [76.0, 34.0], [74.0, 36.0], [73.5, 39.5]
        ]]]
      }
    }]
  },
};

// 都城和重要城市
export const cities = {
  type: 'FeatureCollection' as const,
  features: [
    { type: 'Feature' as const, properties: { name: '镐京', type: 'capital', dynasty: 'zhou' }, geometry: { type: 'Point' as const, coordinates: [108.94, 34.34] } },
    { type: 'Feature' as const, properties: { name: '洛邑', type: 'capital', dynasty: 'spring_autumn' }, geometry: { type: 'Point' as const, coordinates: [112.45, 34.62] } },
    { type: 'Feature' as const, properties: { name: '临淄', type: 'city', dynasty: 'spring_autumn' }, geometry: { type: 'Point' as const, coordinates: [118.31, 36.82] } },
    { type: 'Feature' as const, properties: { name: '郢', type: 'city', dynasty: 'spring_autumn' }, geometry: { type: 'Point' as const, coordinates: [112.24, 30.33] } },
    { type: 'Feature' as const, properties: { name: '咸阳', type: 'capital', dynasty: 'warring_states' }, geometry: { type: 'Point' as const, coordinates: [108.72, 34.33] } },
    { type: 'Feature' as const, properties: { name: '邯郸', type: 'city', dynasty: 'warring_states' }, geometry: { type: 'Point' as const, coordinates: [114.48, 36.62] } },
    { type: 'Feature' as const, properties: { name: '临淄', type: 'city', dynasty: 'warring_states' }, geometry: { type: 'Point' as const, coordinates: [118.31, 36.82] } },
    { type: 'Feature' as const, properties: { name: '郢', type: 'city', dynasty: 'warring_states' }, geometry: { type: 'Point' as const, coordinates: [112.24, 30.33] } },
    { type: 'Feature' as const, properties: { name: '长安', type: 'capital', dynasty: 'han' }, geometry: { type: 'Point' as const, coordinates: [108.94, 34.34] } },
    { type: 'Feature' as const, properties: { name: '洛阳', type: 'city', dynasty: 'han' }, geometry: { type: 'Point' as const, coordinates: [112.45, 34.62] } },
    { type: 'Feature' as const, properties: { name: '建业', type: 'city', dynasty: 'han' }, geometry: { type: 'Point' as const, coordinates: [118.80, 32.06] } },
    { type: 'Feature' as const, properties: { name: '成都', type: 'city', dynasty: 'han' }, geometry: { type: 'Point' as const, coordinates: [104.07, 30.67] } },
    { type: 'Feature' as const, properties: { name: '邯郸', type: 'city', dynasty: 'han' }, geometry: { type: 'Point' as const, coordinates: [114.48, 36.62] } },
    { type: 'Feature' as const, properties: { name: '临淄', type: 'city', dynasty: 'han' }, geometry: { type: 'Point' as const, coordinates: [118.31, 36.82] } },
    { type: 'Feature' as const, properties: { name: '洛阳', type: 'capital', dynasty: 'han_east' }, geometry: { type: 'Point' as const, coordinates: [112.45, 34.62] } },
    { type: 'Feature' as const, properties: { name: '长安', type: 'city', dynasty: 'han_east' }, geometry: { type: 'Point' as const, coordinates: [108.94, 34.34] } },
    { type: 'Feature' as const, properties: { name: '许昌', type: 'city', dynasty: 'han_east' }, geometry: { type: 'Point' as const, coordinates: [113.85, 34.04] } },
    { type: 'Feature' as const, properties: { name: '成都', type: 'city', dynasty: 'han_east' }, geometry: { type: 'Point' as const, coordinates: [104.07, 30.67] } },
    { type: 'Feature' as const, properties: { name: '建康', type: 'capital', dynasty: 'jin_east' }, geometry: { type: 'Point' as const, coordinates: [118.80, 32.06] } },
    { type: 'Feature' as const, properties: { name: '洛阳', type: 'capital', dynasty: 'jin' }, geometry: { type: 'Point' as const, coordinates: [112.45, 34.62] } },
    { type: 'Feature' as const, properties: { name: '长安', type: 'capital', dynasty: 'tang' }, geometry: { type: 'Point' as const, coordinates: [108.94, 34.34] } },
    { type: 'Feature' as const, properties: { name: '洛阳', type: 'city', dynasty: 'tang' }, geometry: { type: 'Point' as const, coordinates: [112.45, 34.62] } },
    { type: 'Feature' as const, properties: { name: '扬州', type: 'city', dynasty: 'tang' }, geometry: { type: 'Point' as const, coordinates: [119.42, 32.39] } },
    { type: 'Feature' as const, properties: { name: '成都', type: 'city', dynasty: 'tang' }, geometry: { type: 'Point' as const, coordinates: [104.07, 30.67] } },
    { type: 'Feature' as const, properties: { name: '广州', type: 'city', dynasty: 'tang' }, geometry: { type: 'Point' as const, coordinates: [113.26, 23.13] } },
    { type: 'Feature' as const, properties: { name: '汴京', type: 'capital', dynasty: 'song' }, geometry: { type: 'Point' as const, coordinates: [114.35, 34.79] } },
    { type: 'Feature' as const, properties: { name: '临安', type: 'capital', dynasty: 'song_south' }, geometry: { type: 'Point' as const, coordinates: [120.16, 30.29] } },
    { type: 'Feature' as const, properties: { name: '大都', type: 'capital', dynasty: 'yuan' }, geometry: { type: 'Point' as const, coordinates: [116.40, 39.90] } },
    { type: 'Feature' as const, properties: { name: '南京', type: 'capital', dynasty: 'ming' }, geometry: { type: 'Point' as const, coordinates: [118.80, 32.06] } },
    { type: 'Feature' as const, properties: { name: '北京', type: 'city', dynasty: 'ming' }, geometry: { type: 'Point' as const, coordinates: [116.40, 39.90] } },
    { type: 'Feature' as const, properties: { name: '京师', type: 'capital', dynasty: 'qing' }, geometry: { type: 'Point' as const, coordinates: [116.40, 39.90] } },
  ]
};

// 主要河流
export const rivers = {
  type: 'FeatureCollection' as const,
  features: [
    {
      type: 'Feature' as const,
      properties: { name: '黄河', type: 'river-major' },
      geometry: {
        type: 'LineString' as const,
        coordinates: [
          [96.0, 35.0], [99.0, 36.0], [102.0, 36.5], [104.0, 36.0], [106.0, 37.5],
          [108.0, 38.5], [110.0, 39.0], [111.0, 40.0], [112.0, 40.5], [113.0, 40.0],
          [112.0, 38.0], [111.0, 36.0], [110.0, 34.5], [111.0, 34.8], [113.0, 35.0],
          [115.0, 35.5], [117.0, 36.5], [118.0, 37.0], [119.0, 37.5]
        ]
      }
    },
    {
      type: 'Feature' as const,
      properties: { name: '长江', type: 'river-major' },
      geometry: {
        type: 'LineString' as const,
        coordinates: [
          [97.0, 33.0], [100.0, 32.0], [103.0, 31.0], [105.0, 30.0], [107.0, 29.5],
          [109.0, 30.5], [111.0, 30.0], [112.0, 30.5], [114.0, 30.5], [115.0, 30.0],
          [116.0, 30.0], [117.0, 31.0], [118.0, 32.0], [119.0, 32.0], [120.0, 32.0],
          [121.0, 31.5], [121.5, 31.2]
        ]
      }
    },
    {
      type: 'Feature' as const,
      properties: { name: '珠江', type: 'river' },
      geometry: {
        type: 'LineString' as const,
        coordinates: [
          [103.0, 25.0], [106.0, 24.5], [109.0, 24.0], [110.0, 23.5], [112.0, 23.0],
          [113.0, 23.1], [113.5, 22.8]
        ]
      }
    },
    {
      type: 'Feature' as const,
      properties: { name: '大运河', type: 'river' },
      geometry: {
        type: 'LineString' as const,
        coordinates: [
          [116.4, 39.9], [117.0, 38.5], [117.5, 37.0], [118.0, 35.5], [119.0, 34.0],
          [119.5, 32.5], [120.0, 31.0], [120.2, 30.3]
        ]
      }
    },
  ]
};
