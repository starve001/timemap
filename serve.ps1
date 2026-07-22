# serve.ps1 — 零依赖静态文件服务器
# 使用 Windows 内置 .NET HttpListener，无需安装 Node.js / Python
# 参考项目 china-history-map-main 的"双击即用"理念

param(
    [string]$Root = "",
    [int]$Port = 8080
)

# 自动定位 out/ 目录
if (-not $Root -or $Root -eq "") {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    if (-not $scriptDir) { $scriptDir = $PSScriptRoot }
    if (-not $scriptDir) { $scriptDir = Get-Location }
    $Root = Join-Path $scriptDir "out"
}

# 检查 out/ 目录是否存在
if (-not (Test-Path $Root -PathType Container)) {
    Write-Host ""
    Write-Host "  [错误] 未找到静态文件目录: $Root" -ForegroundColor Red
    Write-Host ""
    Write-Host "  请先运行构建:" -ForegroundColor Yellow
    Write-Host "    1. 安装 Node.js (https://nodejs.org)" -ForegroundColor Gray
    Write-Host "    2. 在项目目录运行: npm install" -ForegroundColor Gray
    Write-Host "    3. 在项目目录运行: npm run build" -ForegroundColor Gray
    Write-Host "    4. 再次运行本脚本" -ForegroundColor Gray
    Write-Host ""
    Read-Host "按回车键退出"
    exit 1
}

$fullRoot = (Resolve-Path $Root).Path

# MIME 类型映射
$mimeTypes = @{
    '.html'  = 'text/html; charset=utf-8'
    '.htm'   = 'text/html; charset=utf-8'
    '.css'   = 'text/css; charset=utf-8'
    '.js'    = 'application/javascript; charset=utf-8'
    '.mjs'   = 'application/javascript; charset=utf-8'
    '.json'  = 'application/json; charset=utf-8'
    '.png'   = 'image/png'
    '.jpg'   = 'image/jpeg'
    '.jpeg'  = 'image/jpeg'
    '.gif'   = 'image/gif'
    '.svg'   = 'image/svg+xml'
    '.ico'   = 'image/x-icon'
    '.webp'  = 'image/webp'
    '.woff'  = 'font/woff'
    '.woff2' = 'font/woff2'
    '.ttf'   = 'font/ttf'
    '.eot'   = 'application/vnd.ms-fontobject'
    '.txt'   = 'text/plain; charset=utf-8'
    '.map'   = 'application/json'
    '.wasm'  = 'application/wasm'
}

# 尝试启动 HTTP 监听器（端口被占用时自动递增）
$listener = $null
$attempts = 0
$maxAttempts = 5
while ($attempts -lt $maxAttempts) {
    try {
        $listener = New-Object System.Net.HttpListener
        $listener.Prefixes.Add("http://localhost:$Port/")
        $listener.Start()
        break
    } catch {
        $attempts++
        Write-Host "  端口 $Port 被占用，尝试 $($Port + 1)..." -ForegroundColor Yellow
        $Port++
        if ($attempts -ge $maxAttempts) {
            Write-Host "  [错误] 无法启动服务器，所有端口都被占用" -ForegroundColor Red
            Read-Host "按回车键退出"
            exit 1
        }
    }
}

Write-Host ""
Write-Host "  ╔══════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║        中国时序地图 · 静态服务器          ║" -ForegroundColor Cyan
Write-Host "  ╠══════════════════════════════════════════╣" -ForegroundColor Cyan
Write-Host "  ║  地址: http://localhost:$Port$(' ' * (28 - "$Port".Length))║" -ForegroundColor Cyan
Write-Host "  ║  目录: $($fullRoot.Substring(0, [Math]::Min(28, $fullRoot.Length)))$(' ' * [Math]::Max(0, 28 - [Math]::Min(28, $fullRoot.Length)))║" -ForegroundColor Cyan
Write-Host "  ╚══════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "  按 Ctrl+C 停止服务器" -ForegroundColor DarkGray
Write-Host ""

# 自动打开浏览器
Start-Process "http://localhost:$Port"

# 文件缓存（避免重复读取同一文件）
$script:fileCache = @{}

function Get-FileContent {
    param([string]$Path)
    if ($script:fileCache.ContainsKey($Path)) {
        return $script:fileCache[$Path]
    }
    $bytes = [System.IO.File]::ReadAllBytes($Path)
    $script:fileCache[$Path] = $bytes
    return $bytes
}

# 请求处理循环
try {
    while ($listener.IsListening) {
        $context = $listener.GetContext()
        $request = $context.Request
        $response = $context.Response

        $rawPath = $request.Url.AbsolutePath
        $path = [System.Uri]::UnescapeDataString($rawPath)

        # 默认页
        if ($path -eq '/' -or $path -eq '') {
            $path = '/index.html'
        }

        # 映射到文件系统
        $relativePath = $path.TrimStart('/')
        $filePath = Join-Path $fullRoot $relativePath.Replace('/', '\')

        $status = '404'
        $statusColor = 'Red'
        $contentLength = 0

        try {
            $resolvedFile = $null
            if (Test-Path $filePath -PathType Leaf) {
                $resolvedFile = (Resolve-Path $filePath -ErrorAction Stop).Path
            }

            # 安全检查：确保在根目录内
            if ($resolvedFile -and $resolvedFile.StartsWith($fullRoot)) {
                $extension = [System.IO.Path]::GetExtension($filePath).ToLower()
                $contentType = $mimeTypes[$extension]
                if (-not $contentType) {
                    $contentType = 'application/octet-stream'
                }

                $bytes = Get-FileContent -Path $resolvedFile
                $response.ContentType = $contentType
                $response.ContentLength64 = $bytes.Length
                $response.OutputStream.Write($bytes, 0, $bytes.Length)

                $status = '200'
                $statusColor = 'Green'
                $contentLength = $bytes.Length
            } else {
                # 404 — 返回 index.html 作为 SPA fallback
                $fallbackFile = Join-Path $fullRoot 'index.html'
                if (Test-Path $fallbackFile -PathType Leaf) {
                    $bytes = Get-FileContent -Path $fallbackFile
                    $response.ContentType = 'text/html; charset=utf-8'
                    $response.ContentLength64 = $bytes.Length
                    $response.OutputStream.Write($bytes, 0, $bytes.Length)
                    $status = '200'
                    $statusColor = 'DarkYellow'
                    $contentLength = $bytes.Length
                } else {
                    $response.StatusCode = 404
                    $errBytes = [System.Text.Encoding]::UTF8.GetBytes('404 Not Found')
                    $response.ContentLength64 = $errBytes.Length
                    $response.OutputStream.Write($errBytes, 0, $errBytes.Length)
                }
            }
        } catch {
            $response.StatusCode = 500
            $status = '500'
            $statusColor = 'Red'
        }

        $response.Close()

        # 日志输出
        $time = Get-Date -Format 'HH:mm:ss'
        $sizeStr = if ($contentLength -gt 0) { "$([math]::Round($contentLength / 1024, 1)) KB" } else { "-" }
        Write-Host "  [$time] " -NoNewline -ForegroundColor DarkGray
        Write-Host "$status " -NoNewline -ForegroundColor $statusColor
        Write-Host "$rawPath" -NoNewline -ForegroundColor DarkGray
        Write-Host " ($sizeStr)" -ForegroundColor DarkGray
    }
} catch {
    # Ctrl+C 或异常退出
} finally {
    if ($listener) {
        $listener.Stop()
        $listener.Close()
    }
    Write-Host ""
    Write-Host "  服务器已停止" -ForegroundColor Yellow
}
