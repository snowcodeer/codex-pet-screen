#!/usr/bin/env python3
import json
import math
import wave
import subprocess
import sys
import os
from pathlib import Path

LOG_PATH = Path("/tmp/codex_pet_hook.log")
USAGE_PATH = Path("/tmp/codex_pet_usage.json")
CUTE_SOUND = Path("/tmp/codex_pet_cute.wav")
FALLBACK_DONE_SOUND = Path("/System/Library/Sounds/Purr.aiff")


def log(message: str):
    try:
        with LOG_PATH.open("a", encoding="utf-8") as log_file:
            log_file.write(message + "\n")
    except OSError:
        pass


def is_enabled() -> bool:
    return os.environ.get("CODEX_PET_HOOK", "0") == "1"


def latest_usage_snapshot(transcript_path: Path):
    latest_rate_limits = None
    latest_info = None
    try:
        with transcript_path.open("r", encoding="utf-8") as transcript:
            for line in transcript:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = event.get("payload") or {}
                if payload.get("type") == "token_count":
                    if payload.get("rate_limits"):
                        latest_rate_limits = payload.get("rate_limits")
                    if payload.get("info"):
                        latest_info = payload.get("info")
    except OSError:
        return None
    if latest_rate_limits is None and latest_info is None:
        return None
    return {"rate_limits": latest_rate_limits, "info": latest_info}


def token_total(usage):
    if not isinstance(usage, dict):
        return None
    if isinstance(usage.get("total_tokens"), int):
        return usage["total_tokens"]

    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    if isinstance(input_tokens, int) and isinstance(output_tokens, int):
        return input_tokens + output_tokens
    return None


def usage_from_event(event, previous=None):
    if not event:
        return None

    previous = previous or {}
    session_percent = previous.get("session")
    rate_limits = event.get("rate_limits") or {}
    primary_limit = rate_limits.get("primary") or {}
    if isinstance(primary_limit.get("used_percent"), (int, float)):
        session_percent = round(primary_limit["used_percent"])

    context_percent = previous.get("context")
    info = event.get("info") or {}
    context_window = info.get("model_context_window")
    current_tokens = token_total(info.get("last_token_usage"))

    if current_tokens is None:
        cumulative_tokens = token_total(info.get("total_token_usage"))
        if (
            isinstance(cumulative_tokens, int)
            and isinstance(context_window, int)
            and 0 <= cumulative_tokens <= context_window
        ):
            current_tokens = cumulative_tokens

    if isinstance(current_tokens, int) and isinstance(context_window, int) and context_window > 0:
        context_percent = round(current_tokens * 100 / context_window)

    if session_percent is None or context_percent is None:
        return None

    return max(0, min(100, session_percent)), max(0, min(100, context_percent))


def previous_usage():
    try:
        usage = json.loads(USAGE_PATH.read_text(encoding="utf-8"))
        return {"session": int(usage["session"]), "context": int(usage["context"])}
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return {}


def send_pet(*parts):
    script = Path(__file__).with_name("codex_pet.py")
    subprocess.run(
        [str(script), *map(str, parts)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def generate_cute_sound():
    sample_rate = 44100
    notes = [
        (880.0, 0.09, 0.32),
        (1174.66, 0.10, 0.30),
        (1567.98, 0.14, 0.26),
        (1318.51, 0.11, 0.18),
    ]

    samples = []
    for frequency, duration, volume in notes:
        count = int(sample_rate * duration)
        for index in range(count):
            t = index / sample_rate
            envelope = math.sin(math.pi * index / count) ** 0.8
            vibrato = 1.0 + 0.018 * math.sin(2 * math.pi * 7 * t)
            sample = math.sin(2 * math.pi * frequency * vibrato * t)
            samples.append(int(32767 * volume * envelope * sample))
        samples.extend([0] * int(sample_rate * 0.015))

    with wave.open(str(CUTE_SOUND), "wb") as sound:
        sound.setnchannels(1)
        sound.setsampwidth(2)
        sound.setframerate(sample_rate)
        sound.writeframes(b"".join(sample.to_bytes(2, "little", signed=True) for sample in samples))


def play_done_sound():
    if not CUTE_SOUND.exists():
        try:
            generate_cute_sound()
        except OSError as exc:
            log(f"Could not generate cute sound: {exc}")

    if CUTE_SOUND.exists():
        try:
            subprocess.Popen(
                ["afplay", str(CUTE_SOUND)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            log(f"Playing sound {CUTE_SOUND}")
            return
        except OSError as exc:
            log(f"Could not play cute sound: {exc}")

    if not FALLBACK_DONE_SOUND.exists():
        log(f"Fallback sound missing: {FALLBACK_DONE_SOUND}")
        return
    try:
        subprocess.Popen(
            ["afplay", str(FALLBACK_DONE_SOUND)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        log(f"Playing fallback sound {FALLBACK_DONE_SOUND.name}")
    except OSError as exc:
        log(f"Could not play fallback sound: {exc}")


def main() -> int:
    if not is_enabled():
        try:
            with LOG_PATH.open("a", encoding="utf-8") as log_file:
                log_file.write("Stop hook invoked but disabled by CODEX_PET_HOOK env\n")
        except OSError:
            pass
        return 0

    log("Stop hook invoked")
    try:
        hook_input = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        hook_input = {}

    transcript = hook_input.get("transcript_path")
    if transcript:
        usage = usage_from_event(latest_usage_snapshot(Path(transcript)), previous_usage())
        if usage:
            log(f"Sending usage {usage[0]} {usage[1]}")
            try:
                USAGE_PATH.write_text(
                    json.dumps({"session": usage[0], "context": usage[1]}),
                    encoding="utf-8",
                )
            except OSError:
                pass
            send_pet("usage", usage[0], usage[1])

    log("Sending dance")
    send_pet("dance")
    play_done_sound()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
