'use client';

import { useEffect } from 'react';
import { useHistoryStore } from '@/lib/store';
import { dynasties } from '@/data/dynasties';
import { dynastyIndex } from '@/lib/utils';

export default function KeyboardNav() {
  const { map, setCurrentDynasty, toggleTheme } = useHistoryStore();

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // 忽略输入框中的按键
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      const idx = dynastyIndex(dynasties, map.currentDynastyId);

      if (e.key === 'ArrowRight' && idx < dynasties.length - 1) {
        setCurrentDynasty(dynasties[idx + 1].id);
      } else if (e.key === 'ArrowLeft' && idx > 0) {
        setCurrentDynasty(dynasties[idx - 1].id);
      } else if (e.key === 't' || e.key === 'T') {
        toggleTheme();
      }
    };

    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [map.currentDynastyId, setCurrentDynasty, toggleTheme]);

  return null;
}
