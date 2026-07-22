'use client';

import { useRef, useEffect, useCallback } from 'react';
import { useHistoryStore } from '@/lib/store';
import { dynasties } from '@/data/dynasties';
import { timeToX, formatYear, dynastyMidYear, findDynasty } from '@/lib/utils';

const TRACK_WIDTH = 1800;
const TRACK_HEIGHT = 56;

export default function Timeline() {
  const scrollRef = useRef<HTMLDivElement>(null);
  const trackRef = useRef<HTMLDivElement>(null);
  const { map, setCurrentDynasty } = useHistoryStore();

  const currentDynasty = findDynasty(dynasties, map.currentDynastyId);

  // 渲染时间轴
  useEffect(() => {
    const track = trackRef.current;
    if (!track) return;

    // 清除旧内容
    track.querySelectorAll('.tl-era, .tl-marker, .tl-marker-label, .tl-cursor').forEach((el) => el.remove());

    // 朝代条
    dynasties.forEach((d) => {
      const isActive = d.id === map.currentDynastyId;
      const x = timeToX(d.startYear, TRACK_WIDTH);
      const w = Math.max(timeToX(d.endYear, TRACK_WIDTH) - x, 18);

      const era = document.createElement('div');
      era.className = `tl-era absolute top-0 h-full cursor-pointer transition-opacity duration-200 ${
        isActive ? 'opacity-100' : 'opacity-50 hover:opacity-80'
      }`;
      era.dataset.dynasty = d.id;

      const bar = document.createElement('div');
      bar.className = 'absolute rounded-full transition-all duration-250';
      bar.style.cssText = `left:${x}px;width:${w}px;top:${isActive ? '18px' : '22px'};height:${isActive ? '22px' : '16px'};background:${d.color}`;

      const label = document.createElement('div');
      label.className = `absolute left-1/2 -translate-x-1/2 text-[10px] font-serif whitespace-nowrap transition-colors ${
        isActive ? 'text-cinnabar font-bold' : 'text-ink-500'
      }`;
      label.style.top = '0px';
      label.textContent = d.name;

      era.appendChild(bar);
      era.appendChild(label);
      era.addEventListener('click', () => setCurrentDynasty(d.id));
      track.appendChild(era);
    });

    // 世纪刻度
    for (let y = -2000; y <= 2000; y += 100) {
      if (y === 0) continue;
      const isMajor = y % 500 === 0;
      const x = timeToX(y, TRACK_WIDTH);

      const marker = document.createElement('div');
      marker.className = `tl-marker absolute w-px transition-all ${isMajor ? 'bg-ink-500' : 'bg-ink-300'}`;
      marker.style.cssText = `left:${x}px;top:${isMajor ? '4px' : '10px'};height:${isMajor ? '48px' : '36px'}`;
      track.appendChild(marker);

      if (isMajor) {
        const label = document.createElement('div');
        label.className = 'tl-marker-label absolute text-[9px] text-ink-300 whitespace-nowrap tabular-nums';
        label.style.cssText = `left:${x}px;bottom:0;transform:translateX(-50%)`;
        label.textContent = formatYear(y);
        track.appendChild(label);
      }
    }

    // 游标
    if (currentDynasty) {
      const cursor = document.createElement('div');
      cursor.className = 'tl-cursor absolute w-[3px] bg-cinnabar rounded-sm z-10 pointer-events-none transition-all duration-300';
      const midX = timeToX(dynastyMidYear(currentDynasty), TRACK_WIDTH);
      cursor.style.cssText = `left:${midX}px;top:8px;height:40px`;
      track.appendChild(cursor);
    }

    // 滚动到当前朝代
    if (currentDynasty && scrollRef.current) {
      const midX = timeToX(dynastyMidYear(currentDynasty), TRACK_WIDTH);
      scrollRef.current.scrollLeft = Math.max(0, midX - 250);
    }
  }, [map.currentDynastyId, currentDynasty, setCurrentDynasty]);

  // 点击时间轴跳转
  const handleTrackClick = useCallback(
    (e: React.MouseEvent) => {
      if (!trackRef.current || !scrollRef.current) return;
      const rect = trackRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left + scrollRef.current.scrollLeft;
      const year = Math.round((x / TRACK_WIDTH) * 4200 + (-2200));

      // 找最近的朝代
      let nearest = dynasties[0];
      let minDist = Infinity;
      dynasties.forEach((d) => {
        const mid = dynastyMidYear(d);
        const dist = Math.abs(year - mid);
        if (dist < minDist) {
          minDist = dist;
          nearest = d;
        }
      });

      if (nearest.id !== map.currentDynastyId) {
        setCurrentDynasty(nearest.id);
      }
    },
    [map.currentDynastyId, setCurrentDynasty]
  );

  return (
    <div className="bg-white border-t border-bamboo">
      {/* 密度热力条 */}
      <div className="flex gap-px px-4 pt-3 pb-1" id="density-bar">
        {Array.from({ length: 40 }).map((_, i) => {
          const d = currentDynasty;
          let cls = 'bg-bamboo';
          if (d) {
            const start = ((d.startYear + 2200) / 4200) * 40;
            const end = ((d.endYear + 2200) / 4200) * 40;
            if (i >= start && i <= end) {
              const r = (i * 7 + 13) % 10; // deterministic pseudo-random
              cls = r > 7 ? 'bg-cinnabar/60' : r > 4 ? 'bg-gold-light/70' : 'bg-bamboo';
            }
          }
          return <div key={i} className={`flex-1 h-1.5 rounded-sm transition-colors ${cls}`} />;
        })}
      </div>

      {/* 时间轴 */}
      <div
        ref={scrollRef}
        className="overflow-x-auto overflow-y-hidden scrollbar-thin scrollbar-thumb-ink-300"
        style={{ scrollbarWidth: 'thin' }}
      >
        <div
          ref={trackRef}
          className="relative cursor-pointer"
          style={{ width: TRACK_WIDTH, height: TRACK_HEIGHT }}
          onClick={handleTrackClick}
        />
      </div>

      {/* 图例 */}
      <div className="flex items-center gap-4 px-4 py-1.5 text-[10px] text-ink-300">
        <span className="inline-flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-cinnabar inline-block" /> 战争</span>
        <span className="inline-flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-gold inline-block" /> 政治</span>
        <span className="inline-flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-jade inline-block" /> 文化</span>
        <span className="ml-auto inline-flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-bamboo inline-block" /> 低</span>
        <span className="inline-flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-gold-light/70 inline-block" /> 中</span>
        <span className="inline-flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-cinnabar/60 inline-block" /> 高</span>
      </div>
    </div>
  );
}
