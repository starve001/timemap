@echo off
setlocal
title MAPDEX
cd /d "%~dp0"

:: ---------------- locate Java ----------------
set "JAVA="
if defined JAVA_HOME if exist "%JAVA_HOME%\bin\java.exe" set "JAVA=%JAVA_HOME%\bin\java.exe"
if not defined JAVA if exist "D:\jdk-21\bin\java.exe" set "JAVA=D:\jdk-21\bin\java.exe"
if not defined JAVA for /f "delims=" %%i in ('where java 2^>nul') do if not defined JAVA set "JAVA=%%i"
if not defined JAVA (
    echo [ERROR] Java not found. Install JDK 21 to D:\jdk-21 or set JAVA_HOME.
    pause
    exit /b 1
)

set "JAR=%cd%\server\target\mapdex-server.jar"
set "PIDFILE=%cd%\server\mapdex.pid"

if /i "%~1"=="stop" goto :stop

:: ---------------- already running? ----------------
powershell -NoProfile -Command "try{Invoke-WebRequest -Uri 'http://127.0.0.1:8090/healthz' -UseBasicParsing -TimeoutSec 2|Out-Null;exit 0}catch{exit 1}"
if not errorlevel 1 (
    echo [INFO] MAPDEX already running, opening browser...
    start "" "http://127.0.0.1:8090"
    exit /b 0
)

:: ---------------- first build if needed ----------------
if not exist "%JAR%" (
    echo [INFO] jar not found, building... first build downloads dependencies.
    call "%~dp0server\build.bat"
    if errorlevel 1 (
        echo [ERROR] build failed, cannot start.
        pause
        exit /b 1
    )
)

:: ---------------- start in background ----------------
powershell -NoProfile -Command "$p=Start-Process -FilePath '%JAVA%' -ArgumentList '-jar','%JAR%' -WorkingDirectory '%cd%' -WindowStyle Hidden -RedirectStandardOutput '%cd%\server\mapdex.log' -RedirectStandardError '%cd%\server\mapdex.err.log' -PassThru; $p.Id | Out-File '%PIDFILE%' -Encoding ascii"
echo [INFO] starting MAPDEX... logs: server\mapdex.log

:: ---------------- wait until ready ----------------
set /a n=0
:wait
powershell -NoProfile -Command "try{Invoke-WebRequest -Uri 'http://127.0.0.1:8090/healthz' -UseBasicParsing -TimeoutSec 2|Out-Null;exit 0}catch{exit 1}"
if not errorlevel 1 goto :open
set /a n+=1
if %n% geq 40 (
    echo [ERROR] server not ready in 40s. See server\mapdex.log
    pause
    exit /b 1
)
ping -n 2 127.0.0.1 >nul
goto :wait

:open
echo [OK] MAPDEX ready: http://127.0.0.1:8090
start "" "http://127.0.0.1:8090"
exit /b 0

:stop
powershell -NoProfile -Command "$f='%PIDFILE%'; if(Test-Path $f){$id=Get-Content $f -ErrorAction SilentlyContinue|Select-Object -First 1; if($id){Stop-Process -Id $id -Force -ErrorAction SilentlyContinue}; Remove-Item $f -Force -ErrorAction SilentlyContinue}; Get-NetTCPConnection -LocalPort 8090 -State Listen -ErrorAction SilentlyContinue|ForEach-Object{Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue}"
echo [OK] MAPDEX stopped.
exit /b 0