#include <NeoPixelBus.h>

// Налаштування
#define LED_COUNT 5
#define LED_PIN 6

NeoPixelBus<NeoGrbFeature, Neo800KbpsMethod> strip(LED_COUNT, LED_PIN);

void setup() {
  strip.Begin();

  // Білий колір для всіх світлодіодів
  strip.ClearTo(RgbColor(255, 255, 255));

  strip.Show(); // застосувати
}

void loop() {
  // нічого не робимо
}