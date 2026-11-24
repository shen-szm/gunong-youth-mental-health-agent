"""Capture the camera probe's serial output for a fixed duration."""

import argparse
import time
from pathlib import Path

import serial


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default="COM17")
    parser.add_argument("--seconds", type=int, default=45)
    parser.add_argument("--output", type=Path, default=Path("dist/probe-log.txt"))
    parser.add_argument("--reset", action="store_true", help="Reset the device after opening the serial port")
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with serial.Serial(args.port, 115200, timeout=1) as connection, args.output.open(
        "w", encoding="utf-8"
    ) as output:
        if args.reset:
            from esptool.reset import HardReset

            HardReset(connection, uses_usb=True)()
            connection.close()
        deadline = time.monotonic() + args.seconds
        while time.monotonic() < deadline:
            try:
                if not connection.is_open:
                    connection.open()
                line = connection.readline().decode("utf-8", errors="replace").strip()
            except (OSError, serial.SerialException):
                connection.close()
                time.sleep(0.2)
                continue
            if line:
                print(line, flush=True)
                print(line, file=output, flush=True)


if __name__ == "__main__":
    main()
