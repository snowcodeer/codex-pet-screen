---
name: codex-pet-screen
description: Set up the Codex Pet Screen ESP32/OLED project in a chosen Codex workspace, including project-local hooks, Wi-Fi host caching, button daemon commands, and verification.
metadata:
  short-description: Configure Codex Pet Screen hooks
---

# Codex Pet Screen Setup

Use this skill when the user wants a project to drive a Codex Pet Screen: thinking animation on prompt submit, dance/sound/usage update on stop, and optional BOOT button actions.

## Workflow

1. Locate the installed hook runtime. Prefer this unprotected path because Codex sessions launched from Terminal may not be able to read repos under `~/Documents`:

   ```sh
   /Users/nataliechan/.codex/codex-pet-screen-hooks
   ```

   If the installed runtime is missing, locate the `codex-pet-screen` repository. Common local path:

   ```sh
   /Users/nataliechan/Documents/PlatformIO/Projects/codex-pet-screen
   ```

2. Confirm the ESP is reachable. Prefer Wi-Fi if configured:

   ```sh
   /Users/nataliechan/.codex/codex-pet-screen-hooks/codex_pet.py --host http://codex-pet-screen.local think
   ```

   If mDNS fails, use the device IP:

   ```sh
   /Users/nataliechan/.codex/codex-pet-screen-hooks/codex_pet.py --host http://192.168.0.197 think
   ```

3. Install hooks into the target project. Prefer project scope so the pet is opt-in for this workspace. This updates `UserPromptSubmit` and `Stop` while preserving unrelated hook events:

   ```sh
   /Users/nataliechan/.codex/codex-pet-screen-hooks/setup_codex_pet.py --scope project --target <target-project> --host http://<esp-ip-or-mdns>
   ```

   Use `--scope global` only if the user explicitly wants every Codex project to use the pet:

   ```sh
   /Users/nataliechan/.codex/codex-pet-screen-hooks/setup_codex_pet.py --scope global --host http://<esp-ip-or-mdns>
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
   /Users/nataliechan/.codex/codex-pet-screen-hooks/codex_pet.py think
   /Users/nataliechan/.codex/codex-pet-screen-hooks/codex_pet.py dance
   ```

   Then send a Codex prompt in the target project. The OLED should enter thinking mode and dance/update when the response finishes.

## Notes

- Prefer project scope. `setup_codex_pet.py` writes `.codex/hooks.json` for project scope or `~/.codex/hooks.json` for global scope.
- The installed runtime path is `~/.codex/codex-pet-screen-hooks`; use it before falling back to the firmware repo path.
- The ESP host is cached in `/tmp/codex_pet_host` so hooks work even when Codex was not launched with `CODEX_PET_HOST`.
- Hook logs are in `/tmp/codex_pet_hook.log`.
- The last-result button summary cache is `/tmp/codex_pet_last_summary.json`.
