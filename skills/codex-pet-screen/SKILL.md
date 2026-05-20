---
name: codex-pet-screen
description: Set up the Codex Pet Screen ESP32/OLED project in another Codex workspace, including project or global hooks, Wi-Fi host caching, button daemon commands, and verification.
metadata:
  short-description: Configure Codex Pet Screen hooks
---

# Codex Pet Screen Setup

Use this skill when the user wants a project to drive a Codex Pet Screen: thinking animation on prompt submit, dance/sound/usage update on stop, and optional BOOT button actions.

## Workflow

1. Locate the `codex-pet-screen` repository. Prefer the user's provided path. Common local path:

   ```sh
   /Users/nataliechan/Documents/PlatformIO/Projects/codex-pet-screen
   ```

2. Confirm the ESP is reachable. Prefer Wi-Fi if configured:

   ```sh
   <pet-root>/tools/codex_pet.py --host http://codex-pet-screen.local think
   ```

   If mDNS fails, use the device IP:

   ```sh
   <pet-root>/tools/codex_pet.py --host http://192.168.0.197 think
   ```

3. Install hooks into the target project. This updates `UserPromptSubmit` and `Stop` while preserving unrelated hook events:

   ```sh
   <pet-root>/tools/setup_codex_pet.py --scope project --target <target-project> --host http://<esp-ip-or-mdns>
   ```

   Use `--scope global` only when the user wants every Codex project to use the pet:

   ```sh
   <pet-root>/tools/setup_codex_pet.py --scope global --host http://<esp-ip-or-mdns>
   ```

4. Start the button daemon if the user wants BOOT button support:

   ```sh
   cd <pet-root>
   ./tools/prompt_button_daemon.py --no-serial --http-port 8765 --pet-host http://<esp-ip-or-mdns> --button-action last-result
   ```

   Use `--button-action improve` for selected-text prompt improvement.

   Current firmware sends explicit button actions: short press shows `last-result`; long press, about 1 second, runs `improve`. The daemon's `--button-action` is only the fallback for older firmware or manual `/button` requests.

5. Ask the user to open Codex in the target project and run `/hooks` if Codex asks for trust.

6. Verify:

   ```sh
   <pet-root>/tools/codex_pet.py think
   <pet-root>/tools/codex_pet.py dance
   ```

   Then send a Codex prompt in the target project. The OLED should enter thinking mode and dance/update when the response finishes.

## Notes

- `setup_codex_pet.py` writes `.codex/hooks.json` for project scope or `~/.codex/hooks.json` for global scope.
- The ESP host is cached in `/tmp/codex_pet_host` so hooks work even when Codex was not launched with `CODEX_PET_HOST`.
- Hook logs are in `/tmp/codex_pet_hook.log`.
- The last-result button summary cache is `/tmp/codex_pet_last_summary.json`.
