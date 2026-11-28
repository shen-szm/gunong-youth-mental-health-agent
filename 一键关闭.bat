@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"
title 咕哝心岛 - 一键关闭

echo ==========================================
echo   咕哝心岛 一键关闭
echo ==========================================
echo.

rem ---- 读取后端端口，与一键启动.bat 保持一致 ----
set "BACKEND_PORT=9000"
if exist "backend\.env" (
    for /f "usebackq tokens=1,* delims==" %%a in ("backend\.env") do (
        if /i "%%a"=="BACKEND_PORT" set "BACKEND_PORT=%%b"
    )
)

rem ---- 找到监听端口的进程，沿父进程链向上找到启动器窗口 cmd /k 或 npm 包装层，整树结束 ----
powershell -NoProfile -Command "$ErrorActionPreference = 'SilentlyContinue'; $ports = @(%BACKEND_PORT%, 5173); $n = 0; foreach ($port in $ports) { $ids = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique); foreach ($id in $ids) { $p = Get-CimInstance Win32_Process -Filter ('ProcessId=' + $id); while ($p) { $pp = Get-CimInstance Win32_Process -Filter ('ProcessId=' + $p.ParentProcessId); if (-not $pp -or $pp.CreationDate -gt $p.CreationDate) { break }; $wrap = ($pp.Name -eq 'python.exe') -or ($pp.Name -eq 'node.exe'); $cmdwrap = ($pp.Name -eq 'cmd.exe') -and ($pp.CommandLine -match 'main\.py|npm|/c '); if ($wrap -or $cmdwrap) { $p = $pp } else { break } }; if ($p) { Write-Host ('[停止] ' + $p.Name + ' PID ' + $p.ProcessId); taskkill /PID $p.ProcessId /T /F 2>&1 | Out-Null; $n++ } } }; if ($n -eq 0) { Write-Host '没有发现运行中的服务。' } else { Write-Host ('共结束 ' + $n + ' 个进程树。') }"

echo.
echo 已完成。浏览器标签页如仍开着，手动关掉即可。
timeout /t 4 /nobreak
exit /b 0
