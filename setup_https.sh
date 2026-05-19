#!/bin/bash
# 配置 HTTPS 证书脚本
# 在腾讯云服务器 Web 终端中执行

DOMAIN="guunoo.online"

echo "=== [1] 安装 Certbot 和 Nginx 插件 ==="
sudo apt update
sudo apt install -y certbot python3-certbot-nginx

echo "=== [2] 更新 Nginx 配置，添加域名 ==="
sudo tee /etc/nginx/sites-available/shengyu << 'EOF'
server {
    listen 80;
    server_name guunoo.online www.guunoo.online;

    location / {
        root /opt/shengyu/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:9000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

echo "=== [3] 测试 Nginx 配置 ==="
sudo nginx -t

echo "=== [4] 重载 Nginx ==="
sudo systemctl reload nginx

echo "=== [5] 申请 Let's Encrypt 证书 ==="
sudo certbot --nginx -d guunoo.online -d www.guunoo.online --non-interactive --agree-tos --email admin@guunoo.online

echo "=== [6] 测试自动续期 ==="
sudo certbot renew --dry-run

echo ""
echo "✅ HTTPS 配置完成！"
echo "请访问: https://guunoo.online"
