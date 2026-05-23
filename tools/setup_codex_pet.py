#!/usr/bin/env python3
import argparse
import json
import shutil
from pathlib import Path


DEFAULT_PET_ROOT = Path(__file__).resolve().parents[1]
HOST_CACHE = Path("/tmp/codex_pet_host")
HOOK_INSTALL_DIR = Path.home() / ".codex" / "codex-pet-screen-hooks"
HOOK_FILES = (
    "codex_pet.py",
    "codex_pet_prompt_hook.py",
    "codex_pet_stop_hook.py",
    "setup_codex_pet.py",
)


def install_hook_runtime(pet_root: Path):
    source_dir = pet_root / "tools"
    HOOK_INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    for name in HOOK_FILES:
        source = source_dir / name
        destination = HOOK_INSTALL_DIR / name
        shutil.copy2(source, destination)
        destination.chmod(0o755)
    return HOOK_INSTALL_DIR


def installed_runtime_exists():
    return all((HOOK_INSTALL_DIR / name).exists() for name in HOOK_FILES[:3])


def hook_config(hook_dir: Path):
    return {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": str(hook_dir / "codex_pet_prompt_hook.py"),
                            "timeout": 3,
                            "statusMessage": "Codex pet thinking",
                        }
                    ]
                }
            ],
            "Stop": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": str(hook_dir / "codex_pet_stop_hook.py"),
                            "timeout": 5,
                            "statusMessage": "Dancing Codex pet",
                        }
                    ]
                }
            ],
        }
    }


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def write_hooks(path: Path, hook_dir: Path):
    data = read_json(path)
    hooks = data.setdefault("hooks", {})
    pet_hooks = hook_config(hook_dir)["hooks"]
    hooks["UserPromptSubmit"] = pet_hooks["UserPromptSubmit"]
    hooks["Stop"] = pet_hooks["Stop"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Configure Codex Pet Screen hooks for Codex.")
    parser.add_argument(
        "--scope",
        choices=("project", "global"),
        default="project",
        help="Write hooks to the current project or user-level Codex config.",
    )
    parser.add_argument(
        "--target",
        default=".",
        help="Project directory for --scope project. Default: current directory.",
    )
    parser.add_argument(
        "--pet-root",
        default=str(DEFAULT_PET_ROOT),
        help="Path to the codex-pet-screen repository.",
    )
    parser.add_argument(
        "--host",
        default="",
        help="Optional ESP HTTP host, for example http://192.168.0.197.",
    )
    args = parser.parse_args()

    pet_root = Path(args.pet_root).expanduser().resolve()
    if (pet_root / "tools" / "codex_pet.py").exists():
        hook_dir = install_hook_runtime(pet_root)
    elif installed_runtime_exists():
        hook_dir = HOOK_INSTALL_DIR
    else:
        raise SystemExit(
            f"Could not find codex_pet.py under {pet_root} and no installed runtime exists at {HOOK_INSTALL_DIR}"
        )

    if args.scope == "global":
        hook_path = Path.home() / ".codex" / "hooks.json"
    else:
        hook_path = Path(args.target).expanduser().resolve() / ".codex" / "hooks.json"

    write_hooks(hook_path, hook_dir)

    if args.host:
        HOST_CACHE.write_text(args.host.strip() + "\n", encoding="utf-8")

    print(f"Wrote hooks: {hook_path}")
    print(f"Installed hook runtime: {hook_dir}")
    if args.host:
        print(f"Cached ESP host: {args.host}")
    print("Open Codex in the target project and run /hooks if asked to trust the hooks.")


if __name__ == "__main__":
    main()
