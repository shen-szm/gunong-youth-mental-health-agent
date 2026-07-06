# 2026-07-06 教师端线上基线记录

## 当前线上基线

- 域名：`https://www.guunoo.online`
- 恢复时间：2026-07-06
- 前端恢复来源：`/opt/shengyu/backups/20260624-001248/frontend-dist`
- 当前线上前端主资源：`/assets/index-CmwioJLL.js`
- 恢复前 4.3.2 前端备份：`/opt/shengyu/backups/restore-before-/frontend-dist-current`
- 后端服务：`shengyu`，已验证为 `active`
- 后端教师端路由入口：`/api/teacher`

## 已确认需要保留的教师端能力

- 学生情绪状态查看
- 学生情绪预警
- 预警详情查看
- 预警处理闭环
- 班级概览
- AI 班会内容生成
- 班会模板
- 学生画像 / 学生详情
- 教师端账号与管理能力

## 已验证的后端接口

- `GET /api/teacher/class-overview`
- `GET /api/teacher/emotion-trend`
- `GET /api/teacher/student-list`
- `GET /api/teacher/warning-list`
- `POST /api/teacher/warning/{warning_id}/handle`
- `GET /api/teacher/warning/{warning_id}/detail`
- `POST /api/teacher/lesson-plan/generate`
- `GET /api/teacher/lesson-plan/templates`
- `GET /api/teacher/students`
- `GET /api/teacher/students/{student_id}/profile`
- `POST /api/teacher/students/{student_id}/sensitive-context/access`
- `GET /api/teacher/accounts`
- `PATCH /api/teacher/accounts/{account_id}`

## 验证证据

- 线上主资源 `/assets/index-CmwioJLL.js` 已确认包含：`/api/teacher`、`class-overview`、`warning`、`lesson-plan`、`班会`、`预警`。
- `GET /api/teacher/class-overview?user_id=1` 返回过：`total_students=13`、`pending_warnings=5`、`risk_counts.low=6`、`risk_counts.middle=5`、`risk_counts.high=2`。
- `GET /api/teacher/lesson-plan/templates?user_id=1` 返回过：`新生适应`、`考前减压`、`宿舍人际`、`情绪管理`、`生命教育` 等模板。

## 重要约束

- 当前本地 `frontend/src/views/AdminView.vue` 不是线上恢复后的完整教师端源码，只是简化管理页。
- 服务器 `/opt/shengyu/frontend/src/views/AdminView.vue` 也未找到完整教师端 UI 源码；目前完整教师端前端主要存在于已恢复的编译产物中。
- 在源码基线对齐前，不要直接用本地前端重新部署覆盖线上，否则会再次丢失教师端的情绪预警、处理、班会生成等功能。
- 后续“新手引导、交互优化、样式优化、版本号更新、日志记录”必须基于这个教师端基线继续做。

## 后续修改策略

1. 优先从服务器备份、临时压缩包或历史产物中找回匹配的教师端源码。
2. 如果找不到源码，则基于 `/api/teacher/*` 接口契约和当前线上编译产物行为，重建教师端源码。
3. 新手引导要覆盖教师端核心路径：查看班级概览、定位预警学生、打开预警详情、处理预警、生成班会方案。
4. 每次功能更新都要同步记录版本号、变更日志和 Git commit，区分小版本修复与大版本功能更新。
