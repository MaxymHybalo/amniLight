#include <NeoPixelBus.h>

// Налаштування
#define LED_COUNT 180
#define LED_PIN 13

NeoPixelBus<NeoGrbFeature, Neo800KbpsMethod> strip(LED_COUNT, LED_PIN);

float baseHue = 0; // базовий відтінок

void setup() {
  strip.Begin();
  strip.Show();
}

void loop() {
  for (int i = 0; i < LED_COUNT; i++) {
    // плавний градієнт по стрічці
    float hue = baseHue + (float)i / LED_COUNT;

    // зациклення від 0 до 1
    if (hue > 1.0f) hue -= 1.0f;

    RgbColor color = HslColor(hue, 1.0f, 0.5f);
    strip.SetPixelColor(i, color);
  }

  strip.Show();

  baseHue += 0.005f; // швидкість анімації
  if (baseHue > 1.0f) baseHue -= 1.0f;

  delay(10);
}