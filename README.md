# Codex Pet Screen

A tiny ESP32-C3 + SSD1306 OLED desk pet for Codex.

The pet lives on a 128x64 OLED, reacts to Codex hooks, shows session/context usage bars, dances when a prompt finishes, plays a cute laptop sound, and uses the ESP32-C3 BOOT button as a prompt-improver trigger for selected text.

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

## Prompt Button

Run the laptop daemon:

```sh
./tools/prompt_button_daemon.py
```

Then select rough prompt text anywhere and press BOOT. The daemon copies the selection, asks `codex exec` to improve it, puts the improved prompt on the clipboard, and pastes it into the active field.

macOS may require Accessibility permission for the terminal app running the daemon.

## Useful Commands

```sh
./tools/codex_pet.py think
./tools/codex_pet.py dance
./tools/codex_pet.py usage 30 12
./tools/codex_pet.py idle
```
