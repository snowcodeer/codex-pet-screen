#!/usr/bin/env python3
import subprocess
import sys
import os
from pathlib import Path


def main() -> int:
    # Opt-in guard to avoid interfering with other Codex instances.
    if os.environ.get("CODEX_PET_HOOK", "0") != "1":
        try:
            with Path("/tmp/codex_pet_hook.log").open("a", encoding="utf-8") as f:
                f.write("Prompt hook invoked but disabled by CODEX_PET_HOOK env\n")
        except OSError:
            pass
        return 0

    sys.stdin.read()
    script = Path(__file__).with_name("codex_pet.py")
    try:
        subprocess.run(
            [str(script), "think"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        try:
            with Path("/tmp/codex_pet_hook.log").open("a", encoding="utf-8") as f:
                f.write("Could not run codex_pet.py from prompt hook\n")
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
