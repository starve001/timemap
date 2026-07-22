import { create } from 'zustand';
import type { MapState, TimelineState } from '@/types';
import { TIME_START, TIME_END } from '@/data/dynasties';

interface HistoryStore {
  // Map
  map: MapState;
  setMapCenter: (center: [number, number]) => void;
  setMapZoom: (zoom: number) => void;
  setCurrentDynasty: (dynastyId: string) => void;
  selectEvent: (eventId?: string) => void;
  toggleCompare: () => void;
  setCompareDynasty: (dynastyId?: string) => void;

  // Timeline
  timeline: TimelineState;
  setTimelineRange: (start: number, end: number) => void;
  setCursorYear: (year: number) => void;
  setZoomLevel: (level: TimelineState['zoomLevel']) => void;

  // Theme
  theme: 'light' | 'dark';
  toggleTheme: () => void;
}

export const useHistoryStore = create<HistoryStore>((set) => ({
  map: {
    center: [108.94, 34.34],
    zoom: 3.5,
    currentDynastyId: 'han',
    selectedEventId: undefined,
    compareMode: false,
    compareDynastyId: undefined,
  },
  setMapCenter: (center) =>
    set((s) => ({ map: { ...s.map, center } })),
  setMapZoom: (zoom) =>
    set((s) => ({ map: { ...s.map, zoom } })),
  setCurrentDynasty: (dynastyId) =>
    set((s) => ({
      map: { ...s.map, currentDynastyId: dynastyId, selectedEventId: undefined },
    })),
  selectEvent: (eventId) =>
    set((s) => ({ map: { ...s.map, selectedEventId: eventId } })),
  toggleCompare: () =>
    set((s) => ({ map: { ...s.map, compareMode: !s.map.compareMode } })),
  setCompareDynasty: (dynastyId) =>
    set((s) => ({ map: { ...s.map, compareDynastyId: dynastyId } })),

  timeline: {
    rangeStart: TIME_START,
    rangeEnd: TIME_END,
    cursorYear: -100,
    zoomLevel: 'dynasty',
  },
  setTimelineRange: (start, end) =>
    set((s) => ({ timeline: { ...s.timeline, rangeStart: start, rangeEnd: end } })),
  setCursorYear: (year) =>
    set((s) => ({ timeline: { ...s.timeline, cursorYear: year } })),
  setZoomLevel: (level) =>
    set((s) => ({ timeline: { ...s.timeline, zoomLevel: level } })),

  theme: 'light',
  toggleTheme: () =>
    set((s) => ({ theme: s.theme === 'light' ? 'dark' : 'light' })),
}));
