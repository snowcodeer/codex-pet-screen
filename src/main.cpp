#include <Arduino.h>
#include <U8g2lib.h>
#include <Wire.h>

namespace {
constexpr uint8_t kSdaPin = 3;
constexpr uint8_t kSclPin = 4;
constexpr uint8_t kButtonPin = 0;
constexpr uint32_t kBaud = 115200;

U8G2_SSD1306_128X64_NONAME_F_HW_I2C oled(U8G2_R0, U8X8_PIN_NONE);

String serialLine;
String statusText = "waiting for codex";
uint32_t lastIdleFrame = 0;
uint8_t idleFrame = 0;
bool lastButtonState = HIGH;
int8_t sessionPercent = -1;
int8_t contextPercent = -1;
bool thinkingMode = false;

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

void dance() {
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
      renderIdle();
    }
  } else if (command.startsWith("msg ")) {
    showMessage(line.substring(4));
  } else if (command == "idle") {
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
}

void loop() {
  while (Serial.available() > 0) {
    const char c = static_cast<char>(Serial.read());
    if (c == '\n' || c == '\r') {
      handleCommand(serialLine);
      serialLine = "";
    } else if (serialLine.length() < 96) {
      serialLine += c;
    }
  }

  const bool buttonState = digitalRead(kButtonPin);
  if (lastButtonState == HIGH && buttonState == LOW) {
    Serial.println("button:prompt_improve");
    showThinking();
  }
  lastButtonState = buttonState;

  if (millis() - lastIdleFrame > 800) {
    lastIdleFrame = millis();
    idleFrame = (idleFrame + 1) % 8;
    renderIdle();
  }
}
