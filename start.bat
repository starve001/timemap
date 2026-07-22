@echo off
chcp 65001 >nul 2>&1
title 中国时序地图 - ChronoMap CN

echo.
echo   ╔══════════════════════════════════════╗
echo   ║   中国时序地图 · ChronoMap CN       ║
echo   ╚══════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: 检查静态文件是否已构建
if not exist "out\index.html" (
  echo   [提示] 尚未构建静态文件，正在构建...
  echo.
  :: 检查 node_modules
  if not exist "node_modules" (
    echo   [1/2] 安装依赖...
    call npm install
    if errorlevel 1 (
      echo.
      echo   ❌ 依赖安装失败，请确保已安装 Node.js 18+
      echo   下载地址: https://nodejs.org
      pause
      exit /b 1
    )
    echo.
  )
  :: 构建静态文件
  echo   [2/2] 构建静态文件...
  call npm run build
  if errorlevel 1 (
    echo.
    echo   ❌ 构建失败
    pause
    exit /b 1
  )
  echo.
  echo   ✓ 构建完成！
  echo.
)

:: 使用 PowerShell 内置 HTTP 服务器（零依赖）
echo   正在启动静态服务器...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0serve.ps1"

if errorlevel 1 (
  echo.
  echo   ❌ 服务器启动失败
  pause
)
