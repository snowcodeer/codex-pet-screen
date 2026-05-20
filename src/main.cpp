#include <Arduino.h>
#include <U8g2lib.h>
#include <Wire.h>

#if __has_include("wifi_config.h")
#include "wifi_config.h"
#include <ESPmDNS.h>
#include <HTTPClient.h>
#include <WebServer.h>
#include <WiFi.h>
#define CODEX_PET_WIFI_ENABLED 1
#else
#define CODEX_PET_WIFI_ENABLED 0
#endif

namespace {
constexpr uint8_t kSdaPin = 3;
constexpr uint8_t kSclPin = 4;
constexpr uint8_t kButtonPin = 0;
constexpr uint32_t kBaud = 115200;
constexpr uint8_t kNoteMaxLines = 5;
constexpr uint8_t kNoteLinesPerPage = 5;
constexpr uint32_t kNoteHoldMs = 5000;
constexpr uint32_t kLongPressMs = 900;

U8G2_SSD1306_128X64_NONAME_F_HW_I2C oled(U8G2_R0, U8X8_PIN_NONE);

#if CODEX_PET_WIFI_ENABLED
#ifndef CODEX_PET_MDNS_NAME
#define CODEX_PET_MDNS_NAME "codex-pet-screen"
#endif
#ifndef CODEX_PET_BUTTON_URL
#define CODEX_PET_BUTTON_URL ""
#endif
WebServer server(80);
uint32_t lastWifiAttempt = 0;
#endif

String serialLine;
String statusText = "waiting for codex";
uint32_t lastIdleFrame = 0;
uint8_t idleFrame = 0;
bool lastButtonState = HIGH;
uint32_t buttonPressedAt = 0;
int8_t sessionPercent = -1;
int8_t contextPercent = -1;
bool thinkingMode = false;
bool noteMode = false;
uint32_t noteStartedAt = 0;
uint32_t noteUntil = 0;
String noteLines[kNoteMaxLines];
uint8_t noteLineCount = 0;

void drawSparkle(int16_t x, int16_t y) {
  oled.drawPixel(x, y - 2);
  oled.drawPixel(x, y + 2);
  oled.drawPixel(x - 2, y);
  oled.drawPixel(x + 2, y);
  oled.drawPixel(x, y);
}

void drawPet(int16_t x, int16_t y, uint8_t mood, uint8_t pose = 0, bool blink = false) {
  const int8_t earWiggle = pose % 2;
  oled.drawTriangle(x + 8, y + 8, x + 13, y + 1 - earWiggle, x + 18, y + 8);
  oled.drawTriangle(x + 30, y + 8, x + 35, y + 1 + earWiggle, x + 40, y + 8);
  oled.drawRBox(x + 5, y + 7, 38, 28, 8);
  oled.setDrawColor(0);
  oled.drawRBox(x + 7, y + 9, 34, 24, 7);
  oled.setDrawColor(1);

  oled.drawLine(x + 24, y + 6, x + 24, y + 1);
  oled.drawDisc(x + 24, y, 1);

  if (blink) {
    oled.drawHLine(x + 13, y + 18, 7);
    oled.drawHLine(x + 28, y + 18, 7);
  } else if (mood == 2) {
    oled.drawCircle(x + 16, y + 18, 3);
    oled.drawCircle(x + 31, y + 18, 3);
  } else {
    oled.drawDisc(x + 16, y + 18, 3);
    oled.drawDisc(x + 31, y + 18, 3);
    oled.setDrawColor(0);
    oled.drawPixel(x + 17, y + 17);
    oled.drawPixel(x + 32, y + 17);
    oled.setDrawColor(1);
  }

  oled.drawPixel(x + 10, y + 23);
  oled.drawPixel(x + 11, y + 24);
  oled.drawPixel(x + 37, y + 23);
  oled.drawPixel(x + 36, y + 24);

  switch (mood) {
    case 1:
      oled.drawLine(x + 17, y + 26, x + 21, y + 29);
      oled.drawLine(x + 21, y + 29, x + 29, y + 29);
      oled.drawLine(x + 29, y + 29, x + 33, y + 26);
      break;
    case 2:
      oled.drawCircle(x + 24, y + 28, 3);
      break;
    default:
      oled.drawLine(x + 18, y + 27, x + 22, y + 29);
      oled.drawLine(x + 22, y + 29, x + 28, y + 29);
      oled.drawLine(x + 28, y + 29, x + 32, y + 27);
      break;
  }

  oled.drawRBox(x + 9 + (pose % 2), y + 35, 9, 4, 2);
  oled.drawRBox(x + 30 - (pose % 2), y + 35, 9, 4, 2);
}

void drawCaption(const String &text) {
  oled.setFont(u8g2_font_6x10_tf);
  String line = text;
  line.trim();
  if (line.length() > 21) {
    line = line.substring(0, 21);
  }
  oled.drawStr(1, 63, line.c_str());
}

void drawProgressBar(uint8_t x, uint8_t y, uint8_t width, uint8_t percent) {
  percent = percent > 100 ? 100 : percent;
  oled.drawFrame(x, y, width, 5);
  const uint8_t fillWidth = (width - 2) * percent / 100;
  if (fillWidth > 0) {
    oled.drawBox(x + 1, y + 1, fillWidth, 3);
  }
}

void drawUsageBars() {
  oled.setFont(u8g2_font_5x8_tf);
  oled.drawStr(1, 52, "S");
  oled.drawStr(1, 61, "C");

  if (sessionPercent < 0) {
    drawProgressBar(12, 47, 88, 0);
    oled.drawStr(104, 52, "--%");
  } else {
    drawProgressBar(12, 47, 88, sessionPercent);
    oled.setCursor(104, 52);
    oled.print(sessionPercent);
    oled.print("%");
  }

  if (contextPercent < 0) {
    drawProgressBar(12, 56, 88, 0);
    oled.drawStr(104, 61, "--%");
  } else {
    drawProgressBar(12, 56, 88, contextPercent);
    oled.setCursor(104, 61);
    oled.print(contextPercent);
    oled.print("%");
  }
}

void renderIdle() {
  noteMode = false;
  oled.clearBuffer();
  const int16_t bob = idleFrame % 2;
  drawSparkle(28, 15 + (idleFrame % 2));
  drawSparkle(98, 12 + ((idleFrame + 1) % 2));
  drawPet(40, 2 + bob, thinkingMode ? 2 : 0, idleFrame, !thinkingMode && idleFrame == 5);
  oled.setFont(u8g2_font_5x8_tf);
  if (thinkingMode) {
    for (uint8_t dot = 0; dot <= idleFrame % 4; ++dot) {
      oled.drawDisc(55 + dot * 6, 42, 1);
    }
  }
  drawUsageBars();
  oled.sendBuffer();
}

void renderNote() {
  oled.clearBuffer();
  oled.setFont(u8g2_font_6x10_tf);
  uint8_t y = 10;

  for (uint8_t i = 0; i < kNoteLinesPerPage && i < noteLineCount; ++i) {
    oled.drawStr(1, y, noteLines[i].c_str());
    y += 11;
  }
  oled.sendBuffer();
}

void dance() {
  noteMode = false;
  thinkingMode = false;
  static const int8_t xs[] = {36, 45, 40, 32, 47, 40, 36, 44};
  static const int8_t ys[] = {7, 3, 8, 4, 8, 3, 7, 5};

  for (uint8_t i = 0; i < sizeof(xs); ++i) {
    oled.clearBuffer();
    drawSparkle(17, 12 + (i % 3));
    drawSparkle(108, 11 + ((i + 1) % 3));
    oled.drawPixel(26 + i * 2, 4 + (i % 2));
    oled.drawPixel(96 - i * 2, 5 + ((i + 1) % 2));
    drawPet(xs[i], ys[i], 1, i);
    oled.setFont(u8g2_font_6x10_tf);
    oled.drawStr(18, 57, "prompt complete!");
    oled.sendBuffer();
    delay(115);
  }
  statusText = "ready for next prompt";
  renderIdle();
}

void showThinking() {
  noteMode = false;
  thinkingMode = true;
  statusText = "thinking";
  renderIdle();
}

void showMessage(String message) {
  message.trim();
  if (message.length() == 0) {
    message = "hello from laptop";
  }
  thinkingMode = false;
  noteMode = false;
  statusText = message;
  oled.clearBuffer();
  drawPet(4, 6, 1, 0);
  oled.setFont(u8g2_font_6x10_tf);
  uint8_t y = 13;
  while (message.length() > 0 && y <= 57) {
    const uint8_t count = message.length() > 21 ? 21 : message.length();
    String line = message.substring(0, count);
    message.remove(0, line.length());
    oled.drawStr(55, y, line.c_str());
    y += 11;
  }
  oled.sendBuffer();
}

void showNote(String message) {
  message.trim();
  if (message.length() == 0) {
    message = "No recent result";
  }
  thinkingMode = false;
  noteMode = true;
  noteStartedAt = millis();
  noteUntil = noteStartedAt + kNoteHoldMs;
  noteLineCount = 0;
  statusText = message;

  while (message.length() > 0 && noteLineCount < kNoteMaxLines) {
    message.trim();
    int newline = message.indexOf('\n');
    uint8_t count = message.length() > 21 ? 21 : message.length();
    if (newline >= 0 && newline < count) {
      count = newline;
    } else if (count == 21 && message.length() > 21) {
      int lastSpace = message.lastIndexOf(' ', count);
      if (lastSpace > 0) {
        count = lastSpace;
      }
    }

    String line = message.substring(0, count);
    line.trim();
    if (line.length() > 0) {
      noteLines[noteLineCount++] = line;
    }

    if (newline >= 0 && newline <= count) {
      message.remove(0, newline + 1);
    } else {
      message.remove(0, count);
    }
  }

  if (noteLineCount == 0) {
    noteLines[noteLineCount++] = "No recent result";
  }
  renderNote();
}

void handleCommand(String line);

#if CODEX_PET_WIFI_ENABLED
void sendHttpOk(const String &body = "ok") {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "text/plain", body);
}

void handleHttpRoot() {
  String body = "codex-pet-screen\n";
  body += "ip=" + WiFi.localIP().toString() + "\n";
  body += "commands: /cmd?c=think, /cmd?c=dance, /cmd?c=usage%2030%2012\n";
  sendHttpOk(body);
}

void handleHttpCmd() {
  if (!server.hasArg("c")) {
    server.send(400, "text/plain", "missing c");
    return;
  }
  handleCommand(server.arg("c"));
  sendHttpOk();
}

void handleHttpUsage() {
  if (!server.hasArg("s") || !server.hasArg("c")) {
    server.send(400, "text/plain", "missing s or c");
    return;
  }
  handleCommand("usage " + server.arg("s") + " " + server.arg("c"));
  sendHttpOk();
}

void connectWifi() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  WiFi.mode(WIFI_STA);
  WiFi.setHostname(CODEX_PET_MDNS_NAME);
  WiFi.begin(CODEX_PET_WIFI_SSID, CODEX_PET_WIFI_PASSWORD);
  lastWifiAttempt = millis();
}

void setupWifiServer() {
  connectWifi();
  const uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 8000) {
    delay(100);
  }

  if (WiFi.status() == WL_CONNECTED) {
    MDNS.begin(CODEX_PET_MDNS_NAME);
    server.on("/", handleHttpRoot);
    server.on("/cmd", handleHttpCmd);
    server.on("/usage", handleHttpUsage);
    server.begin();
    showMessage("wifi " + WiFi.localIP().toString());
    delay(900);
  }
}

void serviceWifi() {
  if (WiFi.status() == WL_CONNECTED) {
    server.handleClient();
    return;
  }

  if (millis() - lastWifiAttempt > 10000) {
    connectWifi();
  }
}

void notifyButtonCallback(const char *action) {
  const char *url = CODEX_PET_BUTTON_URL;
  if (WiFi.status() != WL_CONNECTED || url[0] == '\0') {
    return;
  }

  String callback = String(url);
  callback += callback.indexOf('?') >= 0 ? "&action=" : "?action=";
  callback += action;

  HTTPClient http;
  http.setTimeout(1200);
  if (http.begin(callback)) {
    http.GET();
    http.end();
  }
}
#else
void setupWifiServer() {}
void serviceWifi() {}
void notifyButtonCallback(const char *) {}
#endif

void handleCommand(String line) {
  line.trim();
  String command = line;
  command.toLowerCase();

  if (command == "dance" || command == "done") {
    dance();
  } else if (command == "think" || command == "thinking") {
    showThinking();
  } else if (command.startsWith("usage ")) {
    const int split = command.indexOf(' ', 6);
    if (split > 0) {
      sessionPercent = constrain(command.substring(6, split).toInt(), 0, 100);
      contextPercent = constrain(command.substring(split + 1).toInt(), 0, 100);
      if (!noteMode) {
        renderIdle();
      }
    }
  } else if (command.startsWith("msg ")) {
    showMessage(line.substring(4));
  } else if (command.startsWith("note ")) {
    showNote(line.substring(5));
  } else if (command == "idle") {
    noteMode = false;
    thinkingMode = false;
    statusText = "waiting for codex";
    renderIdle();
  } else if (line.length() > 0) {
    showMessage(line);
  }
}
}  // namespace

void setup() {
  pinMode(kButtonPin, INPUT_PULLUP);
  Serial.begin(kBaud);

  Wire.begin(kSdaPin, kSclPin);
  Wire.setClock(100000);

  oled.begin();
  oled.setPowerSave(0);
  oled.setContrast(180);
  renderIdle();
  setupWifiServer();
}

void loop() {
  serviceWifi();

  while (Serial.available() > 0) {
    const char c = static_cast<char>(Serial.read());
    if (c == '\n' || c == '\r') {
      handleCommand(serialLine);
      serialLine = "";
    } else if (serialLine.length() < 512) {
      serialLine += c;
    }
  }

  const bool buttonState = digitalRead(kButtonPin);
  if (lastButtonState == HIGH && buttonState == LOW) {
    buttonPressedAt = millis();
  } else if (lastButtonState == LOW && buttonState == HIGH) {
    const uint32_t pressMs = millis() - buttonPressedAt;
    if (pressMs >= kLongPressMs) {
      Serial.println("button:prompt_improve");
      showMessage("improving prompt");
      notifyButtonCallback("improve");
    } else {
      Serial.println("button:last_result");
      showThinking();
      notifyButtonCallback("last-result");
    }
  }
  lastButtonState = buttonState;

  if (noteMode && static_cast<int32_t>(millis() - noteUntil) >= 0) {
    noteMode = false;
    renderIdle();
  }

  if (millis() - lastIdleFrame > 800) {
    lastIdleFrame = millis();
    idleFrame = (idleFrame + 1) % 8;
    if (noteMode) {
      renderNote();
    } else {
      renderIdle();
    }
  }
}
