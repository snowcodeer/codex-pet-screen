# Codex Pet Screen

A tiny ESP32-C3 + SSD1306 OLED desk pet for Codex.

The pet lives on a 128x64 OLED, reacts to Codex hooks, shows session/context usage bars, dances when a prompt finishes, plays a cute laptop sound, and uses the ESP32-C3 BOOT button as a prompt-improver trigger for selected text.

## Quick Start

```sh
git clone https://github.com/snowcodeer/codex-pet-screen.git
cd codex-pet-screen
pio run -e codex-pet-screen -t upload
./tools/prompt_button_daemon.py
```

Keep `prompt_button_daemon.py` running while you use the BOOT button. Select rough prompt text anywhere, press BOOT, and the improved prompt should be pasted into the active text field.

To make the pet react to Codex prompt start/finish events in this repo, launch Codex with:

```sh
CODEX_PET_HOOK=1 codex
```

## Hardware

- ESP32-C3 SuperMini
- SSD1306 128x64 I2C OLED at `0x3C`
- I2C wiring: `SDA=GPIO3`, `SCL=GPIO4`
- BOOT button: `GPIO0`
- OLED power: `3V3` and `GND`

## Firmware

Build and upload with PlatformIO:

```sh
pio run -e codex-pet-screen -t upload
```

The default upload and monitor port is `/dev/cu.usbmodem101`.

## Codex Hooks

Project-local hooks live in `.codex/hooks.json`.

- `UserPromptSubmit`: sends `think` so the pet enters thinking mode.
- `Stop`: updates usage bars, dances, and plays `/tmp/codex_pet_cute.wav`.

After cloning, restart Codex in this repo and run `/hooks` if Codex asks you to trust the hooks.

### Hook Opt-in (recommended)

To avoid these hooks interfering with other Codex instances, hooks in this project are now opt-in.

- Enable the hooks only for the Codex instance you want to control by setting the environment variable `CODEX_PET_HOOK=1` before launching Codex or when invoking the hook scripts directly.
- Example (test the prompt hook):

```bash
CODEX_PET_HOOK=1 python3 tools/codex_pet_prompt_hook.py
```

- Example (test the stop hook with JSON input):

```bash
echo '{}' | CODEX_PET_HOOK=1 python3 tools/codex_pet_stop_hook.py
```

- Logs for hook activity are written to `/tmp/codex_pet_hook.log`.

Notes:
- On macOS, processes may be blocked from reading files in `~/Documents` or other protected locations by system privacy controls. If you see "Operation not permitted" when Codex invokes hooks, either grant Full Disk Access to the app that launches Codex (System Settings → Privacy & Security → Full Disk Access) or run Codex from a location that isn't protected (for example `/Users/Shared`).
- If you prefer per-instance hooks, configure a different hook path for each Codex installation instead of sharing this repository's hooks.

## Prompt Button

The prompt button is activated by running the laptop daemon:

```sh
./tools/prompt_button_daemon.py
```

If your ESP32-C3 uses a different serial port:

```sh
./tools/prompt_button_daemon.py --port /dev/cu.usbmodem101
```

To keep it running in the background:

```sh
nohup ./tools/prompt_button_daemon.py > /tmp/codex_pet_button.log 2>&1 &
```

To stop the background daemon:

```sh
pkill -f prompt_button_daemon.py
```

Then select rough prompt text anywhere and press BOOT. The daemon copies the selection, asks `codex exec` to improve it, puts the improved prompt on the clipboard, and pastes it into the active field.

The daemon must stay running because the ESP32 sends button events over USB serial to the laptop. The ESP32 does not run the prompt improver by itself.

macOS may require Accessibility permission for the terminal app running the daemon.

### macOS Permissions

Open System Settings and allow the terminal app running the daemon:

- Privacy & Security -> Accessibility: required for simulated `Cmd-C` and `Cmd-V`.
- Privacy & Security -> Full Disk Access: useful if Codex or the daemon is blocked from reading files under protected folders such as `Documents`.

Restart the daemon after changing permissions.

### Prompt Button Test

1. Run `./tools/prompt_button_daemon.py`.
2. Select this text in any editable field: `fix this`.
3. Press the ESP32-C3 BOOT button.
4. The OLED should enter thinking mode.
5. The selected text should be replaced with a clearer prompt.

If nothing is selected, the daemon falls back to the current clipboard text. If paste is blocked, the improved prompt remains on the clipboard.

## Useful Commands

```sh
./tools/codex_pet.py think
./tools/codex_pet.py dance
./tools/codex_pet.py usage 30 12
./tools/codex_pet.py idle
```
