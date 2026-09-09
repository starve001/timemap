@echo off
rem ============================================================
rem  MAPDEX 后端构建：生成 server\target\mapdex-server.jar
rem  依赖：JDK 21（默认 D:\jdk-21）+ 本机 Maven 3.9.16
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
echo [错误] 未找到 JDK（需要 javac）。请安装 JDK 21 或设置 JAVA_HOME。
exit /b 1

:have_java
set "MVN=C:\Users\lwr\.m2\wrapper\dists\apache-maven-3.9.16-bin\5grr65jo27hi51sujmtcldfovl\apache-maven-3.9.16\bin\mvn.cmd"
if not exist "%MVN%" (
  echo [错误] 未找到 Maven：%MVN%
  exit /b 1
)

echo 使用 JAVA_HOME=%JAVA_HOME%
call "%MVN%" -s maven-settings.xml --no-transfer-progress -DskipTests clean package
if errorlevel 1 (
  echo [错误] 构建失败
  exit /b 1
)
echo 构建完成：server\target\mapdex-server.jar
endlocal
