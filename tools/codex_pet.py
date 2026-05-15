#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
import time


DEFAULT_PORT = "/dev/cu.usbmodem101"
BAUD = "115200"


def configure_port(port: str) -> None:
    subprocess.run(
        ["stty", "-f", port, BAUD, "raw", "-echo"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def send_command(port: str, command: str) -> None:
    configure_port(port)
    fd = os.open(port, os.O_WRONLY | os.O_NOCTTY)
    try:
        os.write(fd, f"{command.strip()}\n".encode("utf-8"))
        time.sleep(0.05)
    finally:
        os.close(fd)


def main() -> int:
    parser = argparse.ArgumentParser(description="Send commands to the Codex OLED pet.")
    parser.add_argument(
        "command",
        nargs="*",
        help="Command to send: dance, think, idle, or msg <text>.",
    )
    parser.add_argument("--port", default=DEFAULT_PORT, help=f"Serial port, default {DEFAULT_PORT}.")
    args = parser.parse_args()

    command = " ".join(args.command).strip() or "dance"
    try:
        send_command(args.port, command)
    except FileNotFoundError:
        print(f"Serial port not found: {args.port}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError:
        print(f"Could not configure serial port: {args.port}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Could not write to {args.port}: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
