'use client';

import { useHistoryStore } from '@/lib/store';
import HistoryMap from '@/components/map/HistoryMap';
import Timeline from '@/components/timeline/Timeline';
import Sidebar from '@/components/ui/Sidebar';
import ThemeProvider from '@/components/ui/ThemeProvider';
import KeyboardNav from '@/components/ui/KeyboardNav';
import AboutModal from '@/components/ui/AboutModal';
import MobileDrawer from '@/components/ui/MobileDrawer';

export default function Home() {
  const { theme, toggleTheme, map, toggleCompare } = useHistoryStore();

  return (
    <ThemeProvider>
      <KeyboardNav />
      <AboutModal />
      <div className="h-[100dvh] flex flex-col overflow-hidden">
        {/* Header */}
        <header className="flex items-center justify-between px-4 py-3 bg-white border-b border-bamboo z-50">
          <div className="flex items-center gap-2.5">
            <svg className="w-8 h-8 text-cinnabar" viewBox="0 0 32 32" fill="none">
              <rect x="4" y="6" width="24" height="20" rx="3" stroke="currentColor" strokeWidth="2"/>
              <path d="M4 14h24" stroke="currentColor" strokeWidth="1.5"/>
              <circle cx="16" cy="16" r="4" fill="currentColor" opacity="0.25"/>
              <circle cx="16" cy="16" r="2" fill="currentColor"/>
            </svg>
            <h1 className="font-serif text-lg font-bold text-ink-900">中国时序地图</h1>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => (window as unknown as { __openAbout?: () => void }).__openAbout?.()}
              className="w-10 h-10 rounded-md border border-bamboo text-ink-500 hover:bg-silk flex items-center justify-center transition-colors"
              title="关于与数据来源 (Ctrl+H)"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M8 7a.5.5 0 0 1 .5.5v3a.5.5 0 0 1-1 0v-3A.5.5 0 0 1 8 7zm0-3a.75.75 0 1 1 0 1.5A.75.75 0 0 1 8 4zM8 0a8 8 0 1 0 0 16A8 8 0 0 0 8 0z"/>
              </svg>
            </button>
            <button
              onClick={toggleCompare}
              className={`w-10 h-10 rounded-md border flex items-center justify-center transition-colors ${
                map.compareMode
                  ? 'border-cinnabar text-cinnabar bg-cinnabar/5'
                  : 'border-bamboo text-ink-500 hover:bg-silk'
              }`}
              title="对比模式"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <rect x="1" y="3" width="6" height="10" rx="1" stroke="currentColor" fill="none"/>
                <rect x="9" y="1" width="6" height="12" rx="1" stroke="currentColor" fill="none"/>
              </svg>
            </button>
            <button
              onClick={toggleTheme}
              className="w-10 h-10 rounded-md border border-bamboo text-ink-500 hover:bg-silk flex items-center justify-center transition-colors"
              title="切换主题"
            >
              {theme === 'light' ? (
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M8 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM8 0a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-1 0v-2A.5.5 0 0 1 8 0zm0 13a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-1 0v-2A.5.5 0 0 1 8 13zm8-5a.5.5 0 0 1-.5.5h-2a.5.5 0 0 1 0-1h2a.5.5 0 0 1 .5.5zM3 8a.5.5 0 0 1-.5.5h-2a.5.5 0 0 1 0-1h2A.5.5 0 0 1 3 8zm10.657-5.657a.5.5 0 0 1 0 .707l-1.414 1.415a.5.5 0 1 1-.707-.708l1.414-1.414a.5.5 0 0 1 .707 0zm-9.193 9.193a.5.5 0 0 1 0 .707L3.05 13.657a.5.5 0 0 1-.707-.707l1.414-1.414a.5.5 0 0 1 .707 0zm9.193 2.121a.5.5 0 0 1-.707 0l-1.414-1.414a.5.5 0 0 1 .707-.707l1.414 1.414a.5.5 0 0 1 0 .707zM4.464 4.465a.5.5 0 0 1-.707 0L2.343 3.05a.5.5 0 1 1 .707-.707l1.414 1.414a.5.5 0 0 1 0 .708z"/>
                </svg>
              ) : (
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M6 .278a.768.768 0 0 1 .08.858 7.208 7.208 0 0 0-.878 3.46c0 4.021 3.278 7.277 7.318 7.277.527 0 1.04-.055 1.533-.16a.787.787 0 0 1 .81.316.733.733 0 0 1-.031.893A8.349 8.349 0 0 1 8.344 16C3.734 16 0 12.286 0 7.71 0 4.266 2.114 1.312 5.124.06A.752.752 0 0 1 6 .278z"/>
                </svg>
              )}
            </button>
          </div>
        </header>

        {/* Main */}
        <main className="flex-1 flex overflow-hidden">
          {/* Map */}
          <div className="flex-1 relative">
            <HistoryMap />
          </div>

          {/* Sidebar - 桌面端 */}
          <div className="hidden md:block">
            <Sidebar />
          </div>

          {/* MobileDrawer - 移动端 */}
          <MobileDrawer />
        </main>

        {/* Timeline */}
        <Timeline />
      </div>
    </ThemeProvider>
  );
}
