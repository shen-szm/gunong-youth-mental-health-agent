# 咕哝：面向高校学生的情绪陪伴与校园关怀智能体

咕哝是面向高中生与大学生、教师与家长的心理健康支持型多智能体应用。项目将学生端的倾诉、情绪整理和陪伴体验，与教师端的权限审批、安全分流、证据回溯和支持工单连接成可审计的闭环。线上服务见 [guunoo.online](https://guunoo.online)（已上线并完成 ICP 备案）。

> 本项目不提供心理诊断或治疗，不生成临床量表分数，不能替代持证心理专业人员、医疗机构或紧急服务。

本仓库提供可部署的工程参考实现，但公开源码本身不等于已完成面向未成年人的上线合规。接入真实用户前必须完成持证专业人员审核、监护与学校职责设计、数据保护影响评估、应急演练、资源复核和适用法律评估。

**版本说明**：本仓库 `main` 分支是 2026 年 8 月的开源基线。线上版本（v5.1.0-alpha.43）在此之上持续迭代：接入 DeepSeek 生成朋友式回应（对话原文会发送给所接入的模型，并在页面内明确告知），新增倾听记忆、近两周状态自评等能力；相应源码位于仓库的开发分支。

## 核心能力

- 学生端：像素房间、宠物陪伴、正常聊天、倾诉结束确认、非诊断性小结和下一步行动。
- 教师端：今日任务队列、预警处理、审批式原文访问、Agent 工单进度、证据定位和人工任务确认。
- 安全机制：确定性危机规则优先、HttpOnly 会话、角色权限、职责范围、敏感访问审计和最少必要数据。
- Agent 工作流：安全分流、观察摘要、资源检索、行动草案、交叉复核和教师裁决。
- 可验收交付：结构化支持方案、版本化报告、回访任务、测试与本地版本快照。

## 安全边界

- 普通教师只能访问其职责范围内的学生，并且查看原文前必须获得管理员教师审批。
- 管理员教师可以直接进入支持工单，但所有敏感读取仍记录审计。
- 危机信号强制覆盖普通建议，优先提示线下陪伴、可信成年人和 12356、110、120。
- 不把聊天正文默认发送给第三方模型；外部 AI 必须通过环境变量和明确同意启用。
- 仓库不包含数据库、日志、真实账号、密码、API 密钥、服务器地址或用户数据。

更完整的边界见 [AI_SAFETY.md](AI_SAFETY.md)、[PRIVACY.md](PRIVACY.md) 和 [SECURITY.md](SECURITY.md)。

## 技术栈

- 前端：Vue 3、Vite、Pinia、Vue Router、Axios
- 后端：FastAPI、Pydantic、SQLAlchemy
- 数据库：本地开发默认 SQLite，可通过环境变量配置其他数据库
- AI：讯飞星火能力作为可选结构化文字生成器；危机判断、权限和输出校验由后端规则强制执行

## 本地运行

### 1. 后端

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env  # Windows
# cp .env.example .env  # macOS/Linux
python -m uvicorn main:app --host 127.0.0.1 --port 8001
```

不要把 `.env` 提交到 Git。只有需要外部模型时才填写相应密钥。

### 2. 前端

需要 Node.js 20.19+ 或 22.12+。

```bash
cd frontend
npm ci
npm run dev -- --host 127.0.0.1
```

如后端端口不是 `8001`，设置 `VITE_API_TARGET` 后再启动前端。

### 3. 管理员教师

项目不提供默认管理员账号或密码。仅可通过本地环境变量显式初始化：

```env
ADMIN_USERNAME=
ADMIN_PASSWORD=
```

密码必须至少 12 位，并应使用密码管理器生成。生产环境需要单独配置安全 Cookie、HTTPS 和密钥轮换。

## 测试

```bash
cd frontend
npm ci
npm run build
node --test tests/*.test.mjs

cd ../backend
python -m unittest discover -s tests -v
```

浏览器端到端测试需要本地服务运行后显式启用，详见测试文件头部说明。

## 版本与双平台发布

版本遵循语义化版本和预发布标识。每次公开发布必须：

1. 更新 `VERSION`、前端包版本、后端版本与 `CHANGELOG.md`。
2. 执行 `scripts/verify-public-repo.ps1`。
3. 创建本地不可变源码快照和 SHA-256 校验文件。
4. 创建带注释 Git 标签。
5. 同步推送 GitHub 与 Gitee。

完整流程见 [docs/RELEASE_PROCESS.md](docs/RELEASE_PROCESS.md)。发布脚本不会读取或保存平台密码和访问令牌。

## 贡献

提交代码前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 和 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。安全漏洞请不要提交公开 Issue，应按 [SECURITY.md](SECURITY.md) 私下报告。

## 许可证

软件代码采用 [Apache License 2.0](LICENSE)。媒体素材的授权范围单独列在 [ASSET_LICENSES.md](ASSET_LICENSES.md)；没有明确来源与授权的媒体不得加入公开版本。

公开版不附带再分发权未核验的音视频。自有部署如需启用可选媒体，请先阅读 [媒体配置说明](docs/MEDIA_SETUP.md) 并补全素材授权记录。
