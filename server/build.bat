@echo off
rem ============================================================
rem  MAPDEX 后端构建：生成 server\target\mapdex-server.jar
rem  依赖：JDK 21（Maven 用自带 wrapper，首次运行自动下载）
rem ============================================================
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if defined JAVA_HOME (
  if exist "%JAVA_HOME%\bin\javac.exe" goto :have_java
)
if exist "D:\jdk-21\bin\javac.exe" (
  set "JAVA_HOME=D:\jdk-21"
  goto :have_java
)
for /f "delims=" %%i in ('where javac 2^>nul') do (
  set "JAVA_HOME=%%~dpi.."
  goto :have_java
)
echo [错误] 未找到 JDK（需要 javac）。请安装 JDK 21 或设置 JAVA_HOME。
exit /b 1

:have_java
rem 优先用仓库自带的 Maven Wrapper（见 .mvn/wrapper/maven-wrapper.properties），
rem 找不到时回退到系统 PATH 里的 mvn
set "MVN=%~dp0mvnw.cmd"
if not exist "%MVN%" (
    for /f "delims=" %%i in ('where mvn 2^>nul') do if not defined MVN set "MVN=%%i"
)
if not exist "%MVN%" (
    echo [错误] 未找到 mvnw.cmd 且系统 PATH 中没有 mvn。
    exit /b 1
)

echo 使用 JAVA_HOME=%JAVA_HOME%
call "%MVN%" -s maven-settings.xml --no-transfer-progress clean package
if errorlevel 1 (
  echo [错误] 构建失败
  exit /b 1
)
echo 构建完成：server\target\mapdex-server.jar
endlocal
