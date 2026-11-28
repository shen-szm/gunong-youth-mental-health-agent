@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"
title 咕哝心岛 - 一键启动

echo ==========================================
echo   咕哝心岛 本地一键启动
echo ==========================================
echo.

rem ---- 工具检查 ----
where npm >nul 2>&1 || (
    echo [错误] 未检测到 npm，请先安装 Node.js 18 或 20：https://nodejs.org/
    pause
    exit /b 1
)

set "PYCMD="
py -3.12 --version >nul 2>&1 && set "PYCMD=py -3.12"
if not defined PYCMD py -3 --version >nul 2>&1 && set "PYCMD=py -3"
if not defined PYCMD python --version >nul 2>&1 && set "PYCMD=python"
if not defined PYCMD (
    echo [错误] 未检测到 Python，请先安装 Python 3.12：https://www.python.org/downloads/
    pause
    exit /b 1
)

rem ---- 后端配置：首次运行时从模板生成 backend\.env ----
if not exist "backend\.env" (
    echo [初始化] 未找到 backend\.env，已从 .env.example 复制一份，可按需编辑，例如填写 DEEPSEEK_API_KEY。
    copy /y ".env.example" "backend\.env" >nul || goto :fail
)

rem ---- 读取后端端口，默认 9000，与 .env.example 保持一致 ----
set "BACKEND_PORT=9000"
for /f "usebackq tokens=1,* delims==" %%a in ("backend\.env") do (
    if /i "%%a"=="BACKEND_PORT" set "BACKEND_PORT=%%b"
)

rem ---- 后端环境：首次运行时创建虚拟环境并安装依赖 ----
if not exist "backend\venv\Scripts\python.exe" (
    echo [初始化] 首次运行：正在创建 Python 虚拟环境，请稍候...
    %PYCMD% -m venv "backend\venv" || goto :fail
    echo [初始化] 正在安装后端依赖，可能需要几分钟...
    "backend\venv\Scripts\python.exe" -m pip install -r "backend\requirements.txt" || goto :fail
)

rem ---- 前端依赖 ----
if not exist "frontend\node_modules" (
    echo [初始化] 首次运行：正在安装前端依赖，请稍候...
    pushd "frontend"
    call npm ci || (popd & goto :fail)
    popd
)

rem ---- 启动后端 ----
echo.
echo [启动] 后端  http://127.0.0.1:%BACKEND_PORT%
call :IsPortOpen %BACKEND_PORT%
if errorlevel 1 (
    start "咕哝心岛 - 后端" /D "%~dp0backend" cmd /k "venv\Scripts\python.exe main.py"
) else (
    echo        端口 %BACKEND_PORT% 已有服务在监听，视为后端已启动，跳过。
)

rem ---- 启动前端，并让 Vite 在就绪后自动打开浏览器 ----
echo [启动] 前端  http://127.0.0.1:5173
call :IsPortOpen 5173
if errorlevel 1 (
    set "VITE_API_TARGET=http://127.0.0.1:%BACKEND_PORT%"
    start "咕哝心岛 - 前端" /D "%~dp0frontend" cmd /k "npm run dev -- --open"
) else (
    echo        端口 5173 已有服务在监听，视为前端已启动，直接打开浏览器。
    start "" "http://127.0.0.1:5173/"
)

echo.
echo 启动完成。关闭「后端」「前端」两个窗口即可停止服务。
timeout /t 6 /nobreak
exit /b 0

:fail
echo.
echo [失败] 初始化出错，请根据上方提示处理后重新运行。
pause
exit /b 1

:IsPortOpen
powershell -NoProfile -Command "try { $c = New-Object Net.Sockets.TcpClient; $c.Connect('127.0.0.1', %~1); $c.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
exit /b %errorlevel%
