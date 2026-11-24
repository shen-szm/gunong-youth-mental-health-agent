# alpha.37 发布记录（已上线）

## 验收结果

- 后端 unittest：179 项通过。
- 前端 node 测试：116 项通过。
- PC 浏览器验收：报告分栏、返回、版本隔离、审签、需求人工核对流程通过。
- 发布脚本测试：3 项通过，覆盖精确版本替换、实验开关拦截、启动失败后的代码/前端/版本恢复。
- Vite 生产构建通过；仍有大于 500 kB 的 chunk 提示，不能声称性能优化已完成。
- 构建标识：`5.1.0-alpha.37+249a89a.dirty`，工作区尚未提交，不应将 HEAD 当作完整发布源码版本。

## 范围和限制

教师报告的 PC 审阅改进可随发布生效。完整需求核对采用人工逐项确认，不代表模型已能识别所有遗漏或危险要求。

教师自然语言规划、持久化任务试点、格式重试保持关闭；服务器没有可选 LangGraph 依赖，本次不升级依赖。任务历史、验收台等试点入口不会因代码发布自动启用。学生侧既有模型配置不变。

## 发布状态

2026-09-10 13:28（Asia/Shanghai）发布后核验：域名 guunoo.online 的 A 记录为 <SERVER_IP>；服务器健康检查为 5.1.0-alpha.37，服务 active。

初次上传被安全审批拒绝；用户明确回复“同意继续”后，已上传至 `/opt/shengyu/releases/alpha37-249a89a-20260910-075911`，通过生产预检并完成切换。前端 75 个文件的 SHA256 全部与本地一致。

准备的本地文件：`artifacts/alpha37-backend.tar`、`deploy/release-alpha37.py`、`frontend/dist`。后端归档只包含发布脚本 FILES 列表内的 10 个 Python 文件，不包含 .env、数据库、学生数据或测试凭据。

已执行：上传暂存目录 → 比较 SHA256 → 不带 --apply 通过生产基线预检 → 带 --apply 发布 → 检查服务健康、生产开关、HTTPS 页面及静态资源。不要再次运行此发布脚本：它要求 alpha.36 基线及不存在的备份目录。

旧代码和前端备份已保存在 `/opt/shengyu/backups/alpha37-249a89a-20260910-075911`。脚本仅在发布失败时自动回滚，不提供成功上线后的命令行回滚子命令。

## 线上验证

- HTTPS 首页返回 200，引用新入口 `index-CsCAvp54.js`；该 JS 与 `index-ETF0gBQp.css` 均返回 200。
- `/teacher-login` 与三份开源归属文件均返回 200。
- 未登录访问 `/api/teacher/tasks/capabilities` 返回 401。
- 新配置读取确认 `ENABLE_TEACHER_DURABLE_PLANS=False`、`ALLOW_TEACHER_TASK_PLANNER_AI=False`。
- 健康检查仍显示学生 AI、守护者 AI 及既有治理配置开启；此次未修改这些开关。
- 线上未创建测试账号、未读取学生资料、未调用外部模型。登录后的交互验收依据发布前本地 PC 测试，不声称已完成线上登录态端到端测试。

## 发布包校验值

- backend.tar：`e8496d8afe45287d3fafa44a567f2a3ee11fa1f962fb8554aa7a1ed55905915e`
- release-alpha37.py：`216a0059bf3ad79b2cf60e7736401b83810cb51f238dce324a504d55344e8d93`
- dist/index.html：`b2099387e89426d916ad9f7392c7db38d4f5c2794d48a2c7499326884ac0c83c`
