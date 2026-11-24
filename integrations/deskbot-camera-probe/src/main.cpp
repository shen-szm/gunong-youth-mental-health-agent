#include <Arduino.h>
#include <driver/gpio.h>
#include <esp_camera.h>
#include <esp_heap_caps.h>
#include "camera_pins_from_schematic.h"

namespace {

using namespace camera_pins;

struct Edges {
  uint32_t vsync = 0;
  uint32_t href = 0;
  uint32_t pclk = 0;
};

Edges sampleEdges() {
  Edges edges;
  int v = gpio_get_level(static_cast<gpio_num_t>(kVsync));
  int h = gpio_get_level(static_cast<gpio_num_t>(kHref));
  int p = gpio_get_level(static_cast<gpio_num_t>(kPclk));
  const uint32_t started = millis();
  while (millis() - started < 120) {
    const int next_v = gpio_get_level(static_cast<gpio_num_t>(kVsync));
    const int next_h = gpio_get_level(static_cast<gpio_num_t>(kHref));
    const int next_p = gpio_get_level(static_cast<gpio_num_t>(kPclk));
    edges.vsync += next_v != v;
    edges.href += next_h != h;
    edges.pclk += next_p != p;
    v = next_v;
    h = next_h;
    p = next_p;
  }
  return edges;
}

void runProbe() {
  Serial.printf("[PROBE] free_psram=%u largest_internal_dma=%u\n",
                static_cast<unsigned>(heap_caps_get_free_size(MALLOC_CAP_SPIRAM)),
                static_cast<unsigned>(heap_caps_get_largest_free_block(
                    MALLOC_CAP_INTERNAL | MALLOC_CAP_DMA)));

  camera_config_t c{};
  c.pin_pwdn = kPwdn;
  c.pin_reset = kReset;
  c.pin_xclk = kXclk;
  c.pin_sccb_sda = kSda;
  c.pin_sccb_scl = kScl;
  c.pin_pclk = kPclk;
  c.pin_vsync = kVsync;
  c.pin_href = kHref;
  c.pin_d0 = kData[0];
  c.pin_d1 = kData[1];
  c.pin_d2 = kData[2];
  c.pin_d3 = kData[3];
  c.pin_d4 = kData[4];
  c.pin_d5 = kData[5];
  c.pin_d6 = kData[6];
  c.pin_d7 = kData[7];
  c.ledc_timer = LEDC_TIMER_0;
  c.ledc_channel = LEDC_CHANNEL_0;
  c.xclk_freq_hz = 20000000;
  c.pixel_format = PIXFORMAT_JPEG;
  c.frame_size = FRAMESIZE_QVGA;
  c.jpeg_quality = 18;
  c.fb_count = 1;
  c.fb_location = CAMERA_FB_IN_PSRAM;
  c.grab_mode = CAMERA_GRAB_WHEN_EMPTY;

  const esp_err_t err = esp_camera_init(&c);
  Serial.printf("[PROBE] init=0x%x\n", static_cast<unsigned>(err));
  if (err != ESP_OK) return;

  const sensor_t* sensor = esp_camera_sensor_get();
  Serial.printf("[PROBE] sensor_pid=0x%x xclk=%u\n",
                sensor ? static_cast<unsigned>(sensor->id.PID) : 0u,
                sensor ? static_cast<unsigned>(sensor->xclk_freq_hz) : 0u);
  const Edges edges = sampleEdges();
  Serial.printf("[PROBE] edges_vsync=%u href=%u pclk=%u (120ms)\n",
                edges.vsync, edges.href, edges.pclk);

  for (int i = 0; i < 3; ++i) {
    const uint32_t started = millis();
    camera_fb_t* fb = esp_camera_fb_get();
    const bool jpeg = fb && fb->buf && fb->len >= 4 &&
                      fb->buf[0] == 0xff && fb->buf[1] == 0xd8 &&
                      fb->buf[fb->len - 2] == 0xff &&
                      fb->buf[fb->len - 1] == 0xd9;
    Serial.printf("[PROBE] frame=%d jpeg=%d bytes=%u elapsed_ms=%u\n",
                  i + 1, jpeg ? 1 : 0,
                  fb ? static_cast<unsigned>(fb->len) : 0u,
                  static_cast<unsigned>(millis() - started));
    if (fb) esp_camera_fb_return(fb);
    delay(100);
  }
  esp_camera_deinit();
}

}  // namespace

void setup() {
  Serial.begin(115200);
  delay(2000);
  Serial.println("[PROBE] OpenDeskBotV2 camera-only diagnostic; no USB protocol or other peripherals");
  Serial.printf("[PINMAP] source=PCB_V2.0_Base contact=25-n SDA=%d SCL=%d XCLK=%d PCLK=%d VSYNC=%d HREF=%d\n",
                kSda, kScl, kXclk, kPclk, kVsync, kHref);
  Serial.printf("[PINMAP] D0..D7=%d,%d,%d,%d,%d,%d,%d,%d RESET=%d PWDN=%d\n",
                kData[0], kData[1], kData[2], kData[3], kData[4], kData[5], kData[6], kData[7], kReset, kPwdn);
}

void loop() {
  runProbe();
  delay(10000);
}
