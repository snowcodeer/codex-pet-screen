# Codex Pet Screen

A tiny ESP32-C3 + SSD1306 OLED desk pet for Codex.

The pet lives on a 128x64 OLED, reacts to Codex hooks, shows session/context usage bars, dances when a prompt finishes, plays a cute laptop sound, and uses the ESP32-C3 BOOT button as a prompt helper.

## Quick Start

```sh
git clone https://github.com/snowcodeer/codex-pet-screen.git
cd codex-pet-screen
pio run -e codex-pet-screen -t upload
./tools/prompt_button_daemon.py
```

Keep `prompt_button_daemon.py` running while you use the BOOT button. By default, selecting rough prompt text and pressing BOOT improves it and pastes it back. You can also run the button in `last-result` mode to show a short summary of the latest Codex response on the OLED.

To make the pet react to Codex prompt start/finish events, restart Codex after setting up hooks.

```sh
codex
```

## Wi-Fi Mode

Wi-Fi mode lets the OLED screen work without USB serial after flashing. The ESP32 hosts a tiny HTTP API, and the laptop daemon hosts a tiny HTTP callback for BOOT button events.

Copy the example config and fill in your local network details:

```sh
cp include/wifi_config.example.h include/wifi_config.h
```

Edit `include/wifi_config.h`:

```c
#define CODEX_PET_WIFI_SSID "your-wifi-name"
#define CODEX_PET_WIFI_PASSWORD "your-wifi-password"
#define CODEX_PET_BUTTON_URL "http://YOUR_LAPTOP_LAN_IP:8765/button"
#define CODEX_PET_MDNS_NAME "codex-pet-screen"
```

`include/wifi_config.h` is ignored by git so credentials are not committed.

Flash after creating the Wi-Fi config:

```sh
pio run -e codex-pet-screen -t upload
```

Run the laptop daemon in Wi-Fi mode with one of the button actions:

```sh
# Option 1: improve selected text and paste it back.
./tools/prompt_button_daemon.py --no-serial --http-port 8765 --pet-host http://codex-pet-screen.local --button-action improve

# Option 2: show the last Codex result on the OLED.
./tools/prompt_button_daemon.py --no-serial --http-port 8765 --pet-host http://codex-pet-screen.local --button-action last-result
```

If mDNS does not resolve, use the OLED-displayed IP address instead:

```sh
./tools/prompt_button_daemon.py --no-serial --http-port 8765 --pet-host http://192.168.0.123 --button-action last-result
```

Send commands over Wi-Fi:

```sh
CODEX_PET_HOST=http://codex-pet-screen.local ./tools/codex_pet.py dance
CODEX_PET_HOST=http://codex-pet-screen.local ./tools/codex_pet.py usage 30 12
CODEX_PET_HOST=http://codex-pet-screen.local ./tools/codex_pet.py note "LAST RESULT\nBuild passed\nPushed to main"
```

If you launch Codex from a shell and want to force a specific ESP host:

```sh
CODEX_PET_HOST=http://codex-pet-screen.local codex
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
- `Stop`: updates usage bars, remembers the last Codex result, dances, and plays `/tmp/codex_pet_cute.wav`.

After cloning, restart Codex in this repo and run `/hooks` if Codex asks you to trust the hooks.

### Hook Control

Hooks are enabled by default. Set `CODEX_PET_HOOK=0` only when you want to temporarily disable the pet hooks for a Codex launch.

- Example (test the prompt hook):

```bash
python3 tools/codex_pet_prompt_hook.py
```

- Example (test the stop hook with JSON input):

```bash
echo '{}' | python3 tools/codex_pet_stop_hook.py
```

- Logs for hook activity are written to `/tmp/codex_pet_hook.log`.
- The button daemon writes the active Wi-Fi host to `/tmp/codex_pet_host`, so hooks can keep sending commands over Wi-Fi even when Codex was not launched with `CODEX_PET_HOST`.

Notes:
- On macOS, processes may be blocked from reading files in `~/Documents` or other protected locations by system privacy controls. If you see "Operation not permitted" when Codex invokes hooks, either grant Full Disk Access to the app that launches Codex (System Settings → Privacy & Security → Full Disk Access) or run Codex from a location that isn't protected (for example `/Users/Shared`).
- If you prefer per-instance hooks, configure a different hook path for each Codex installation instead of sharing this repository's hooks.

### Use From Another Project

You can configure any Codex project to use this same pet without copying the firmware project.

Project-only setup:

```sh
/Users/nataliechan/Documents/PlatformIO/Projects/codex-pet-screen/tools/setup_codex_pet.py \
  --scope project \
  --target /path/to/other/project \
  --host http://192.168.0.197
```

Global setup for every Codex project:

```sh
/Users/nataliechan/Documents/PlatformIO/Projects/codex-pet-screen/tools/setup_codex_pet.py \
  --scope global \
  --host http://192.168.0.197
```

The setup command writes hook config that points back to this repo's hook scripts. It also caches the ESP host in `/tmp/codex_pet_host`, so Codex can reach the screen even when launched from VS Code or another app without `CODEX_PET_HOST`.

After setup, open Codex in the target project and run `/hooks` if Codex asks you to trust the hooks.

To install the bundled setup skill for future Codex sessions:

```sh
mkdir -p ~/.codex/skills
cp -R /Users/nataliechan/Documents/PlatformIO/Projects/codex-pet-screen/skills/codex-pet-screen ~/.codex/skills/
```

Then ask Codex in another project: `Use the codex-pet-screen skill to set up this repo with my OLED pet.`

## Button Actions

The BOOT button is activated by running the laptop daemon. The firmware sends two press types:

- Short press: shows the latest Codex result summary.
- Long press, about 1 second: improves selected text and pastes it back.

The daemon also supports a fallback action for older firmware or manual `/button` requests:

- `improve`: copies selected text, asks `codex exec` to rewrite it as a stronger prompt, puts the result on the clipboard, clears the active terminal input with `Ctrl-A` + `Ctrl-K`, and pastes the improved prompt.
- `last-result`: summarizes the latest remembered Codex response and sends one concise full-screen note to the OLED for about 5 seconds.

The default fallback action is `improve`, but current firmware sends explicit short/long press actions.

### Prompt Improver

USB serial mode:

```sh
./tools/prompt_button_daemon.py --button-action improve
```

If your ESP32-C3 uses a different serial port:

```sh
./tools/prompt_button_daemon.py --port /dev/cu.usbmodem101 --button-action improve
```

Wi-Fi mode:

```sh
./tools/prompt_button_daemon.py --no-serial --http-port 8765 --pet-host http://codex-pet-screen.local --button-action improve
```

Then select rough prompt text anywhere and press BOOT. The daemon only improves selected text; if nothing is selected, it asks you to select text instead of using unrelated clipboard contents. The active terminal input line is cleared before pasting, which works better in terminal-style prompt fields that do not replace selected text on paste. If paste is blocked, the improved prompt remains on the clipboard.

With current firmware, this action is triggered by a long BOOT press even when the daemon fallback action is `last-result`.

### Last Result Summary

USB serial mode:

```sh
./tools/prompt_button_daemon.py --button-action last-result
```

Wi-Fi mode:

```sh
./tools/prompt_button_daemon.py --no-serial --http-port 8765 --pet-host http://codex-pet-screen.local --button-action last-result
```

Then press BOOT. The daemon reads the last response saved by the Codex `Stop` hook, compresses it to one 5-line OLED page, and sends it as a full-width note. The note hides the session/context bars while it is displayed.

With current firmware, this action is triggered by a short BOOT press.

Generated summaries are cached in `/tmp/codex_pet_last_summary.json`, so pressing BOOT repeatedly for the same Codex result reuses the existing summary instead of calling Codex again.

This mode works best when Codex was launched with hooks enabled:

```sh
CODEX_PET_HOST=http://codex-pet-screen.local codex
```

If there is no remembered Codex result yet, the daemon falls back to the latest git commit.

To keep it running in the background:

```sh
nohup ./tools/prompt_button_daemon.py --button-action last-result > /tmp/codex_pet_button.log 2>&1 &
```

To stop the background daemon:

```sh
pkill -f prompt_button_daemon.py
```

The daemon must stay running because the ESP32 sends button events to the laptop over USB serial or Wi-Fi HTTP. The ESP32 does not run Codex actions by itself.

macOS may require Accessibility permission for the terminal app running the daemon.

### macOS Permissions

Open System Settings and allow the terminal app running the daemon:

- Privacy & Security -> Accessibility: required for simulated `Cmd-C` and `Cmd-V`.
- Privacy & Security -> Full Disk Access: useful if Codex or the daemon is blocked from reading files under protected folders such as `Documents`.

Restart the daemon after changing permissions.

### Prompt Improver Test

1. Run `./tools/prompt_button_daemon.py --button-action last-result`.
2. Select this text in any editable field: `fix this`.
3. Long-press the ESP32-C3 BOOT button for about 1 second.
4. The OLED should enter thinking mode.
5. The selected text should be replaced with a clearer prompt.

### Last Result Test

1. Run `./tools/prompt_button_daemon.py --button-action last-result`.
2. Short-press the ESP32-C3 BOOT button.
3. The OLED should show a concise one-page summary of the latest Codex result for about 5 seconds.

## Useful Commands

```sh
./tools/codex_pet.py think
./tools/codex_pet.py dance
./tools/codex_pet.py usage 30 12
./tools/codex_pet.py note "LAST RESULT\nBuild passed\nPushed to main"
./tools/codex_pet.py idle
```
