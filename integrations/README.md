# OpenDeskBotV2 → 咕哝账号语音接入

适配上游 [OpenDeskBotV2](https://github.com/tudoom/OpenDeskBotV2) `1cf5050ee63b1fe4cae6b7815e565a0955f15bd6`。硬件继续经 USB / 局域网连接电脑；只有电脑端 RTC 语音大模型通路连接 `https://guunoo.online/api/robot/v1`。网站不连接串口，也不接收原始音频或摄像头画面。

## 接入步骤

1. 部署本仓库新增的后端与前端。后端启动时 `Base.metadata.create_all` 会新建 `robot_links` 表。先在正式学生账号登录网站，在个人页「桌面机器人」生成一次性显示的连接密钥。演示、匿名及教师账号不能生成。
2. 在 OpenDeskBotV2 源码根目录运行 `git apply --check <本仓库绝对路径>/integrations/opendeskbotv2-guunoo-rtc.patch`，再运行 `git apply <同一路径>`。该补丁仅改 RTC 语音模型配置，Core 的其他模型用途仍使用原配置。按上游 `service/client/README.md` 重建并安装桌面客户端。已发布的原版安装包不会自动包含此补丁。
3. 把 `GUUNOO_ROBOT_TOKEN=<从个人页复制的密钥>` 单独写入 `%LOCALAPPDATA%\OpenDeskBotV2\.env`，重启客户端。该文件只保存在个人电脑，不要提交到 Git。正常 LLM、豆包 ASR 和 TTS 配置继续按上游要求配置；补丁启用时，RTC 语音模型改为咕哝网站。
4. 关闭 OpenDeskBotV2 的主动陪伴定时任务，并由用户主动对设备讲话测试。个人页可随时撤销或轮换密钥。密钥有效期 90 天，到期后重新生成。

## 数据与行为

- 网站把语音转写文本作为 `input_type=voice` 交给现有 `/api/chat/send`。用户话语和回复保存在该学生账号的倾诉记录中，沿用现有会话归属、外部 AI 授权和安全分流规则。客户端仍会按其配置把音频交给第三方 ASR、把回复交给第三方 TTS；网站的外部 AI 授权开关不控制这两条客户端流量。机器人本机可能也保留自己的会话记录，需按上游客户端的数据设置管理。
- 网站仅接受带 `guunoo-robot-voice-v1` 语音模式标记的请求；普通客户端仅填写自定义模型 Base URL 无法启用此接入，以免表情、动作等其他模型请求误写入倾诉记录。
- 网站在高风险话语中返回已有的安全转接话术。机器人负责按其现有豆包 TTS 配置播报；该集成不等于真人在线值守、心理诊断或治疗。
- 密钥以 SHA-256 摘要保存在网站数据库，明文只在创建时返回一次；撤销后旧密钥立即失效。不要把密钥写进固件、网页源码或公开日志。

## 验证与限制

- 网站侧：`backend/venv/Scripts/python.exe -m unittest backend.tests.test_robot_gateway -v`，`cd frontend && npm run build`。
- 补丁已针对上述上游提交运行 `git apply --check` 与 Python 语法编译。尚需在重建的客户端和实体机器人上验证 RTC 请求格式、语音延迟和紧急话术播放。
- 上游 RTC Agent 也可能执行工具调用和主动任务。咕哝接口不执行工具，并拒绝已知系统发起前缀；此阶段应关闭主动陪伴，限定为用户主动语音倾诉。若需要在同一模式保留完整机器人功能，应另做通路级区分与真机测试。
