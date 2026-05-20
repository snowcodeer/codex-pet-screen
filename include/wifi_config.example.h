#pragma once

// Copy this file to include/wifi_config.h and fill in your local values.
// include/wifi_config.h is ignored by git so Wi-Fi credentials are not committed.

#define CODEX_PET_WIFI_SSID "your-wifi-name"
#define CODEX_PET_WIFI_PASSWORD "your-wifi-password"

// Optional: laptop daemon callback for BOOT button prompt-improver events.
// Run: ./tools/prompt_button_daemon.py --no-serial --http-port 8765
#define CODEX_PET_BUTTON_URL "http://192.168.0.245:8765/button"

// Optional mDNS name: http://codex-pet-screen.local/
#define CODEX_PET_MDNS_NAME "codex-pet-screen"
