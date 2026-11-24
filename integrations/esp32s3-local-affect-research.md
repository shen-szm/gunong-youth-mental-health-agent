# OpenDeskBotV2 的 ESP32-S3 R8 本地情绪线索识别选型

核查日期：2026-10-24。这里的“情绪”仅指声音或面部表情的机器分类结果，不等同于学生的真实感受或心理诊断。以下项目均未在现有 DeskBot 固件上完成合并、编译和真机满载验证。

## 现有硬件与固件约束

- [DeskBot V2 固件](https://github.com/tudoom/OpenDeskBotV2/blob/main/hardware/README.md)为 ESP32-S3、PDM 麦克风、OV3660 摄像头、USB 优先且 Wi-Fi 可回连电脑；电脑负责云端会话。语音 16 kHz、每 20 ms 为 320 个 PCM 样本，经 Opus 上传；摄像头以 JPEG 上传。相机和 Opus 已与显示、舵机并行。
- [V2 PlatformIO 配置](https://github.com/tudoom/OpenDeskBotV2/blob/main/hardware/platformio.ini)是 16 MB Flash、八线 PSRAM，并保持两个相机缓冲。R8 应先在实机启动日志确认可用 PSRAM 为 8 MB。
- [固件内部 RAM 预算](https://github.com/tudoom/OpenDeskBotV2/blob/main/hardware/docs/MEMORY_BUDGET.md)记录：USB 空闲内部堆约 137 KB、最大连续块约 59 KB；Wi-Fi 与语音满载时约 72 KB、最大连续块约 31.7 KB，低于 28 KB 被视为回归。配网机器开机时会停用板载 ESP-SR AFE。新增模型的 arena、PCM 环形缓冲和大任务栈必须优先放 PSRAM，不能按独立开发板的空载内存推断可用性。

## 候选项目

| 项目 | 可复用部分 | 与现有 DeskBot 的差距 | 结论 |
| --- | --- | --- | --- |
| [ALQAI EmotionCam](https://github.com/Dyia-Alqaisi/esp32s3-tinyml-emotion-cam) | 同为 ESP32-S3 R8N16、OV3660；有 PlatformIO 固件、JPEG 解码、128×128 INT8 表情分类流程，四类为 neutral/happy/sad/surprise。 | 当前实现从 SD 卡读取模型，预留 [至多 4 MB 模型和 3 MB arena](https://github.com/Dyia-Alqaisi/esp32s3-tinyml-emotion-cam/blob/main/phaseThree/include/AiConfig.h)。仓库未提交现成 `.tflite`，需自行训练；它使用中心裁切而不是可靠的人脸定位。代码未证明可与 DeskBot 的 Opus、双相机缓冲和显示共存。仓库 README 声称 MIT，但仓库树中没有独立 LICENSE 文件，复用前须确认授权。 | **视觉原型参考，不能直接烧录到现有机器人。** |
| [HugoMitre Anger-Speaker-Recognition-ESP32](https://github.com/HugoMitre/Anger-Speaker-Recognition-ESP32) | 已公开中文和英文情感语料训练流程以及 [29,488 B 的 INT8 愤怒二分类模型](https://github.com/HugoMitre/Anger-Speaker-Recognition-ESP32/tree/main/outputs/anger)；作者报告该模型 arena 为 59.7 KB。 | 仓库主要是 Python 训练、量化和评估资料；未见可移植 ESP32 固件。性能表部分耗时是估算，未证明和 DeskBot 同时运行。二分类“愤怒”不覆盖悲伤、焦虑或心理风险。仓库 README 显示 MIT 标识，但未见 LICENSE 文件。 | **语音模型研究参考；须补完整固件和授权确认。** |
| [Espressif ESP-DL 人脸检测](https://github.com/espressif/esp-dl/tree/master/models/human_face_detect) | 官方 ESP32-S3 模型，可给相机帧定位人脸；官方列出 S3 上两阶段模型的推理耗时。 | 只检测人脸，不识别情绪；需另训练小型表情分类器。官方 [模型目录](https://github.com/espressif/esp-dl/blob/master/models/README.md)没有 S3 表情模型。 | **适合作为视觉前处理，不是完整情绪识别方案。** |
| [Espressif esp-tflite-micro / micro_speech](https://github.com/espressif/esp-tflite-micro/tree/master/examples/micro_speech) | 官方 ESP32-S3 音频推理底座，可换成自训 INT8 声学分类模型。 | 示例是关键词识别，不是情绪识别；必须重新收集、标注并验证目标学生群体的语音。 | **最稳妥的自研语音固件底座。** |
| [worthant edge-ai-voice-recognition](https://github.com/worthant/edge-ai-voice-recognition) | 完整 ESP32-S3 MFCC、ESP-DSP、INT8 DS-CNN、ESP-NN 固件与训练流程。 | 当前模型识别关键词，不识别情绪；作者把 140 KB arena 放内部 RAM，超过 DeskBot 满载剩余内存。需改小模型或改为 PSRAM 并重新测时延。 | **可借 MFCC/训练结构，不能原样并入。** |

[Espressif 官方表情识别示例](https://github.com/espressif/esp-iot-solution/tree/master/examples/ai/esp_dl/emotion_recognition)只列 ESP32-P4 和 ESP32-S31，模型也为这些芯片制作，不能把官方示例当作 ESP32-S3 即用方案。

## 推荐的适配顺序

1. **先做语音小模型实验。** 在现有 [`audio_capture.cpp`](https://github.com/tudoom/OpenDeskBotV2/blob/main/hardware/firmware/audio_capture.cpp)的 20 ms PDM/PCM 流上加只读分支，绝不再开一个 I2S 消费者；将约 2 秒 PCM 环形缓冲置于 PSRAM，保持原 Opus 通路不变。只在用户语音段结束后启动低优先级推理，先测试“声音较激动/不确定”这样的声学线索，不把分类结果当成心理结论。
2. **先跑基准，再定模型。** 分别测 USB、Wi-Fi、语音播报、相机预览四种状态下的内部最大连续块、PSRAM 剩余量、Opus 丢帧、模型耗时和温度。Wi-Fi 语音满载时内部最大连续块要维持至少 28 KB。模型与训练前处理必须严格同频率、窗长和量化参数；必须用中文学生真实使用环境的授权数据检验跨人、噪声与设备差异。
3. **再做低频视觉实验。** 若还需要视觉，用现有 [`camera.cpp`](https://github.com/tudoom/OpenDeskBotV2/blob/main/hardware/firmware/camera.cpp)获取经用户授权的偶发快照，先在独立固件验证人脸定位和缩小后的表情分类器；仅在语音空闲时运行。ALQAI 的 SD 卡、引脚和显示代码不要整体移植，模型应考虑现有 16 MB Flash 分区或客户端管理的模型分发。没有真机 PSRAM 与延迟数据前不承诺双模态同板并发。
4. **接回电脑和网站。** 设备仅向 DeskBot 电脑客户端发送 `{source, label, confidence, time_ms, model_version}` 等短元数据；电脑端与当前语音轮次对齐。咕哝网站的学生账号、倾诉记录和安全分流继续由现有机器人网关负责。默认不保存原始声纹/人脸图像，也不因分类结果自动生成风险告警或更改学生档案；只有用户明确允许并确认含义后才把线索纳入记录。

心理支持场景需把“模型看到的表情/声学线索”和“学生自述”分开。研究指出单凭面部动作推断情绪缺乏稳定的一一对应关系；表演语音训练的模型也存在跨语料、跨场景泛化问题：[面部表情综述](https://doi.org/10.1177/1529100619832930)、[跨语料语音情绪研究](https://arxiv.org/abs/2207.02104)。因此回复应采用可纠正的询问，例如“听起来你可能有点激动，我理解对吗？”，而不是断言学生的情绪或病情。
