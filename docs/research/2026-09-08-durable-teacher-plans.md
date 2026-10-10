# 持久化教师计划：LangGraph 接入记录

日期：2026-09-08。仅本地开发试点，未上线，非完整业务任务执行。

## 实际复用

安装固定版本 LangGraph 1.2.11、langgraph-checkpoint-sqlite 3.1.1，使用官方 StateGraph、SqliteSaver、interrupt 和 Command(resume=...)。MIT 许可位于 backend/third-party-langgraph.txt，安装入口 backend/requirements-agent.txt。pip check 无冲突；传递依赖尚未制作跨平台锁，生产发布前需在目标 Python/Linux 环境验证并锁定。

- https://docs.langchain.com/oss/python/langgraph/interrupts
- https://docs.langchain.com/oss/python/langgraph/persistence

执行图现在真实完成的是：形成受限计划 → 保存 checkpoint → 等待确认 → 新请求/新进程恢复 → 保存 plan_approved 或 cancelled。plan_approved 不等于工作报告生成，更不等于教师实际关怀完成。

## 数据与并发边界

- 只保存枚举契约、教师所有者 ID、计划工具名称、摘要哈希、到期时间与状态；不读取、复制学生资料，不调用外部模型。
- 以教师 ID 和请求 UUID 派生幂等任务 ID；相同请求返回相同任务，同一请求改变契约返回冲突。
- 确认必须匹配契约摘要，重复同一决定幂等，反向决定冲突；更改条件当前需新建任务，不伪称已实现动态重规划。
- 独立 coordination.sqlite 的 BEGIN IMMEDIATE 在操作期间持有本机跨进程互斥，checkpoint 写入另一数据库，避免并发恢复重复确认；进程退出释放锁。锁等待超过 2 秒返回暂不可用，不无限阻塞。
- 每次读取、确认与删除均验证教师角色和任务所有者；试点 API 使用数据库重读角色。这里没有学生访问授权，后续业务工具必须单独重检学生授权。
- checkpoint 与写入记录通过官方 delete_thread 清理；过期计划访问时删除并拒绝恢复。尚未接入后台主动到期清理、账户注销清理与备份清理，因此默认关闭，不能在此状态宣称满足生产全生命周期留存。
- 禁用该图 LangSmith tracing，不使用云端调试或上传 checkpoint。
- 单机本地磁盘 SQLite 试点，不支持多机共享文件部署。数据库文件存放 backend/.teacher-plan-runtime/，已忽略提交；生产启用前还需目录权限、磁盘备份、容量及高并发评估。

## API

ENABLE_TEACHER_DURABLE_PLANS 默认 false；默认不打开存储目录，也不导入可选 LangGraph 包。

- POST /api/teacher/tasks/durable-plans：request_id(UUID)、contract。
- GET /api/teacher/tasks/durable-plans/{task_id}：只读，不自动执行。
- POST /api/teacher/tasks/durable-plans/{task_id}/decision：digest、approved(boolean)。
- DELETE /api/teacher/tasks/durable-plans/{task_id}：删除本人任务与 checkpoint。

原 /preview 保留，可独立验证 LoRA；持久化计划目前明确标注 source=local_rules，没有将规则计划冒充模型规划。

## 验证与后续

新增测试覆盖独立 Python 进程恢复、重复创建/确认、并发确认、取消冲突、陈旧摘要、跨教师访问、角色撤销、过期与删除，以及 API 完整流程。

上一轮午夜后今日活跃测试失败已定位并修正测试数据：相关 MoodRecord/ChatMessage 现在与真实 mood/chat API 一样显式传 china_now_naive()，避免测试依赖 SQLite UTC 默认时间；没有更改生产时间规则或迁移旧数据。

下一阶段接入实际教师工具、工具级幂等与授权撤销处理、失败记录和重试预算，再连接教师 UI。当前没有成果生成工具或通用后台 worker，不应宣称已完成端到端自主执行。
