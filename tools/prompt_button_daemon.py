#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote_plus, urlparse
from urllib.request import urlopen


DEFAULT_PORT = "/dev/cu.usbmodem101"
DEFAULT_HTTP_PORT = 8765
DEFAULT_PET_HOST = os.environ.get("CODEX_PET_HOST", "")
BAUD = "115200"
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USAGE_PATH = "/tmp/codex_pet_usage.json"
LAST_RESULT_PATH = "/tmp/codex_pet_last_result.txt"
LAST_SUMMARY_PATH = "/tmp/codex_pet_last_summary.json"
PET_HOST_PATH = "/tmp/codex_pet_host"

IMPROVER_INSTRUCTIONS = """Rewrite the selected text into a clearer, stronger prompt for Codex.

Keep the user's intent, but make the prompt more actionable. Add concise context placeholders only
when useful. Do not answer the prompt. Return only the improved prompt text."""


def run(command, *, input_text=None, timeout=60):
    return subprocess.run(
        command,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def configure_port(port):
    subprocess.run(["stty", "-f", port, BAUD, "raw", "-echo"], check=True)


def send_pet_message(fd, message):
    send_pet_command(fd, f"msg {message[:60]}")


def send_pet_command(fd, command):
    try:
        if isinstance(fd, str) and fd:
            base = fd.rstrip("/")
            if not base.startswith(("http://", "https://")):
                base = "http://" + base
            with urlopen(f"{base}/cmd?c={quote_plus(command)}", timeout=3) as response:
                response.read()
        elif fd is not None:
            os.write(fd, f"{command}\n".encode("utf-8"))
    except Exception:
        pass


def remember_pet_host(host):
    if not host:
        return
    try:
        with open(PET_HOST_PATH, "w", encoding="utf-8") as host_file:
            host_file.write(host.strip() + "\n")
    except OSError:
        pass


def restore_usage(fd):
    try:
        with open(USAGE_PATH, "r", encoding="utf-8") as usage_file:
            usage = json.load(usage_file)
        session = int(usage["session"])
        context = int(usage["context"])
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return
    send_pet_command(fd, f"usage {session} {context}")


def read_clipboard():
    result = run(["pbpaste"], timeout=5)
    return result.stdout


def write_clipboard(text):
    run(["pbcopy"], input_text=text, timeout=5)


def paste_clipboard():
    script = 'tell application "System Events" to keystroke "v" using command down'
    result = run(["osascript", "-e", script], timeout=5)
    return result.returncode == 0, result.stderr.strip()


def copy_selection():
    previous_clipboard = read_clipboard()
    script = 'tell application "System Events" to keystroke "c" using command down'
    result = run(["osascript", "-e", script], timeout=5)
    if result.returncode != 0:
        return "", previous_clipboard, "macOS could not copy selection"

    time.sleep(0.2)
    selected_text = read_clipboard()
    if selected_text == previous_clipboard:
        return selected_text, previous_clipboard, "clipboard unchanged"
    return selected_text, previous_clipboard, ""


def improve_prompt(selected_text):
    prompt = f"{IMPROVER_INSTRUCTIONS}\n\nSelected text:\n{selected_text}"
    with tempfile.NamedTemporaryFile("r", encoding="utf-8", delete=False) as output_file:
        output_path = output_file.name
    try:
        result = run(
            [
                "codex",
                "exec",
                "-C",
                PROJECT_ROOT,
                "--skip-git-repo-check",
                "--disable",
                "codex_hooks",
                "--output-last-message",
                output_path,
                prompt,
            ],
            timeout=120,
        )
        try:
            with open(output_path, "r", encoding="utf-8") as final_output:
                improved = final_output.read().strip()
        except OSError:
            improved = ""
    finally:
        try:
            os.unlink(output_path)
        except OSError:
            pass

    if result.returncode != 0 or not improved:
        return "", result.stderr.strip() or "codex exec did not return text"
    return improved, ""


def compact_lines(text, *, max_lines=5, width=21):
    words = " ".join(text.replace("\n", " ").split()).split(" ")
    lines = []
    current = ""
    for word in words:
        if not word:
            continue
        if len(word) > width:
            word = word[:width]
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= width:
            current = candidate
            continue
        lines.append(current)
        current = word
        if len(lines) >= max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    return "\n".join(lines[:max_lines])


def cached_summary(cache_key):
    try:
        with open(LAST_SUMMARY_PATH, "r", encoding="utf-8") as summary_file:
            cache = json.load(summary_file)
        if cache.get("key") == cache_key and cache.get("summary"):
            return compact_lines(str(cache["summary"]))
    except (OSError, TypeError, json.JSONDecodeError):
        pass
    return ""


def save_summary(cache_key, summary):
    try:
        with open(LAST_SUMMARY_PATH, "w", encoding="utf-8") as summary_file:
            json.dump({"key": cache_key, "summary": summary}, summary_file)
    except OSError:
        pass


def summarize_last_result():
    try:
        text = open(LAST_RESULT_PATH, "r", encoding="utf-8").read().strip()
    except OSError:
        text = ""

    if not text:
        result = run(
            [
                "git",
                "log",
                "-1",
                "--pretty=format:Last commit %h %s",
            ],
            timeout=5,
        )
        text = result.stdout.strip() or "No recent Codex result yet"

    cache_key = hashlib.sha256(text.encode("utf-8")).hexdigest()
    summary = cached_summary(cache_key)
    if summary:
        return summary

    prompt = """Summarize this Codex result for a 128x64 OLED screen.

Return exactly 5 short lines. Each line must be 21 characters or fewer.
Do not use bullets, markdown, emojis, or quotes.

Result:
""" + text

    with tempfile.NamedTemporaryFile("r", encoding="utf-8", delete=False) as output_file:
        output_path = output_file.name
    try:
        result = run(
            [
                "codex",
                "exec",
                "-C",
                PROJECT_ROOT,
                "--skip-git-repo-check",
                "--disable",
                "codex_hooks",
                "--output-last-message",
                output_path,
                prompt,
            ],
            timeout=60,
        )
        try:
            with open(output_path, "r", encoding="utf-8") as final_output:
                summary = final_output.read().strip()
        except OSError:
            summary = ""
    finally:
        try:
            os.unlink(output_path)
        except OSError:
            pass

    if result.returncode != 0 or not summary:
        summary = compact_lines(text)
    summary = compact_lines(summary)
    save_summary(cache_key, summary)
    return summary


def handle_improve_button(fd):
    restore_usage(fd)
    send_pet_command(fd, "think")
    selected_text, previous_clipboard, selection_error = copy_selection()
    if not selected_text.strip():
        selected_text = previous_clipboard

    if not selected_text.strip():
        send_pet_message(fd, "copy/select text")
        print(f"No selected text: {selection_error}", file=sys.stderr)
        return

    if selection_error:
        print(f"Using clipboard fallback: {selection_error}", file=sys.stderr)

    improved, improve_error = improve_prompt(selected_text)
    if not improved:
        write_clipboard(previous_clipboard)
        send_pet_message(fd, "improve failed")
        print(improve_error, file=sys.stderr)
        return

    write_clipboard(improved)
    pasted, paste_error = paste_clipboard()
    if pasted:
        send_pet_message(fd, "prompt pasted")
        print("Improved prompt pasted.")
    else:
        send_pet_message(fd, "paste blocked")
        print(f"Improved prompt copied, but paste failed: {paste_error}", file=sys.stderr)


def handle_last_result_button(fd):
    send_pet_command(fd, "think")
    summary = summarize_last_result()
    send_pet_command(fd, f"note {summary}")
    print("Last result shown.")


def handle_button(fd, action):
    if action == "last-result":
        handle_last_result_button(fd)
    else:
        handle_improve_button(fd)


def start_http_server(http_port, pet_target, button_action):
    class ButtonHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = urlparse(self.path).path
            if path not in ("/", "/button"):
                self.send_response(404)
                self.end_headers()
                return
            if path == "/button":
                threading.Thread(target=handle_button, args=(pet_target, button_action), daemon=True).start()
                body = b"button accepted\n"
            else:
                body = b"codex pet button daemon\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format, *args):
            return

    server = ThreadingHTTPServer(("0.0.0.0", http_port), ButtonHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"HTTP button listener on http://0.0.0.0:{http_port}/button")
    return server


def main():
    parser = argparse.ArgumentParser(description="Listen for ESP32 button events and improve selected prompts.")
    parser.add_argument("--port", default=DEFAULT_PORT)
    parser.add_argument("--no-serial", action="store_true", help="Do not open the USB serial port.")
    parser.add_argument("--http-port", type=int, default=DEFAULT_HTTP_PORT)
    parser.add_argument(
        "--button-action",
        choices=("improve", "last-result"),
        default="improve",
        help="Action to run when BOOT is pressed.",
    )
    parser.add_argument(
        "--pet-host",
        default=DEFAULT_PET_HOST,
        help="ESP32 HTTP host/IP for status messages. Can also be set with CODEX_PET_HOST.",
    )
    args = parser.parse_args()

    pet_target = args.pet_host or None
    remember_pet_host(args.pet_host)
    start_http_server(args.http_port, pet_target, args.button_action)

    if args.no_serial:
        print("Serial listener disabled. Press Ctrl-C to stop.")
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            return

    configure_port(args.port)
    print(f"Listening on {args.port}. Select text, then press BOOT.")

    fd = os.open(args.port, os.O_RDWR | os.O_NOCTTY)
    try:
        buffer = b""
        while True:
            chunk = os.read(fd, 128)
            if not chunk:
                time.sleep(0.05)
                continue
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                text = line.decode("utf-8", errors="replace").strip()
                if text == "button:prompt_improve":
                    handle_button(fd, args.button_action)
    finally:
        os.close(fd)


if __name__ == "__main__":
    raise SystemExit(main())
