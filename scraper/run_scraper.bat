@echo off
REM Fuel Price Scraper - Windows Task Scheduler 启动脚本
REM 每天下午3点运行

cd /d "C:\Users\Tracy Wei\Agent Workspace\fuel-tracker\scraper"

REM 使用指定的 Python 路径
/c/Users/Tracy\ Wei/AppData/Local/Python/bin/python3 auto_scraper.py

echo.
echo 任务完成