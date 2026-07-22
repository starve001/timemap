'use client';

import { useState, useCallback } from 'react';
import { useHistoryStore } from '@/lib/store';
import { dynasties } from '@/data/dynasties';
import { historyEvents } from '@/data/events/events';
import { findDynasty, formatYear } from '@/lib/utils';

const categoryColors: Record<string, string> = {
  war: 'bg-cinnabar',
  politics: 'bg-gold',
  culture: 'bg-jade',
  economy: 'bg-blue-500',
  technology: 'bg-indigo-500',
};

export default function MobileDrawer() {
  const { map: mapState, setCurrentDynasty, selectEvent } = useHistoryStore();
  const [expanded, setExpanded] = useState(false);
  const currentDynasty = findDynasty(dynasties, mapState.currentDynastyId);
  const dynastyEvents = historyEvents.filter((e) => e.dynastyId === mapState.currentDynastyId);

  const handleEventClick = useCallback((eventId: string) => {
    selectEvent(eventId);
  }, [selectEvent]);

  if (!currentDynasty) return null;

  return (
    <>
      {/* 底部抽屉 - 仅在 md 以下显示 */}
      <div className="md:hidden fixed bottom-0 left-0 right-0 z-30 bg-white border-t border-bamboo shadow-2xl transition-transform duration-300 ease-out"
        style={{
          height: expanded ? '60vh' : 'auto',
          transform: expanded ? 'translateY(0)' : 'translateY(0)',
        }}
      >
        {/* 拖拽手柄 */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full flex flex-col items-center py-2 touch-none"
        >
          <div className={`w-10 h-1 rounded-full bg-bamboo transition-transform duration-300 ${expanded ? 'rotate-180' : ''}`} />
        </button>

        {/* 朝代名 + 折叠摘要 */}
        {!expanded && (
          <button
            onClick={() => setExpanded(true)}
            className="w-full px-4 pb-3 flex items-center gap-2 text-left"
          >
            <span
              className="inline-block w-2.5 h-2.5 rounded-full flex-shrink-0"
              style={{ background: currentDynasty.color }}
            />
            <span className="font-serif text-sm font-bold" style={{ color: currentDynasty.color }}>
              {currentDynasty.name}
            </span>
            <span className="text-[10px] text-ink-500 tabular-nums">
              {formatYear(currentDynasty.startYear)} — {formatYear(currentDynasty.endYear)}
            </span>
            <span className="ml-auto text-[10px] text-ink-300">点击展开详情</span>
          </button>
        )}

        {/* 展开内容 */}
        {expanded && (
          <div className="px-4 pb-4 overflow-y-auto" style={{ maxHeight: 'calc(60vh - 40px)' }}>
            {/* 朝代导航 */}
            <div className="mb-3">
              <h3 className="font-serif text-xs font-semibold text-ink-900 mb-2">朝代导航</h3>
              <div className="flex flex-wrap gap-1">
                {dynasties.map((d) => (
                  <button
                    key={d.id}
                    onClick={() => {
                      setCurrentDynasty(d.id);
                    }}
                    className={`px-2 py-0.5 rounded-full text-[10px] font-serif transition-all ${
                      d.id === mapState.currentDynastyId
                        ? 'text-white'
                        : 'bg-silk text-ink-500'
                    }`}
                    style={d.id === mapState.currentDynastyId ? { background: d.color } : undefined}
                  >
                    {d.name}
                  </button>
                ))}
              </div>
            </div>

            {/* 朝代信息 */}
            <div className="bg-silk rounded-lg p-2.5 border border-bamboo mb-3">
              <h4 className="font-serif text-sm font-semibold text-ink-900">
                {currentDynasty.name}
              </h4>
              <p className="text-[10px] text-ink-500 mt-0.5">
                {formatYear(currentDynasty.startYear)} — {formatYear(currentDynasty.endYear)}
                {' · '}共 {currentDynasty.endYear - currentDynasty.startYear} 年
              </p>
              {currentDynasty.description && (
                <p className="text-[10px] text-ink-500 mt-1.5 leading-relaxed">{currentDynasty.description}</p>
              )}
            </div>

            {/* 事件列表 */}
            <div>
              <h3 className="font-serif text-xs font-semibold text-ink-900 mb-2">重大事件 ({dynastyEvents.length})</h3>
              <div className="flex flex-col gap-1">
                {dynastyEvents.map((event) => (
                  <button
                    key={event.id}
                    onClick={() => handleEventClick(event.id)}
                    className={`flex items-start gap-2 p-2 rounded-md border text-left transition-all ${
                      mapState.selectedEventId === event.id
                        ? 'border-cinnabar bg-cinnabar/5'
                        : 'border-bamboo'
                    }`}
                  >
                    <div className={`w-1.5 h-1.5 rounded-full mt-1 flex-shrink-0 ${categoryColors[event.category] || 'bg-gold'}`} />
                    <div className="min-w-0 flex-1">
                      <div className="text-[9px] text-ink-300 tabular-nums">
                        {formatYear(event.startYear)}
                      </div>
                      <div className="text-[11px] font-medium text-ink-700 truncate">{event.title}</div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
