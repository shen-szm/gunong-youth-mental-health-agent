# 双平台发布与本地回滚

## 原则

- 开源仓库使用独立目录和全新 Git 历史，不连接原项目的生产远端。
- 每次公开发布只从 `main` 的干净工作树执行。
- 凭据仅保存在 Git Credential Manager、GitHub CLI 或平台登录会话中，禁止写入仓库和脚本。
- GitHub 与 Gitee 使用两个独立远端：`github`、`gitee`。
- 代码通过安全扫描、前后端测试后才允许发布。

## 版本步骤

1. 按语义化版本更新 `VERSION`、`frontend/package.json`、`frontend/package-lock.json`、`backend/config.py` 和 `CHANGELOG.md`。
2. 提交变更并确认 `git status` 为空。
3. 运行 `./scripts/release.ps1`，仅生成本地快照。
4. 检查生成的 ZIP、`manifest.json` 和 `SHA256SUMS.txt`。
5. 首次使用 `git remote add github <GitHub 仓库 URL>` 与 `git remote add gitee <Gitee 仓库 URL>` 配置远端。
6. 运行 `./scripts/release.ps1 -Publish` 同步发布两个平台。

## 回滚

本地快照位于开源仓库同级的 `gunong-release-archives/v<版本>/`。优先通过 Git 标签新建修复分支；如 Git 仓库不可用，可校验 SHA-256 后解压对应 ZIP。不要覆盖已有版本目录，也不要删除旧标签。

发布脚本不会自动部署服务器，也不会改动原项目数据库、日志、环境变量或历史提交。
