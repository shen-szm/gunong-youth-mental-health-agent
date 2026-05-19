#!/bin/bash
# 在腾讯云服务器 Web 终端中执行以下命令

echo "=== [1] 创建缺失的 __init__.py 文件 ==="
touch /opt/shengyu/backend/api/__init__.py
touch /opt/shengyu/backend/xunfei/__init__.py
echo "已创建 api/__init__.py 和 xunfei/__init__.py"

echo ""
echo "=== [2] 检查目录结构 ==="
ls -la /opt/shengyu/backend/api/
echo "---"
ls -la /opt/shengyu/backend/xunfei/

echo ""
echo "=== [3] 查看服务日志（排查启动失败原因）==="
sudo journalctl -u shengyu --no-pager -n 30

echo ""
echo "=== [4] 重新启动服务 ==="
sudo systemctl restart shengyu
sleep 3

echo ""
echo "=== [5] 检查服务状态 ==="
sudo systemctl status shengyu --no-pager

echo ""
echo "=== [6] 测试 API 响应 ==="
curl -s http://127.0.0.1:9000/
