#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
import time
import fcntl
from pathlib import Path
from urllib.parse import quote_plus
from urllib.request import urlopen


DEFAULT_PORT = "/dev/cu.usbmodem101"
HOST_CACHE = Path("/tmp/codex_pet_host")
BAUD = "115200"


def default_host() -> str:
    host = os.environ.get("CODEX_PET_HOST", "").strip()
    if host:
        return host
    try:
        return HOST_CACHE.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _lock_path_for_port(port: str) -> Path:
    safe = port.replace("/", "_").replace("\\", "_").replace(":", "_")
    return Path(f"/tmp/codex_pet{safe}.lock")


def configure_port(port: str) -> None:
    subprocess.run(
        ["stty", "-f", port, BAUD, "raw", "-echo"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def send_http_command(host: str, command: str) -> int:
    base = host.rstrip("/")
    if not base.startswith(("http://", "https://")):
        base = "http://" + base
    url = f"{base}/cmd?c={quote_plus(command.strip())}"
    try:
        with urlopen(url, timeout=3) as response:
            response.read()
        return 0
    except OSError as exc:
        print(f"Could not send HTTP command to {base}: {exc}", file=sys.stderr)
        return 1


def send_command(port: str, command: str) -> int:
    """Send `command` to `port`. Returns 0 on success, nonzero on failure.

    This acquires a per-port file lock in /tmp to avoid concurrent writers.
    If the lock cannot be acquired, the call exits quickly with code 2.
    """
    lock_path = _lock_path_for_port(port)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    # Open lock file and try to acquire exclusive non-blocking lock
    try:
        lock_fd = lock_path.open("w")
    except OSError as exc:
        print(f"Could not open lock file {lock_path}: {exc}", file=sys.stderr)
        return 1

    try:
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print(f"Port busy (lock held): {port}", file=sys.stderr)
        try:
            lock_fd.close()
        except Exception:
            pass
        return 2

    # We hold the lock; perform port configuration and write
    try:
        configure_port(port)
        fd = os.open(port, os.O_WRONLY | os.O_NOCTTY)
        try:
            os.write(fd, f"{command.strip()}\n".encode("utf-8"))
            time.sleep(0.05)
        finally:
            os.close(fd)
    except FileNotFoundError:
        print(f"Serial port not found: {port}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError:
        print(f"Could not configure serial port: {port}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Could not write to {port}: {exc}", file=sys.stderr)
        return 1
    finally:
        try:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass
        try:
            lock_fd.close()
        except Exception:
            pass

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Send commands to the Codex OLED pet.")
    parser.add_argument(
        "command",
        nargs="*",
        help="Command to send: dance, think, idle, or msg <text>.",
    )
    parser.add_argument("--port", default=DEFAULT_PORT, help=f"Serial port, default {DEFAULT_PORT}.")
    parser.add_argument(
        "--host",
        default=default_host(),
        help="ESP32 HTTP host/IP. Can also be set with CODEX_PET_HOST or cached by the button daemon.",
    )
    args = parser.parse_args()

    command = " ".join(args.command).strip() or "dance"
    if args.host:
        return send_http_command(args.host, command)

    result = send_command(args.port, command)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
