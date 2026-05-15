#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path


def main() -> int:
    sys.stdin.read()
    script = Path(__file__).with_name("codex_pet.py")
    subprocess.run(
        [str(script), "think"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
