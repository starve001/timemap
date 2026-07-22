import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: '中国时序地图 — 历史长河',
  description: '以时间轴和交互地图探索中国五千年历史疆域变迁。历史地图数据来源：中研院谭其骧《中国历史地图集》WMTS 服务。',
  authors: [{ name: 'mapcn' }],
  keywords: ['中国历史', '历史地图', '谭其骧', '时序地图', '朝代变迁', 'MapLibre'],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600;700&family=Noto+Serif+SC:wght@600;700;900&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="antialiased">{children}</body>
    </html>
  );
}
