'use client';

import { useState, useEffect } from 'react';

export default function AboutModal() {
  const [open, setOpen] = useState(false);

  // 快捷键 Ctrl+H 打开
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'h') {
        e.preventDefault();
        setOpen((v) => !v);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  // 暴露给全局，让 Header 按钮可以触发
  useEffect(() => {
    (window as unknown as { __openAbout?: () => void }).__openAbout = () => setOpen(true);
    return () => {
      delete (window as unknown as { __openAbout?: () => void }).__openAbout;
    };
  }, []);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={() => setOpen(false)}
    >
      <div
        className="bg-white rounded-xl shadow-2xl max-w-lg w-[90vw] max-h-[80vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 标题栏 */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-bamboo sticky top-0 bg-white">
          <h2 className="font-serif text-base font-bold text-ink-900">关于与数据来源</h2>
          <button
            onClick={() => setOpen(false)}
            className="w-7 h-7 rounded-md hover:bg-silk flex items-center justify-center text-ink-400"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M1 1l12 12M13 1L1 13" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        <div className="px-5 py-4 space-y-4 text-sm text-ink-700">
          {/* 项目简介 */}
          <div>
            <h3 className="font-serif font-semibold text-ink-900 mb-1">中国时序地图</h3>
            <p className="text-xs text-ink-500 leading-relaxed">
              以时间轴 + 交互地图探索中国五千年历史疆域变迁，覆盖夏商周至清末共 19 个朝代/时期。
            </p>
          </div>

          {/* 数据来源 */}
          <div>
            <h3 className="font-serif font-semibold text-ink-900 mb-2">数据来源</h3>
            <div className="space-y-2 text-xs">
              <div className="bg-silk rounded-lg p-3 border border-bamboo">
                <div className="font-medium text-ink-900">谭其骧《中国历史地图集》</div>
                <div className="text-ink-500 mt-0.5">
                  中研院 WMTS 在线服务 · 学术/教育用途
                </div>
                <a
                  href="https://gis.sinica.edu.tw/ccts"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-cinnabar hover:underline mt-1 inline-block"
                >
                  gis.sinica.edu.tw/ccts →
                </a>
              </div>
              <div className="bg-silk rounded-lg p-3 border border-bamboo">
                <div className="font-medium text-ink-900">OpenFreeMap</div>
                <div className="text-ink-500 mt-0.5">
                  免费矢量底图 · 基于 OpenStreetMap · ODbL 许可
                </div>
                <a
                  href="https://openfreemap.org/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-cinnabar hover:underline mt-1 inline-block"
                >
                  openfreemap.org →
                </a>
              </div>
              <div className="bg-silk rounded-lg p-3 border border-bamboo">
                <div className="font-medium text-ink-900">朝代与事件数据</div>
                <div className="text-ink-500 mt-0.5">
                  公开历史资料整理 · 可能有误差，以权威史料为准
                </div>
              </div>
            </div>
          </div>

          {/* AI 操作声明 */}
          <div>
            <h3 className="font-serif font-semibold text-ink-900 mb-2">AI 操作声明</h3>
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs space-y-1.5">
              <p className="text-ink-700">
                <span className="font-medium">本项目使用 AI 辅助开发。</span>
                前端代码、WMTS 对接、朝代/事件数据、架构文档均由 AI 生成或辅助整理。
              </p>
              <p className="text-ink-500">
                人工负责需求定义、方向决策、效果审核与数据质量把关。历史数据可能存在偏差，欢迎勘误。
              </p>
            </div>
          </div>

          {/* 开源许可 */}
          <div>
            <h3 className="font-serif font-semibold text-ink-900 mb-1">开源许可</h3>
            <p className="text-xs text-ink-500">
              代码采用 <span className="font-medium text-ink-700">MIT License</span>。
              历史地图瓦片版权归中研院及谭其骧先生相关权利人。
            </p>
          </div>

          {/* 快捷键提示 */}
          <div className="text-center text-[10px] text-ink-300 pt-1">
            按 Ctrl+H 可随时打开此面板
          </div>
        </div>
      </div>
    </div>
  );
}
