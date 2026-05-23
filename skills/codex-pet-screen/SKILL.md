---
name: codex-pet-screen
description: Quickly activate the Codex Pet Screen ESP32/OLED in the current Codex workspace with project-local hooks, preferring USB serial when present and avoiding broad repo/network discovery.
metadata:
  short-description: Activate Codex Pet Screen
---

# Codex Pet Screen Setup

Use this skill when the user asks to activate, enable, or set up the OLED pet for the current Codex project.

## Fast Path

Do not search for the firmware repo, scan subnets, inspect ARP, or run `git status` unless the fast path fails.

1. Use the installed runtime only:

   ```sh
   R=/Users/nataliechan/.codex/codex-pet-screen-hooks
   test -x "$R/setup_codex_pet.py" && test -x "$R/codex_pet.py"
   ```

2. Choose transport with one cheap check:

   ```sh
   P=$(find /dev -maxdepth 1 \( -name 'cu.usbmodem*' -o -name 'cu.wchusbserial*' \) -print | head -1)
   ```

   If `P` is nonempty, use USB serial. Do not test Wi-Fi first.

3. Install project-local hooks.

   USB serial:

   ```sh
   "$R/setup_codex_pet.py" --scope project --target "$PWD" --serial
   "$R/codex_pet.py" --port "$P" think
   ```

   Wi-Fi fallback, only when no USB serial device exists:

   ```sh
   H=$(cat /tmp/codex_pet_host 2>/dev/null || printf 'http://192.168.0.197')
   "$R/setup_codex_pet.py" --scope project --target "$PWD" --host "$H"
   "$R/codex_pet.py" --host "$H" think
   ```

4. Report concise status:

   - hook file written at `.codex/hooks.json`
   - transport used: USB serial path or Wi-Fi host
   - live verification passed or failed
   - run `/hooks` if Codex asks to trust project hooks

## Guardrails

- Prefer project scope; use global hooks only if the user explicitly asks.
- Preserve unrelated hook events; `setup_codex_pet.py` replaces only `UserPromptSubmit` and `Stop`.
- If `.codex/hooks.json` already has pet hooks, rerun the installer instead of adding duplicates.
- If USB verification fails with `Port busy`, wait briefly and retry once.
- If Wi-Fi verification fails, do not scan the network. Tell the user setup is installed but the pet is unreachable.
- Button daemon setup is separate. Only start it if the user asks for BOOT button support.
