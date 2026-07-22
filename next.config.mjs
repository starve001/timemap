/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ['maplibre-gl'],
  // 静态导出：生成纯 HTML/CSS/JS 到 out/ 目录，无需 Node.js 服务器
  output: 'export',
  images: {
    // 静态导出不支持图片优化
    unoptimized: true,
  },
};

export default nextConfig;
