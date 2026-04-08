# Fuel Price Scraper - Windows Task Scheduler 配置脚本
# 以管理员身份运行此脚本

# 任务名称
$TaskName = "FuelPriceScraper"
$TaskDescription = "每天下午3点自动抓取柴油价格数据"

# 启动脚本路径
$ScriptPath = "C:\Users\Tracy Wei\Agent Workspace\fuel-tracker\scraper\run_scraper.bat"

# 创建触发器：每天下午3点
$Trigger = New-ScheduledTaskTrigger -Daily -At "3:00PM"

# 创建操作
$Action = New-ScheduledTaskAction -Execute $ScriptPath -WorkingDirectory "C:\Users\Tracy Wei\Agent Workspace\fuel-tracker\scraper"

# 创建设置
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd -AllowStartIfOnBatteries

# 注册任务（以当前用户身份运行）
Register-ScheduledTask -TaskName $TaskName -Description $TaskDescription -Trigger $Trigger -Action $Action -Settings $Settings -RunLevel Highest -Force

Write-Host "定时任务已创建: $TaskName"
Write-Host "运行时间: 每天下午 3:00"
Write-Host ""
Write-Host "查看任务: Get-ScheduledTask -TaskName '$TaskName'"
Write-Host "手动运行: Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "删除任务: Unregister-ScheduledTask -TaskName '$TaskName'"