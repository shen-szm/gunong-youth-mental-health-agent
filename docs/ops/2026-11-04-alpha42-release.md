# 5.1.0-alpha.42 发布记录

- 发布时间：2026-11-04 22:43（CST）
- 发布方式：`deploy/release-alpha42.py --apply`（root，预检通过后执行）
- 发布 ID：`alpha42-local-20261104-224107`
- 版本变化：`5.1.0-alpha.37` → `5.1.0-alpha.42`
- 生产路径：`/opt/shengyu`
- 线上地址：https://guunoo.online

## 发布内容

### 前端

完整替换 `frontend/dist`（新构建 67 个文件），并保留旧哈希资源以兼容发布前已打开的页面。主要变化：

- 心岛学生角色改为 6×3 像素精灵图（240×168，单帧 40×56），正/背/侧三向行走与待机。
- 心岛像素底图、海面留白（晨/黄昏/夜晚）、暖房羊皮纸皮肤与窄屏布局。
- alpha.38–alpha.41 累积的学生端极简首页、倾诉页、回顾页、双栏布局与流光氛围等既有改动一并上线。

关键校验：

| 文件 | SHA256 |
| --- | --- |
| `dist/index.html` | `04f0f954b5214487609627c5e3b43c9e99ebd762c370994f4089ba68f0b49376` |
| `dist/images/island/student-back.webp` | `bd23ca02716e8efef4d356724eb7237fb2ba55b19a109fb4eb4d903a167211b3` |
| `dist/images/island/heart-island-base.webp` | `56f6d78e6797f6d17586d0ec758d366c83f6921d4a1bf28396292a2e7f830433` |
| `dist/assets/createIslandGame-CvsvcZid.js` | `220ac79689c44a69e1306ded36db8cedc42e4a73787e7793a46f092f5190bb81` |
| `dist/assets/index-DItLdA2W.js` | `c543f3a9e4fd25adc2773168456aa82b4a9dc5a96d1b0498382c7175b18c3c4f` |

完整 103 个线上文件哈希：`/opt/shengyu/backups/alpha42-local-20261104-224107/dist-sha256.txt`。

### 后端

部署 26 个运行时文件：13 个改动、13 个新增。新增文件包含 `api/screening.py`、`screening_engine.py`、`companion_engine.py`、`deepseek_client.py` 及教师任务相关模块；依赖仅新增 `websocket-client>=1.8.0`，生产 venv 已有 1.9.0，未执行安装。

归档校验：

- `backend.tar` SHA256：`eecfef8991f4305debc82755f00b2d76cb11562fa1c528a52b679c9d547e660a`
- 归档成员与脚本白名单逐项一致，全部为普通文件；Python 文件已 `py_compile`。

### 配置（仅写入服务器 `backend/.env`，权限 600 ubuntu:ubuntu）

```text
RELEASE_VERSION=5.1.0-alpha.42
STUDENT_COMPANION_ENGINE=deepseek
DEEPSEEK_API_KEY=<仅服务端>
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
STUDENT_SCREENING_ENABLED=true
```

DeepSeek 密钥已在服务器侧通过 `GET /models`（HTTP 200）与一次最小对话请求验证；账号模型列表显示 `deepseek-flash` / `deepseek-v4-pro`，`deepseek-chat` 别名仍可正常返回内容。密钥文件在发布成功后已删除，未写入前端或仓库。

### 数据库

启动时执行 `init_db()`，确认为纯新增迁移：

- 新表：`student_screening_runs`
- 新增列：`student_chat_sessions.companion_state_json`、`student_screening_runs.acknowledged_at`

发布前一致性备份：`/opt/shengyu/backups/alpha42-local-20261104-224107/shengyu_v2.db`（1,855,488 字节，600 ubuntu:ubuntu，SHA256 `bee328eec666ff313c71fb161a3ee0c4af50ecb961a01aa6fae5d775ac2fcb50`）。

## 发布前本地验证

- 前端单元测试：164 项，162 通过；仅 2 项既有失败，均因仓库缺少 `deploy-frontend.ps1`（与本次改动无关）。
- 心岛测试：8/8 通过。
- 后端测试：203 项，1 个 PDF 体积断言失败 + 5 个可选 LangGraph 模块导入错误；均为既有本地环境问题，核心用例通过。
- `npm run build` 成功；构建产物包含 `5.1.0-alpha.42` 徽标与新心岛资源。

## 线上验收

- `http://127.0.0.1:9000/health`：`status=ok`，`version=5.1.0-alpha.42`，`external_ai=true`、`student_ai=true`。
- `https://guunoo.online/`：HTTP 200，入口引用新哈希 `assets/index-DItLdA2W.js`。
- `https://guunoo.online/images/island/student-back.webp`：HTTP 200，`image/webp`，1,712 字节。
- `https://guunoo.online/assets/createIslandGame-CvsvcZid.js`：HTTP 200，16,902 字节。
- `https://guunoo.online/api/screening/schema`：HTTP 401（路由已注册，未登录被鉴权拦截；启用前为 404）。
- `systemctl is-active shengyu`：`active`；启动日志无 error/traceback；`Application startup complete`。
- 旧哈希资源仍可访问（发布前页面不白屏）。

## 备份与回滚

备份目录：`/opt/shengyu/backups/alpha42-local-20261104-224107`

- `frontend-dist/`：alpha.37 原 dist（327MB 量级）
- 13 个被修改后端文件 + 原始 `.env`
- `shengyu_v2.db`：发布前数据库

回滚方式：使用同目录下发布脚本的异常回滚逻辑会恢复代码、`.env`、dist 与数据库；手工回滚时先 `systemctl stop shengyu`，恢复上述文件（`.env` 与数据库保持 `ubuntu:ubuntu` 600），再 `systemctl start shengyu` 并确认 `/health` 回到 `5.1.0-alpha.37`。

## 已知事项

- 前端两个 PowerShell 部署脚本相关断言持续失败，属仓库既有缺口。
- 本地后端 6 个可选模块/PDF 用例失败未影响线上（生产未安装 LangGraph，试点功能保持关闭）。
- PHQ-9 筛查按本次选择开启；结果仅用于支持分流，不构成诊断，紧急风险仍走既有安全交接。
