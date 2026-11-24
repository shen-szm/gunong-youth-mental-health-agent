# OpenDeskBotV2 V2 camera-only probe

This temporary firmware isolates camera initialisation and capture from the
desktop application, audio, display, and servos. It uses the upstream V2 board
pin map and a 20 MHz XCLK from the beginning, suitable for the OV3660 module.

It replaces the application firmware while installed. The normal desktop app
will show the robot offline until the original 0.0.59 firmware is restored.
Neither this probe nor the restore procedure should erase flash; avoid
`erase_flash` for this diagnostic. Preserve the original firmware package.

1. Close OpenDeskBotV2 so it releases COM17. Confirm the device is the V2
   16 MB flash / 8 MB PSRAM board, not a XIAO Sense board.
2. Use the prebuilt `dist/camera-probe.bin`. To rebuild on Windows, copy this
   source project to an ASCII-only path first (the linker fails on a Chinese
   workspace path) and run `pio run -e deskbot_v2_camera_probe` there.
3. Run `python -m esptool --chip esp32s3 --port COM17 write_flash 0x10000
   dist/camera-probe.bin` to write **only the application**. Do not use
   PlatformIO's `-t upload` target, which may write bootloader and partitions.
4. Open `pio device monitor -p COM17 -b 115200` and record several `[PROBE]`
   cycles. A valid frame has `jpeg=1` and `bytes>0`.
5. Close the monitor. Restore the original application image from the
   checksum-verified official v0.9 firmware package in `dist/` with
   `python -m esptool --chip esp32s3 --port COM17 write_flash 0x10000
   dist/OpenDeskBotV2-firmware-0.0.59/firmware.bin`. Then reopen OpenDeskBotV2.
   The package's matching firmware is 0.0.59.

Interpretation: a good JPEG under this probe points to an issue in the normal
firmware's camera initialisation or concurrent workload. Repeated `init=0x106`
or successful sensor identification followed by zero sync edges and zero frames
points toward the module, FPC connector, supply/control lines, or lower-level
camera driver. A failed probe alone does not prove a particular PCB is defective.
