# 咕哝心岛 · 最新工作区源码交付（2026-10-30）

整理日期：2026-10-30。此包是当前工作区快照，包含未提交代码，不是仅导出 Git HEAD。完整架构、功能、安全与运行说明见 **`docs/技术说明_2026-10-30_v5.1.0-alpha.41.md`**；本文档保留交付、启动与核验口径。

## 版本与完成情况

包内 package/config 版本仍为 5.1.0-alpha.41，未随内容升级；版本字符串相同不代表文件内容相同。本包在 alpha.41 之上包含：

- 学生聊天（`/chat`，以及房间页内的聊天）后端生成分支替换为 DeepSeek「小满」对话引擎；保留内部 9 个话题的对话流程与危机锁定，界面不展示分数、量表或诊断词汇。
- 本地确定性安全规则（危机词、safeguarding、紧急分流）仍然优先于模型，模型不可用时不会阻断安全流程。
- 倾诉后小结改为由 DeepSeek 只依据学生自己的原话撰写，更具体地复述处境与感受；风险等级、情绪标签、边界与结构字段仍由本地确定性流程裁决。引用必须能在原话中逐字找到，出现分数、量表或诊断词即整份回退本地模板。
- 会话隐私口径升级：模型会收到对话原文，用于生成本轮回应和本次小结；会话同意版本 `platform-direct-transcript-v3`、教师授权版本 `teacher-ai-authorization-v3`，旧会话与旧授权自动失效。
- 新增学生标准筛查（PHQ-9，聊天页可选卡片）：本地确定性计分，不发送外部模型；教师端只看到分级、总分、填写时间与第9题安全标记，看不到单题答案；结果接入现有风险分流。默认关闭，开关为 `backend/.env` 的 `STUDENT_SCREENING_ENABLED=false`，开启前需学校心理老师/合规负责人复核中文措辞与教师可见口径。
- 未提交的 alpha.42 候选界面、**首页大厅 3.1** 与**全学生端像素点缀皮肤 3.0** 一并打包，前后端来自同一工作区时间点。
- 首页 `/` 改为主题大厅：三张 1600×1000 像素 SVG 昼夜场景、动态云/星/萤火/流星、真实太阳轨迹与月相、天气、问候、四张主卡与超大倾诉 CTA；`/room` 重定向到 `/`，删除旧 `MinimalHomeView` 与旧昼夜照片背景。
- 学生端全部页面统一 2px 边框、6px 卡片圆角、零模糊硬投影、金色虚线焦点；标题使用自托管像素字体子集（首页 3.5KB、学生端 49.8KB，SIL OFL 1.1）；聊天页保持零 `backdrop-filter`。
- 新增弹层焦点管理（Esc 关闭、Tab 循环、关闭后焦点归还）与 `prefers-reduced-motion` 全量降级；心岛画面层只改外框，不改内部像素画。

回滚开关：`STUDENT_COMPANION_ENGINE=legacy_xunfei` 时回到旧讯飞策略协作分支（需要另行配置讯飞能力）。

## 文件结构

- backend：FastAPI 后端、Agent、工具、授权、测试、合成评测数据与脚本。新增 `deepseek_client.py`、`companion_engine.py`、`screening_engine.py`、`api/screening.py` 及对应测试。
- frontend：Vue/Vite 界面、静态资源、前端测试、锁文件。新增 `styles/game-theme.css`、`assets/fonts/` 像素字体、`public/images/lobby/` 三张昼夜 SVG、`components/student/GameBackdrop.vue`、`utils/timeOfDay.js`、`utils/petCompanion.js`、`utils/dialogFocus.js`、`scripts/build_student_font_subset.py`、`scripts/gen_lobby_scenes.py`。
- docs：设计、研究、验收与部署记录；本次新增 `docs/技术说明_2026-10-30_v5.1.0-alpha.41.md` 与 `docs/情绪识别_检测与筛查说明_2026-10-30.md`。文档附件不纳入本源码包。
- deploy：历史部署脚本及测试，只供参考；旧版本脚本不能直接发布当前源码。
- licenses、THIRD_PARTY_NOTICES.md：第三方依赖与素材归属。
- scripts：资源处理与源码打包脚本。
- DELIVERY_MANIFEST.json：包内各文件 SHA256、Git 基点、未提交状态和排除规则。

已排除真实 .env、数据库、学生资料目录、运行时任务记录、日志、虚拟环境、node_modules、dist、缓存、Git 历史和旧压缩包。保留 .env.example 模板。业务必需的静态素材与 backend/data 审核资源 JSON 保留。测试中的固定账号/密码为合成夹具，不是线上账号。

## Windows 本地启动

建议使用 Python 3.12/3.13 和 Node.js 18/20。以下命令从解压后的源码根目录执行。

```powershell
cd backend
py -3.12 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item ..\.env.example .env
```

编辑 `backend/.env`，确保以下配置（其余项保持模板默认）：

```dotenv
RELEASE_VERSION=5.1.0-alpha.41-local
DATABASE_URL=sqlite:///./shengyu_v5_dev.db
DEMO_MODE=true
COOKIE_SECURE=false
BACKEND_PORT=9000

# 本地演示：允许免注册游客会话；线上必须为 false
ALLOW_GUEST_SESSION=true

# 标准筛查（PHQ-9）：默认关闭；开启前需完成中文措辞与教师可见口径复核
STUDENT_SCREENING_ENABLED=false

# 开启小满 DeepSeek 对话（对话原文会发送给 DeepSeek 生成回应和小结）
ALLOW_EXTERNAL_AI=true
ALLOW_STUDENT_EXTERNAL_AI=true
STUDENT_AI_ACCESS_MODE=platform_direct
PLATFORM_STUDENT_AI_GOVERNANCE_ACK=true
STUDENT_COMPANION_ENGINE=deepseek
DEEPSEEK_API_KEY=sk-你的密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

DeepSeek Key 只在服务端使用，不会下发浏览器；**不要把填好 Key 的 .env 提交或转发**。`PLATFORM_STUDENT_AI_GOVERNANCE_ACK=true` 表示运营方确认接受「对话原文发送给外部模型，用于回应和小结」这一口径，只应在本机演示时打开。

```powershell
.\venv\Scripts\python.exe main.py
```

后端按模板监听 127.0.0.1:9000。另开终端：

```powershell
cd frontend
npm ci
$env:VITE_API_TARGET='http://127.0.0.1:9000'
npm run dev
```

## macOS / Linux 本地启动

```bash
cd backend
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp ../.env.example .env
# 按上一节编辑 backend/.env
.venv/bin/python main.py
```

另开终端：

```bash
cd frontend
npm ci
VITE_API_TARGET=http://127.0.0.1:9000 npm run dev
```

访问终端显示的本地地址（默认 http://127.0.0.1:5173）。注意 `VITE_API_TARGET` 必须指向后端 9000 端口，否则前端默认代理到 8001，页面能打开但接口全部失败。

## 没有 DeepSeek Key 时

聊天仍可进行：模型调用失败时返回符合语境的兜底回应，响应标记为降级，用户可以直接继续说，不会出现空白气泡或死路。但这不是完整的小满对话体验，正式演示请配置 Key。Key 可用额度、费用以 DeepSeek 平台账户为准。

## 测试与可选 Agent 试点

```powershell
cd backend
.\venv\Scripts\python.exe -m pip install -r requirements-agent.txt
.\venv\Scripts\python.exe -W ignore -m unittest discover -s tests
cd ..\frontend
node --test tests/*.test.mjs
npm run build
```

最近一次基线（2026-10-30）：前端全量 164 项中 162 项通过，2 项失败是仓库未包含 Windows 专用 `deploy-frontend.ps1`；后端全量 203 项中 197 项通过，5 项错误为未安装可选 `langgraph` 依赖，1 项失败为既有 PDF 体积断言（8178 < 20000）；像素皮肤专项 7 项全部通过；`npm run build` 通过。依赖安装需要网络；Python requirements 部分为版本下限，并非完全锁定环境。切勿将测试服务部署到生产。

## 交付核验

压缩包已执行 ZIP 完整性检测，并核对所有归档文件与交付清单哈希。外部 .sha256 文件可核验压缩包本身。敏感字段扫描仅作辅助检查，不替代正式安全审计。
