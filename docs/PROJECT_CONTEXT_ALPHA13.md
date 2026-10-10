# 咕哝项目交接上下文（v5.1.0-alpha.13）

## 1. 项目目标

咕哝是面向青少年（12–18岁）的心理健康教育、倾听、支持建议和求助导航网站，服务学生、教师与家长。目标是展示“AI+超级智能体”端到端能力：学生侧倾诉/活动交互/情绪回顾，教师侧审批后的关注与支持工作台。系统不诊断、不治疗、不使用正式心理量表。

## 2. 当前目录结构

```text
frontend/                 Vue 3 + Vite 学生端/教师端
  src/views/              房间、教师、守护者页面
  src/components/island/  心岛、种植、钓鱼、幸福交换、宠物组件
  src/game/island/        心岛状态、寻路、Phaser钓鱼、种植引擎
  src/api/                chat、mood、teacher 等接口客户端
  tests/                  前端契约、组件、E2E/状态测试
backend/                  FastAPI + SQLAlchemy 后端
  api/                    chat、mood、guardian、teacher、companion 等路由
  xunfei/                 讯飞 Spark/TTS/ASR 封装
  data/                   守护者证据与资源白名单
  tests/                  后端安全、工作流、API 测试
docs/research/            GitHub/架构调研记录
docs/screenshots/         alpha13 本地预览截图
licenses/                 第三方许可证
```

## 3. 已完成的功能

- 学生房间保留原像素风和液态玻璃；心岛支持昼/暮/夜按本地时间自动切换、二维移动、场景碰撞、网格寻路和右侧 Agent 进度。
- 心岛种植已替换 2048：9 块田、翻地、四类作物、播种、浇水联动成长、收获篮、岛民订单、种子商店、岛币、咕团协助。
- 钓鱼为三阶段玩法：抛竿落点、咬钩限时提竿、张力收线；6 类鱼图鉴、落点精度、奖励和持久化状态。使用懒加载 Phaser。
- 幸福交换保留写下小事、安全门、卡片交换、幸福册、30天清理和 12356/110/120 危机路径。
- 学生聊天支持明确结束确认、完整会话小结、危机优先、非诊断情绪标签/强度/证据、可删除和30天到期。
- 讯飞仅在学生逐会话同意后接收最近六轮脱敏文本；严格 JSON、证据必须来自输入、禁止诊断/量表/危险建议；失败降级确定性模板。
- 活动后学生主动自评写入后端；床头“情绪回顾”直接显示30天 Agent 报告：来源计数、时间线、倾诉轨迹、支持重点、下一步和边界。
- 教师/守护者工作台、申请审批、管理员直达、风险分流、证据审查、PDF和回访 API 已存在并保留。
- 当前本地预览：前端 `http://127.0.0.1:5175/`，后端 `http://127.0.0.1:8001/health`。

## 4. 正在开发/待完善

- 教师端将学生情绪报告纳入审批后的关注流程（目前学生报告不自动提供教师）。
- 继续提升钓鱼手感、种植成长反馈、宠物养成深度和 Agent 可验收事件；移动端本轮暂不重做。
- 将真实讯飞凭据、模型超时、限流、审计和生产环境配置做上线前联调；不能在仓库写入密钥。
- 完善视觉回归、键盘/读屏、减少动态效果和真实中文 PDF 渲染检查。

## 5. 关键技术

- Vue 3 Composition API、Vite、Axios、Vue Router；Phaser 3.90（钓鱼场景）、Swiper 12（幸福交换）。
- FastAPI、Pydantic 严格 Schema、SQLAlchemy、HttpOnly 会话、角色权限和敏感访问审计。
- 确定性 `StudentSafetyGate`/安全规则优先，讯飞 Spark 只生成受约束文字；报告基于主动记录和对话标签，不从游戏成绩推断情绪。
- 参考高 Star 开源项目：Phaser、Swiper、BrowserQuest、A Dark Room、sandspiel、declare-lab/conv-emotion、PaddleNLP；详见 `docs/research/2026-08-27-heart-island-emotion-alpha13.md`，仅按许可证和产品思路借鉴。

## 6. 重要文件说明

- `frontend/src/views/RoomHomeView.vue`：学生房间、聊天、情绪回顾、Agent 轨迹和心岛入口。
- `frontend/src/components/island/StudentIslandWorkspace.vue`：心岛容器、地点导航、活动反馈与状态保存。
- `frontend/src/game/island/gardenLifeEngine.js`：非 2048 的种植状态机。
- `frontend/src/game/island/createFishingGame.js`：Phaser 钓鱼场景与三阶段状态机。
- `backend/api/chat.py`：学生会话、安全门、讯飞约束、完整小结与脱敏。
- `backend/api/mood.py`：活动后主动反馈和情绪报告 API。
- `backend/api/guardian.py`、`backend/guardian_engine.py`：守护者工作流、风险与证据。
- `CHANGELOG.md`：每个 alpha 版本变更记录；当前 alpha13。

## 7. 已知问题

- `npm audit` 已返回 0 vulnerabilities；此前在线审计端点偶发网络失败，需联网时重试。
- Vite 构建提示 Phaser chunk 较大，但 Phaser 已懒加载，不影响首屏功能。
- 后端测试有 Python `datetime.utcnow()` 弃用警告，不影响通过结果，后续可统一迁移时区感知时间。
- 当前工作树包含 alpha13 未提交修改；截图可保留，运行日志不应提交。

## 8. 下一步

1. 清理运行日志，检查 `git diff`，完成 alpha13 本地提交（不 push、不部署）。
2. 复核教师端审批后报告展示方案，明确最小必要字段和授权审计。
3. 增加真实讯飞响应契约、超时/限流/重试及报告过期测试。
4. 做桌面端教师/学生视觉回归，再规划 alpha14；移动端保持兼容。
5. 上线前完成人工心理专业审核、法律/隐私评估、算法/生成式应用登记和密钥轮换。

## 9. 不得改动/必须遵守

- 禁止生产部署、上传服务器、`git push`、操作线上数据；只在本地分支 `codex/guardian-agent-v5` 工作。
- 不修改生产备份、数据库、日志、`.env`；不得提交密钥、密码、Cookie、用户原文或真实未成年人数据。
- 身份只能由 HttpOnly 登录会话确定，禁止仅凭前端 `user_id` 越权；敏感读取必须审计。
- 危机安全规则覆盖所有 Agent：不生成普通方案或游戏反馈，提供可信成年人/12356/110/120路径。
- 不展示模型私有思维链；不声称专家会诊、临床验证、诊断或量表分数；模型失败必须真实降级。
- 每次更新同步版本、`CHANGELOG.md`、测试和本地 Git 提交，并保留可回滚历史。
