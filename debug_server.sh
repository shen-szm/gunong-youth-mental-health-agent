#!/bin/bash
# 在腾讯云服务器 Web 终端中执行以下命令来排查问题

echo "=== [1] 查看详细错误日志 ==="
sudo journalctl -u shengyu --no-pager -n 50

echo ""
echo "=== [2] 手动尝试启动后端（看具体报错）==="
cd /opt/shengyu/backend
source venv/bin/activate
python -c "from main import app; print('导入成功')"

echo ""
echo "=== [3] 检查 .env 文件是否存在 ==="
ls -la /opt/shengyu/backend/.env
cat /opt/shengyu/backend/.env | head -5

echo ""
echo "=== [4] 检查 main.py 文件 ==="
ls -la /opt/shengyu/backend/main.py
head -30 /opt/shengyu/backend/main.py

echo ""
echo "=== [5] 检查目录结构 ==="
find /opt/shengyu/backend -name "*.py" -type f | head -20
