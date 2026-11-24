# 5.1.0-alpha.43 发布记录

- 发布时间：2026-11-18 10:25（CST）
- 发布方式：`deploy/release-alpha43.py --apply`（root，预检通过后执行）
- 发布 ID：`alpha43-local-20261118-102415`
- 版本变化：`5.1.0-alpha.42` → `5.1.0-alpha.43`
- 生产路径：`/opt/shengyu`
- 线上地址：https://guunoo.online

## 发布内容

### 前端

完整替换 `frontend/dist`（新构建 67 个文件），并保留 alpha.42 的旧哈希资源以兼容发布前已打开的页面；线上当前共 113 个 dist 文件。主要变化：

- 心岛地图可缩放：手机双指捏合（100%–250%）、放大后单指拖动平移；桌面滚轮缩放与左上角「＋ / － / 倍率 / 复位」控件。点击自动前往、摇杆、方向键行走保持不变。
- 小满跨会话记忆：聊天页与首页聊天面板新增「小满记得的事」，可逐条忘记或全部清空；隐私说明版本升至 `platform-direct-transcript-v4`。
- 心岛小人侧面头像重做（斜刘海 + 楔形侧脸）；6×3 / 40×56 精灵帧契约不变。

关键校验：

| 文件 | SHA256 |
| --- | --- |
| `dist/index.html` | `f6cecce14ef371abd18375ac3dbfccf4c5843ae1221465680454c58e6555a7ee` |
| `dist/assets/index-ANTMc8U2.js` | `47b14f5552c29b4c2349d74a711e18d65c72bb72cd54f257379db33d6447e421` |
| `dist/assets/createIslandGame-CSC8l8IH.js` | `b29b1dc8ce34e7076a3b0d2802cfe731ea8478be729ab82085574f5140c2b992` |

完整 113 个线上文件哈希：`/opt/shengyu/backups/alpha43-local-20261118-102415/dist-sha256.txt`。

### 后端

部署 5 个改动文件（无新增文件、无依赖变化）：

| 文件 | 线上 SHA256 |
| --- | --- |
| `api/chat.py` | `bfa55f7f7c4d7a06245066c4d32b386ce3948283b2f492359c6ef4d96c6fa96c` |
| `companion_engine.py` | `fa6a9843b21df1aa2f6f227667e139bbe16be9bc65ff793aca6101561c120ff3` |
| `config.py` | `f8264bf30fe7432d0fa85ad06fb1396a86d63bfd680e6f4b1bb7f36929ed984e` |
| `models.py` | `2fa6247e3a3f6c61dad61326e5e50abdf65e952a143ffadd2f9933b13a0bc1f3` |
| `student_ai_authorization.py` | `63a9227b148b3713e9e6eb0ed502b2bbaf2a447c6108eb56deae3cdc824f8e85` |

归档校验：

- `backend.tar` SHA256：`26bf0da47649c7075ec92a3e7a22fcb982b91629afec1387ce748280ffd021f3`
- 归档成员与脚本白名单逐项一致，全部为普通文件；Python 文件已 `py_compile`。

### 配置（服务器 `backend/.env`，权限 600 ubuntu:ubuntu）

仅更新 `RELEASE_VERSION=5.1.0-alpha.43`；原有受管项原样保留：`STUDENT_COMPANION_ENGINE`、`DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL`、`STUDENT_SCREENING_ENABLED`。本次未写入或轮换任何密钥。

### 数据库

启动时 `init_db()` 执行 `create_all`，确认纯新增迁移：

- 新表：`student_companion_memories`（每用户最多 30 条、180 天过期，含用户/去重/更新时间/过期时间索引）；已有表无结构变化。

发布前一致性备份：`/opt/shengyu/backups/alpha43-local-20261118-102415/shengyu_v2.db`（2,101,248 字节，600 ubuntu:ubuntu）。

## 发布前本地验证

- 前端单元测试：174 项，172 通过；仅 2 项既有失败（仓库缺 `deploy-frontend.ps1`，与本次改动无关）。
- 后端目标测试：86 项全部通过（`tests.test_companion_engine`、`test_student_chat_companion`、`test_student_conversation_summary`、`test_teacher_case_access`、`test_release_health`）。
- `npm run build` 成功；产物含 `5.1.0-alpha.43` 徽标、缩放版心岛与记忆面板。

## 线上验收

- `http://127.0.0.1:9000/health`：`status=ok`，`version=5.1.0-alpha.43`，`external_ai=true`、`student_ai=true`、`guest_session=true`。
- `https://guunoo.online/`：HTTP 200，入口引用 `assets/index-ANTMc8U2.js`。
- `https://guunoo.online/assets/index-ANTMc8U2.js`：HTTP 200，764,821 字节；`assets/createIslandGame-CSC8l8IH.js` HTTP 200，20,920 字节。
- 旧入口 `assets/index-DItLdA2W.js` 仍返回 200（发布前页面不白屏）。
- 图片资源：`/images/island/heart-island-base.webp` 200（107,516 字节）；`/images/island/student-back.webp` 200（1,698 字节）。
- `https://guunoo.online/api/chat/memories`：HTTP 401（路由已注册，未登录被鉴权拦截）；`/api/screening/schema` 仍为 401。
- 数据库存在 `student_companion_memories` 表；`systemctl is-active shengyu` 为 `active`；近 5 分钟日志无 error/traceback。
- 生产移动端浏览器实测（390×844）：心岛加载成功，缩放按钮 100% → 156% → 100%，无控制台错误；截图 `/tmp/island-prod-mobile-zoom.png`。

## 备份与回滚

备份目录：`/opt/shengyu/backups/alpha43-local-20261118-102415`

- `frontend-dist/`：alpha.42 原 dist（51MB）
- 5 个被修改后端文件 + 原始 `.env`
- `shengyu_v2.db`：发布前数据库（2,101,248 字节）
- `dist-sha256.txt`：alpha.43 线上 113 个 dist 文件哈希

回滚方式：脚本异常时自动恢复代码、`.env`、dist 与数据库并重启，断言 `/health` 回到 `5.1.0-alpha.42`；手工回滚先 `systemctl stop shengyu`，恢复上述文件（`.env` 与数据库保持 `ubuntu:ubuntu` 600），再 `systemctl start shengyu` 并确认 `/health` 回到 alpha.42。

## 已知事项

- 前端两个 PowerShell 部署脚本断言持续失败，属仓库既有缺口。
- 线上 `models.py` 为 CRLF 行尾，且 `models.py` 本身就是 CRLF 源文件；发布脚本的基线比对会先做 CRLF→LF 归一化，记录哈希时务必使用归一化值（原始 `sha256sum` 值会导致预检误报 `baseline changed`）。
- 发布暂存目录保留在 `/opt/shengyu/releases/alpha43-local-20261118-102415`（`backend.tar`、`code/`、发布脚本；dist 已移入生产）。
