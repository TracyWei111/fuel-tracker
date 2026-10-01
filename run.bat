@echo off
chcp 65001 >nul
echo ============================================================
echo Fuel Price Tracker Dashboard
echo ============================================================
echo.
echo 启动 Web 服务...
echo 访问地址: http://localhost:5005
echo 按 Ctrl+C 停止服务
echo ============================================================
echo.

cd /d "%~dp0"
"C:\Users\Tracy\Documents\Codex\migration-env\Scripts\python.exe" dashboard\app.py

pause