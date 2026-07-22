'use client';

import { useHistoryStore } from '@/lib/store';
import { dynasties } from '@/data/dynasties';
import { historyEvents } from '@/data/events/events';
import { findDynasty, formatYear } from '@/lib/utils';
import { useCallback } from 'react';

const categoryColors: Record<string, string> = {
  war: 'bg-cinnabar',
  politics: 'bg-gold',
  culture: 'bg-jade',
  economy: 'bg-blue-500',
  technology: 'bg-indigo-500',
};

const categoryLabels: Record<string, string> = {
  war: '战争',
  politics: '政治',
  culture: '文化',
  economy: '经济',
  technology: '科技',
};

export default function Sidebar() {
  const { map: mapState, setCurrentDynasty, selectEvent } = useHistoryStore();
  const currentDynasty = findDynasty(dynasties, mapState.currentDynastyId);
  const dynastyEvents = historyEvents.filter((e) => e.dynastyId === mapState.currentDynastyId);

  const handleEventClick = useCallback((eventId: string) => {
    selectEvent(eventId);
  }, [selectEvent]);

  if (!currentDynasty) return null;

  return (
    <aside className="w-[340px] bg-white border-l border-bamboo flex flex-col overflow-y-auto">
      <div className="p-4 flex flex-col gap-4">
        {/* 朝代选择 */}
        <div>
          <h3 className="font-serif text-sm font-semibold text-ink-900 mb-2">朝代导航</h3>
          <div className="flex flex-wrap gap-1.5">
            {dynasties.map((d) => (
              <button
                key={d.id}
                onClick={() => setCurrentDynasty(d.id)}
                className={`px-2.5 py-1 rounded-full text-xs font-serif transition-all ${
                  d.id === mapState.currentDynastyId
                    ? 'text-white shadow-sm'
                    : 'bg-silk text-ink-500 hover:bg-bamboo'
                }`}
                style={d.id === mapState.currentDynastyId ? { background: d.color } : undefined}
              >
                {d.name}
              </button>
            ))}
          </div>
        </div>

        {/* 朝代信息 */}
        <div className="bg-silk rounded-lg p-3 border border-bamboo">
          <h4 className="font-serif text-base font-semibold text-ink-900">
            {currentDynasty.name}朝
          </h4>
          <p className="text-xs text-ink-500 mt-1">
            {formatYear(currentDynasty.startYear)} — {formatYear(currentDynasty.endYear)}
            {' '}·{' '}
            共 {currentDynasty.endYear - currentDynasty.startYear} 年
          </p>
          {currentDynasty.description && (
            <p className="text-xs text-ink-500 mt-2 leading-relaxed">{currentDynasty.description}</p>
          )}
        </div>

        {/* 事件列表 */}
        <div>
          <h3 className="font-serif text-sm font-semibold text-ink-900 mb-2">重大事件</h3>
          <div className="flex flex-col gap-1.5">
            {dynastyEvents.map((event) => (
              <button
                key={event.id}
                onClick={() => handleEventClick(event.id)}
                className={`flex items-start gap-2.5 p-2.5 rounded-md border text-left transition-all hover:bg-silk ${
                  mapState.selectedEventId === event.id
                    ? 'border-cinnabar bg-cinnabar/5'
                    : 'border-bamboo'
                }`}
              >
                <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${categoryColors[event.category] || 'bg-gold'}`} />
                <div className="min-w-0">
                  <div className="text-[10px] text-ink-300 tabular-nums">
                    {formatYear(event.startYear)}
                    {event.endYear && event.endYear !== event.startYear
                      ? ` — ${formatYear(event.endYear)}`
                      : ''}
                  </div>
                  <div className="text-xs font-medium text-ink-700 truncate">{event.title}</div>
                  <div className="text-[10px] text-ink-500 mt-0.5 line-clamp-2">{event.description}</div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* 数据统计 */}
        <div className="bg-silk rounded-lg p-3 border border-bamboo">
          <h4 className="font-serif text-xs font-semibold text-ink-900 mb-2">统计</h4>
          <div className="grid grid-cols-3 gap-2 text-center">
            <div>
              <div className="text-lg font-bold text-cinnabar">{dynastyEvents.length}</div>
              <div className="text-[10px] text-ink-500">事件</div>
            </div>
            <div>
              <div className="text-lg font-bold text-gold">
                {dynastyEvents.filter((e) => e.importance >= 4).length}
              </div>
              <div className="text-[10px] text-ink-500">重大事件</div>
            </div>
            <div>
              <div className="text-lg font-bold text-jade">
                {dynastyEvents.filter((e) => e.category === 'culture').length}
              </div>
              <div className="text-[10px] text-ink-500">文化事件</div>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
