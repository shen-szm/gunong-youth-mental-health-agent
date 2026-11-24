# 摄像头故障日志标记（更换新模组后）

## 原固件运行日志：2026-10-27 09:47–09:48

原文件：`C:\Users\31795\AppData\Local\OpenDeskBotV2\logs\core.log`。

| 原文件行号 | 日志关键内容 | 标记与含义 |
| ---: | --- | --- |
| 61363 | `camera health ... ready=False last_frame_ms=0` | **异常**：摄像头未就绪，尚无图像帧。 |
| 61434 | `[CAMERA] supervisor setup attempt=5` | 设备第 5 次尝试初始化相机。 |
| 61435 | `[CAMERA_HEAP] stage=before_init ... psram_free=7516928` | 初始化前仍有约 7.5 MB PSRAM。 |
| 61442 | `[CAMERA_HEAP] stage=init_failed ... psram_free=7516928` | **异常**：初始化失败；失败前后可用内存基本未变。 |
| 61443 | `[ERROR] [CAMERA] setup failed 0x106` | **关键故障行**：相机初始化返回 `0x106`。 |
| 61444 | `supervisor setup failed attempt=5 error=0x106 retry_in=120000ms` | **故障持续**：本轮失败，计划 120 秒后重试。 |

`0x106` 指向相机初始化/探测阶段，但这行日志本身不能确定是主板、排线、模组还是底层驱动。

## 新摄像头独立测试日志

原文件：`dist/new-camera-probe-log.txt`。相同结果在两轮测试中重复，以下标出第二轮：

| 原文件行号 | 日志关键内容 | 标记与含义 |
| ---: | --- | --- |
| 14 | `[PROBE] init=0x0` | 相机驱动初始化这一步成功。 |
| 15 | `[PROBE] sensor_pid=0x3660 xclk=20000000` | 控制总线读到了 OV3660 传感器 ID，XCLK 配置为 20 MHz。 |
| 16 | `[PROBE] edges_vsync=0 href=0 pclk=0 (120ms)` | **异常**：120 ms 采样内未检测到这些同步/像素时钟引脚变化；这不是示波器测量结论。 |
| 17–19 | `frame=1/2/3 jpeg=0 bytes=0 elapsed_ms≈4000` | **关键故障行**：三次取帧均在约 4 秒后超时，没有图像数据。 |

综合：正常固件在初始化阶段失败；独立程序能读出传感器 ID，但取不到图像。更换新模组后仍相同，下一步优先测模组侧 4、10、11 脚供电并检查共用的 FPC 排线、连接器和主板图像信号线路。
