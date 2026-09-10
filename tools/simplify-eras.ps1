# 批量简化时代切片：从输入目录读 *.geojson，简化后写入输出目录（同名）。
# 用 mapshaper -simplify <percent>% keep-shapes，保留全部属性字段。
# 用法示例：
#   .\simplify-eras.ps1 -InputDir .\data\eras -OutputDir .\data\eras_simp -Percent 75
param(
    [string]$InputDir  = "c:\Users\lwr\Desktop\timemap\data\eras",
    [string]$OutputDir = "c:\Users\lwr\Desktop\timemap\data\eras_simp",
    [int]$Percent = 75
)

if (-not (Test-Path $InputDir)) { Write-Host "输入目录不存在: $InputDir"; exit 1 }
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$files = Get-ChildItem -Path $InputDir -Filter "*.geojson" -File
Write-Host "待处理切片数: $($files.Count) (保留 $Percent%)"
$ok = 0
foreach ($f in $files) {
  $target = Join-Path $OutputDir $f.Name
  npx --yes mapshaper $f.FullName -simplify "$Percent%" keep-shapes -o format=geojson $target 2>$null
  if ($LASTEXITCODE -eq 0 -and (Test-Path $target)) { $ok++ }
  else { Write-Host "失败: $($f.Name)" }
}
$sum = (Get-ChildItem $OutputDir -Filter *.geojson -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
Write-Host "成功: $ok / $($files.Count)，输出总大小 $([math]::Round($sum/1MB,2)) MB"