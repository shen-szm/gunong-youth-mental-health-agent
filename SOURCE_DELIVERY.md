# 咕哝心岛 · 最新工作区源码交付

整理日期：2026-10-08。此包是当前工作区快照，包含未提交代码，不是仅导出 Git HEAD。前一次提供的 `shengyu-live-alpha37-20261008.tar.gz` 是线上运行文件快照，前端仅有编译产物；本包才包含前端开发源码与本地最新后端源码。

## 版本与完成情况

包内 package/config 版本仍为 5.1.0-alpha.37，但包含该版本发布后新增的教师需求风险预检、PC 澄清界面与后端澄清记录。2026-10-08 核对线上健康检查仍为 alpha.37；版本字符串相同不代表文件内容相同。线上运行快照的后端不包含本地后续新增的 `teacher_intent_guard.py` 与 `teacher_clarification.py`；本包包含。前端开发源码与上次本地源码包相比没有新的功能提交，本次重新纳入，以确保前后端来自同一工作区时间点。

教师自然语言规划与持久化任务属于默认关闭的试点。澄清记录尚未与计划创建/执行完整绑定，前端也尚未接入后端澄清记录接口；不能声称完整的人工确认恢复执行已完成。历史验收记录见 docs/research 和 docs/ops。本次整理不等同于重跑全部测试。

## 文件结构

- backend：FastAPI 后端、Agent、工具、授权、测试、合成评测数据与脚本。
- frontend：Vue/Vite PC 界面、静态资源、前端测试、锁文件。
- docs：设计、研究、验收与部署记录；文档附件不纳入本源码包。
- deploy：历史部署脚本及测试，只供参考；旧版本脚本不能直接发布当前源码。
- licenses、THIRD_PARTY_NOTICES.md：第三方依赖与素材归属。
- scripts：资源处理与源码打包脚本。
- DELIVERY_MANIFEST.json：包内各文件 SHA256、Git 基点、未提交状态和排除规则。

已排除真实 .env、数据库、学生资料目录、运行时任务记录、日志、虚拟环境、node_modules、dist、缓存、Git 历史和旧压缩包。保留 .env.example 模板。业务必需的静态素材与 backend/data 审核资源 JSON 保留。测试中的固定账号/密码为合成夹具，不是线上账号。

## Windows 本地启动

建议使用 Python 3.12/3.13 和 Node.js 20。以下命令从解压后的源码根目录执行。

```powershell
cd backend
py -3.12 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item ..\.env.example .env
```

编辑 backend/.env：RELEASE_VERSION 可设为 5.1.0-alpha.37-local；保持 ALLOW_EXTERNAL_AI=false，不填写真实学生资料。需要本地教师登录时，自行设置 ADMIN_USERNAME 与至少 12 位的 ADMIN_PASSWORD。该根目录模板用于本地开发，不能直接作为生产配置。

```powershell
.\venv\Scripts\python.exe main.py
```

后端默认按上述模板监听 127.0.0.1:9000。另开终端：

```powershell
cd frontend
npm ci
$env:VITE_API_TARGET='http://127.0.0.1:9000'
npm run dev
```

访问终端显示的本地地址（默认 http://127.0.0.1:5173）。基础运行不要求模型密钥，部分 AI 功能会明确显示不可用或降级。

## 测试与可选 Agent 试点

完整后端测试包含 LangGraph 试点依赖，先安装可选依赖；安装不代表启用生产功能。

```powershell
cd backend
.\venv\Scripts\python.exe -m pip install -r requirements-agent.txt
.\venv\Scripts\python.exe -W ignore -m unittest discover -s tests
cd ..\frontend
node --test tests/*.test.mjs
npm run build
```

依赖安装需要网络；Python requirements 部分为版本下限，并非完全锁定环境。浏览器测试需要本地 Edge 及合成测试服务，详见 frontend/tests/teacher-case-task.e2e.mjs 与 backend/scripts/serve_teacher_task_preview.py。切勿将测试服务部署到生产。

## 交付核验

压缩包已执行 ZIP 完整性检测，并核对所有归档文件与交付清单哈希。外部 .sha256 文件可核验压缩包本身。敏感字段扫描仅作辅助检查，不替代正式安全审计。
