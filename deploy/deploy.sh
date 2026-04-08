#!/bin/bash
# Fuel Tracker 一键部署脚本
# 在 Ubuntu 服务器上运行

set -e

echo "=========================================="
echo "Fuel Tracker 部署脚本"
echo "=========================================="

# 1. 更新系统
echo "[1/6] 更新系统..."
sudo apt update && sudo apt upgrade -y

# 2. 安装依赖
echo "[2/6] 安装依赖..."
sudo apt install -y python3 python3-pip python3-venv nginx git

# 3. 安装 Playwright 依赖
echo "[3/6] 安装 Playwright 依赖..."
sudo apt install -y libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libgbm1 libasound2 libpango-1.0-0 libcairo2

# 4. 克隆代码
echo "[4/6] 克隆代码..."
cd /var/www
sudo git clone https://github.com/TracyWei111/fuel-tracker.git
cd fuel-tracker

# 5. 创建虚拟环境并安装 Python 依赖
echo "[5/6] 安装 Python 依赖..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install flask gunicorn playwright
playwright install chromium

# 6. 配置 Nginx
echo "[6/6] 配置 Nginx..."
sudo tee /etc/nginx/sites-available/fuel-tracker << 'EOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/fuel-tracker /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx

# 7. 创建 systemd 服务
echo "[7/7] 创建 systemd 服务..."
sudo tee /etc/systemd/system/fuel-tracker.service << 'EOF'
[Unit]
Description=Fuel Tracker Dashboard
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/fuel-tracker
Environment="PATH=/var/www/fuel-tracker/venv/bin"
ExecStart=/var/www/fuel-tracker/venv/bin/gunicorn -w 2 -b 127.0.0.1:5000 dashboard.app:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable fuel-tracker
sudo systemctl start fuel-tracker

# 8. 配置定时任务（每天下午3点运行）
echo "配置定时任务..."
(crontab -l 2>/dev/null; echo "0 15 * * * cd /var/www/fuel-tracker && /var/www/fuel-tracker/venv/bin/python scraper/auto_scraper.py >> /var/www/fuel-tracker/logs/cron.log 2>&1") | crontab -

# 修复权限
sudo chown -R www-data:www-data /var/www/fuel-tracker

echo ""
echo "=========================================="
echo "部署完成！"
echo "=========================================="
echo ""
echo "访问地址: http://你的服务器IP"
echo ""
echo "常用命令:"
echo "  查看状态: sudo systemctl status fuel-tracker"
echo "  重启服务: sudo systemctl restart fuel-tracker"
echo "  查看日志: sudo journalctl -u fuel-tracker -f"
echo ""