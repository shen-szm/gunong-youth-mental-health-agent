#!/bin/bash
# 声愈服务器安全加固脚本
# 在腾讯云 Web 终端中逐行执行

echo "=== [1] 更新系统包 ==="
sudo apt update && sudo apt upgrade -y

echo "=== [2] 安装防火墙工具 UFW ==="
sudo apt install -y ufw

echo "=== [3] 配置防火墙规则 ==="
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw --force enable

echo "=== [4] 禁用 root 远程登录 ==="
sudo sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config

echo "=== [5] 禁用密码登录（可选，需要先配置密钥） ==="
# ⚠️ 执行此步前请确保已配置SSH密钥登录！
# 如果没有密钥，跳过此步
# sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
# sudo sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config

echo "=== [6] 安装 fail2ban 防暴力破解 ==="
sudo apt install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

echo "=== [7] 自动安全更新 ==="
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades

echo "=== [8] 查看防火墙状态 ==="
sudo ufw status

echo "=== [9] 查看 fail2ban 状态 ==="
sudo systemctl status fail2ban --no-pager

echo ""
echo "✅ 安全加固完成！"
