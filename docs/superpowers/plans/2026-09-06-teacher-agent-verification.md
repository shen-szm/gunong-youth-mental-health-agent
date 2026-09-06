# 教师 Agent 可验收能力与桌面工具优化

## 设计与复用

- 按 `impeccable` 产品界面规范，保留既有教师工作台绿色体系，用列表、轻量分隔与单个流程核查面板呈现信息；减少重复卡片，不改变移动端入口布局。
- 沿用项目中的 [Vue Flow](https://github.com/bcakmakoglu/vue-flow) 1.48.2。教师图展示服务端报告工作流的顺序与快照，不宣称实时流式执行或模型私有思维过程。
- 使用 [Lucide 官方 Vue 包](https://lucide.dev/guide/vue) `@lucide/vue` 1.41.0，显式导入用到的图标，构建时可 tree-shake。源项目：[lucide-icons/lucide](https://github.com/lucide-icons/lucide)。完整 ISC 与衍生 Feather MIT 许可随站点发布于 `third-party-icons.txt`。
- 教师报告图和验证档案动态加载；移动端不加载新增教师图，也不显示验证入口。

## 已实现路径

教师已授权工单 → 学生 Agent 有效结构化接力 → 报告七阶段处理 → 工具/状态/结果可点选核查 → 证据审计 → 人工签署/退回 → PDF 下载。

图与报告状态均取自实际报告，未执行的线下支持不会标记完成。修正紧急路径 ContextAnalyst / SupportPlanner 的停止状态与结果文字不一致问题。历史报告保持原快照，不篡改历史记录。

## 验证档案

`backend/scripts/verify_teacher_cases.py` 复用现有 API 测试夹具，在独立内存 SQLite 数据库中执行。每例重新创建并销毁数据库，不连接生产数据。外部 AI 开关强制关闭，教师模型调用被失败哨兵拦截。

- 8 类、24 例：学业、睡眠、同伴、家庭沟通、积极体验、即时安全、人身保护、信息不足。
- 非空类别分别使用 1/3/6 条情绪记录；信息不足重复验证 3 次。并非 24 种独立心理情况。
- 检验学生对话、学生交付核验、教师接力、权限拒绝、工单生成、报告快照、引用有效性、无外传、PDF 响应、风险路径、停止普通支持和缺失信息。
- 档案写入 `frontend/src/data/teacher-verification.json`，含逐项布尔结果、真实生成报告、执行时间、案例定义 SHA-256 与报告引擎 SHA-256。失败会保留并令脚本以非零退出；前端同时提供失败筛选。
- 页面统一注明“合成案例 · 本地确定性 API 验证”。数字不进入真实工作台统计，不是临床效果、真实学生使用效果、外部模型质量或性能测评。

仓库根目录复现：

```powershell
backend/venv/Scripts/python.exe backend/scripts/verify_teacher_cases.py
```

前端 `teacher-verification.test.mjs` 校验汇总、来源、唯一 ID、引擎哈希和逐例状态。浏览器回归覆盖节点键盘操作、紧急停止、类型筛选、失败空状态与移动端恢复。

2026-09-06 本地结果：24/24 案例、270/270 断言；后端 117/117、前端 108/108 回归通过。最终生产构建在 1440px、1024px、390px 浏览器视口连续三次通过交互验证，并回归短暂 1×1 视口不丢失任务。生产依赖审计为 0 漏洞；仍有既有主包/Phaser 大包构建提示。验证档案独立 chunk gzip 约 15.4 KB。

## 发布约束

alpha.35 仅替换后端 `config.py`、`teacher_review_engine.py` 与已测试前端构建。合成案例不写入生产数据库。发布脚本验证 alpha.34 基线并备份旧代码和前端，只修改 `.env` 的公开 `RELEASE_VERSION` 字段；任何健康检查失败均回滚。

通过 `.gitattributes` 固定 `deploy/*.sh` 为 LF，避免 Windows `git archive` 按本地换行规则导出后无法在 Linux 执行。脚本在服务切换前执行 `bash -n` 检查。
