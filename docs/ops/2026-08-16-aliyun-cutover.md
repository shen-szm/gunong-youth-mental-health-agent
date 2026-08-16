# 2026-08-16 阿里云正式接入记录

## 切换结果

- 域名：`guunoo.online`、`www.guunoo.online`
- 原服务器：腾讯云 `<OLD_SERVER_IP>`
- 新服务器：阿里云 `<SERVER_IP>`
- 前端版本：`4.5.6+dfbd5fd`
- 线上前端资源：`/assets/index-Ac5eZyun.js`
- ICP 备案号：`粤ICP备2026048986号-2`
- ICP 查询链接：`https://beian.miit.gov.cn/`

## DNS

- `@`：A 记录切换至 `<SERVER_IP>`
- `www`：A 记录切换至 `<SERVER_IP>`
- TTL：600 秒
- DNSPod 已显示两次修改成功；公共递归 DNS 可能在原 TTL 到期后逐步刷新。

## 服务验证

- 阿里云 Nginx：`active`
- 阿里云后端 `shengyu`：`active`
- HTTP 访问返回 `301` 并跳转 HTTPS
- `https://guunoo.online/` 返回 `200`
- `https://www.guunoo.online/` 返回 `200`
- `https://www.guunoo.online/teacher-login` 返回 `200`
- 新备案号已存在于线上构建资源中

## 回滚信息

- 切换前前端备份：`/opt/shengyu/backups/frontend-dist-20260816-222655`
- 如需紧急回滚，可先将 DNS A 记录恢复为 `<OLD_SERVER_IP>`，再按备份目录恢复前端。
