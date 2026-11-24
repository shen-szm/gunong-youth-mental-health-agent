# OpenDeskBotV2 摄像头独立固件测试

测试对象：COM17，ESP32-S3，8 MB PSRAM，16 MB Flash，OV3660 摄像头。

## 操作与恢复

- 测试前读取了原分区表及完整应用分区（`dist/original-app-backup.bin`）。原应用镜像与官方 0.0.59 `firmware.bin` 逐字节一致。
- 仅在应用区 `0x10000` 写入 `dist/camera-probe.bin`；未擦除整片 Flash，未改写引导程序、分区表或 NVS。
- 测试后将官方 0.0.59 应用镜像写回 `0x10000`。重新读取整个应用分区后，与测试前备份逐字节一致，SHA-256 均为 `8aba832a2a271dfb96577c916457eb1b2d618a8aab26a42e46870ecb42cf7f52`。

## 观测

独立测试程序只初始化相机，不运行桌面通信、音频、屏幕或舵机。使用 V2 主板引脚、20 MHz XCLK、JPEG QVGA。

- PSRAM 空闲约 8.38 MB。
- `esp_camera_init` 返回 `0x0`，识别传感器 PID `0x3660`（OV3660）。
- 120 ms 采样中 VSYNC、HREF、PCLK 均未检测到边沿。
- 连续两轮共六次取帧均在约 4 秒后超时，`jpeg=0 bytes=0`。

原始记录：`dist/probe-log.txt`。`gdma_disconnect` 出现在取帧失败后的反初始化阶段，不能单独视为根因。

## 结论与下一步

相机无图像的问题在不运行原应用其他功能时仍然存在，因此桌面程序负载或外设并发不是充分解释。传感器能通过控制总线报告 PID，但图像数据通路没有成功输出可接收的帧。仍需区分摄像头模组、排线/连接器、供电、主板线路，以及底层驱动兼容性；这次测试不能单独证明主板损坏。

下一步在相机被初始化期间，用万用表直流电压挡，黑表笔接摄像头 GND（资料中的 2 或 15 脚），红表笔分别测模组侧 4 脚 VDD2.8V、10 脚 VDD1.5V、11 脚 DOVDD1.8/2.8V。先确认实际线序和探针位置，避免相邻触点短路。若缺一条电源，沿该电源从板端到模组端排查；若三条均正常，优先更换已知良好的排线/模组进行交叉测试。

## 更换新摄像头后的复测

使用同一台 COM17 设备、同一份测试镜像和相同的 20 MHz XCLK 配置。测试前的整个应用分区与第一次测试前备份逐字节一致。

- 新模组依然识别为 OV3660（PID `0x3660`），`esp_camera_init=0x0`。
- 连续两轮共六次取帧均约 4 秒超时，`jpeg=0 bytes=0`；120 ms 采样中仍未检测到 VSYNC、HREF、PCLK 边沿。
- 原始记录：`dist/new-camera-probe-log.txt`。
- 测试后恢复官方 0.0.59。再次读取整个应用分区，与复测前备份逐字节一致，SHA-256 仍为 `8aba832a2a271dfb96577c916457eb1b2d618a8aab26a42e46870ecb42cf7f52`。

两个摄像头表现一致，单个摄像头模组故障的可能性降低。下一步优先检查共用部分：板端连接器与 FPC 接触、摄像头三路电源，以及 VSYNC/HREF/PCLK 从模组到主控的连接。若新模组沿用了同一根排线，仍应对排线做交叉替换或通断检查。

后续收到的 OV2640 模组图与 FPC1 原理图表明主板焊盘编号与模组脚号相反，详见 `PIN_MAPPING.md`。上次新模组测试实际读取 PID `0x3660`（OV3660），而主板对应模组 10 脚的供电网名为 `VCC_1V2`；先前 OV3660 模组图将该脚标为 1.5 V。应优先实测 FPC1 15 号焊盘与模组 10 脚的电压，并核实实际模组规格。这个潜在电压不匹配无法通过重排 ESP32 数据 GPIO 解决。

## 外部 OV3660 诊断包试验

用户提供 `OpenDeskBotV2_OV3660_Diagnostic.rar`，SHA-256 为 `E19F5820EE5FE5A88B6CA43A3502957AB21B87212A93A6BBB258CF94BBB54721`。包内只有 bootloader、partition、firmware 与整合镜像及刷机说明，没有相机驱动源码。整合镜像中的应用区与独立 `firmware.bin` 相同；它的分区表与设备原分区表不同，因此没有按包内说明写入 `0x0` 整合镜像。

仅将包内应用镜像写入现有应用区 `0x10000` 并校验成功。最初打开 COM17 过晚，错过了这个一次性自检程序的开机输出；先用原固件验证快速重启与立即监听的采集方法，再按相同方式复测包内镜像，成功得到完整日志（`dist/vendor-fast-start-log.txt`）：

```text
[V2_PROBE] MEMORY   PASS flash=16777216 psram=8388608
[V2_PROBE] LCD      PASS ST7789 mode3 offset0
[V2_PROBE] MIC      PASS n=1024 range=18676 mean=-2140
[V2_PROBE] CAMERA   FAIL xclk=10MHz pid=0x3660 no frame
[V2_PROBE] SPEAKER  PASS short quiet tone sent
```

这份镜像能读取 OV3660 ID，但在 10 MHz XCLK 下依然无帧；此前自行编译的 20 MHz 相机独立测试也无帧。包内没有驱动源码，故不能确认它使用了不同版本的相机驱动，也不能将它当作原应用的驱动替换包。自检输出格式和上游 V2 硬件测试程序相同。

随后恢复官方 0.0.59 应用，重新读取完整应用分区，与写入前备份逐字节一致，SHA-256 均为 `8aba832a2a271dfb96577c916457eb1b2d618a8aab26a42e46870ecb42cf7f52`。恢复后的 COM17 日志再次显示：传感器 PID `0x3660`、XCLK 由 10 MHz 改为 20 MHz、120 ms 同步信号采样为 `0/0/0`，随后暖机取帧 `no_frame`（`dist/post-restore-serial.txt`）。


## 2026-10-27 原始 EDA 数据独立追线与配置重写

从本地 native_docs.json 的 PCB_V2.0_Base / PAD_NET 及 U4 符号 Pin Number、Pin Name 独立导出 14 路 GPIO，未读取旧固件作为推导输入。完整链路见 PIN_MAPPING.md 和 pin_trace.json。

诊断源码已改用自动生成的 src/camera_pins_from_schematic.h，并增加 [PINMAP] 启动日志。所得 GPIO 数值与原诊断程序相同；没有声称形成不同的引脚电气行为。假设模组 n 接 FPC1 的 25-n；实物接触方向、实际 PCB 版本、模组电源规格仍需核实。

验证：PlatformIO deskbot_v2_camera_probe 编译 SUCCESS；esptool image-info 确认 ESP32-S3 / 16MB，checksum 与 validation hash 均 valid。此轮未烧录、未采集新的摄像头运行日志，也未判定摄像头恢复。

产物：dist/camera-probe-schematic.bin，394176 字节，SHA256 `392eeac40d24164c12ce9996c23c31fb0d08ccf2f3a1b2449e060768642f71ba`。


## 2026-10-27 13:10 图纸引脚诊断固件烧录实测

经用户明确要求烧录，将 camera-probe-schematic.bin 写入 COM17 / ESP32-S3 的 0x10000，写入哈希校验通过。运行资料：`D:\桌面文件\大学文件\一些比赛\讯飞杯\shengyu-web\integrations\deskbot-camera-probe\dist\schematic-flash-20261027-131036`。烧录前完整应用备份 7012352 字节，SHA256 8aba832a2a271dfb96577c916457eb1b2d618a8aab26a42e46870ecb42cf7f52。

启动 [PINMAP] 输出确认新诊断程序生效。45 秒日志包含两轮 init=0x0、PID=0x3660、XCLK=20000000；每轮软件采样同步跳变 0/0/0，三次取帧约 4 秒超时、bytes=0，共六次失败。逐行标记见本次目录 MARKED_LOG.md。未获得有效图像，不能声称修复或排除所有驱动因素。设备现保留诊断固件，不自动恢复原生产固件。


## 2026-10-27 16:09:01 恢复烧录前原固件

按用户要求恢复 preflash-app.bin 至 0x10000。写入校验通过，读回整个 0x6b0000 字节应用区域并逐字节比较，与备份完全一致。SHA256：8aba832a2a271dfb96577c916457eb1b2d618a8aab26a42e46870ecb42cf7f52。启动日志确认固件 0.0.59，原显示、音频及 USB 协议固件已恢复；摄像头仍有 no_frame / setup validation failed。设备不再运行诊断固件。启动日志：`D:\桌面文件\大学文件\一些比赛\讯飞杯\shengyu-web\integrations\deskbot-camera-probe\dist\schematic-flash-20261027-131036\restored-startup-log.txt`。串口采集已结束并释放 COM17。
