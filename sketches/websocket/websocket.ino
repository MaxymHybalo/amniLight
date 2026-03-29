#include <WiFi.h>
#include <ESPAsyncWebServer.h>
#include <FastLED.h>

#define LED_PIN 13
#define NUM_LEDS 180

CRGB leds[NUM_LEDS];

const char* ssid = "Farosh";
const char* password = "8912345678";

AsyncWebServer server(80);
AsyncWebSocket ws("/ws");

// Обробка повідомлень
void handleWebSocketMessage(void *arg, uint8_t *data, size_t len) {
  AwsFrameInfo *info = (AwsFrameInfo*)arg;
  if (info->opcode == WS_BINARY) {

    uint8_t type = data[0];

    // FRAME
    if (type == 0x01) {
      uint16_t length = data[1] | (data[2] << 8);

      if (length == NUM_LEDS * 3) {
        for (int i = 0; i < NUM_LEDS; i++) {
          leds[i].r = data[3 + i*3];
          leds[i].g = data[3 + i*3 + 1];
          leds[i].b = data[3 + i*3 + 2];
        }

        FastLED.show();
      }
    }

    // BRIGHTNESS
    else if (type == 0x02) {
      uint8_t brightness = data[1];
      FastLED.setBrightness(brightness);
      FastLED.show();
    }
  }

}

void onEvent(AsyncWebSocket *server, AsyncWebSocketClient *client,
             AwsEventType type, void *arg, uint8_t *data, size_t len) {

  if (type == WS_EVT_DATA) {
    handleWebSocketMessage(arg, data, len);
  }
}

void setup() {
  Serial.begin(115200);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }

  Serial.println(WiFi.localIP());

  FastLED.addLeds<WS2812, LED_PIN, GRB>(leds, NUM_LEDS);

  ws.onEvent(onEvent);
  server.addHandler(&ws);

  server.begin();
}

void loop() {
  ws.cleanupClients();
}