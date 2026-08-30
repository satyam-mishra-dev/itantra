// iTantra LoRa bridge: phone <-BT SPP-> ESP32 <-LoRa IN865-> ESP32 <-BT SPP-> phone
// Relays iTantra frames verbatim. CRC-checked both directions. 1% duty-cycle guard.
#include <Arduino.h>
#include <BluetoothSerial.h>
#include <RadioLib.h>
#include "itantra_frame.h"

// ---- IN865 compliance (DoT/WPC license-exempt band, GSR 564(E)) ----
// Channels: 865.0625 / 865.4025 / 865.985 MHz, 125 kHz BW, max 30 dBm ERP,
// 1% duty cycle per hour. 868 MHz EU plan is NOT license-free in India.
#define LORA_FREQ_MHZ     865.0625
#define LORA_BW_KHZ       125.0
#define LORA_SF           9        // knob: SF7 = 4x more frames/hr, less range
#define LORA_CR           5        // 4/5 — best airtime/robustness trade at SF9
#define LORA_TX_DBM       17       // well under 30 dBm ERP cap
#define LORA_PREAMBLE     8
#define DUTY_BUDGET_MS    36000UL  // 1% of one hour
#define DUTY_WINDOW_MS    3600000UL

// ---- Pin map: common Indian-market "ESP32 LoRa OLED" boards (TTGO LoRa32
// V1 / Heltec WiFi LoRa 32 share this SX127x wiring). Generic DevKit + module:
// wire the same. ----
#define PIN_SCK   5
#define PIN_MISO  19
#define PIN_MOSI  27
#define PIN_NSS   18
#define PIN_RST   14
#define PIN_DIO0  26
#define PIN_LED   2   // TTGO onboard LED is 25; DevKit is 2 — calibration knob

BluetoothSerial bt;
SX1276 radio = new Module(PIN_NSS, PIN_DIO0, PIN_RST, RADIOLIB_NC);

static uint8_t btBuf[ITANTRA_MAX_FRAME * 2];
static size_t btLen = 0;
static uint32_t btLastByteMs = 0;

static uint32_t dutyWindowStart = 0;
static uint32_t dutyUsedMs = 0;

volatile bool rxFlag = false;
static void onRx() { rxFlag = true; }

static void blink() { digitalWrite(PIN_LED, HIGH); delay(5); digitalWrite(PIN_LED, LOW); }

static bool dutyAllows(size_t frameLen) {
  uint32_t now = millis();
  if (now - dutyWindowStart >= DUTY_WINDOW_MS) { dutyWindowStart = now; dutyUsedMs = 0; }
  uint32_t airMs = (uint32_t)(radio.getTimeOnAir(frameLen) / 1000);
  if (dutyUsedMs + airMs > DUTY_BUDGET_MS) return false;
  dutyUsedMs += airMs;
  return true;
}

static void txLora(const uint8_t *frame, size_t len) {
  if (!dutyAllows(len)) {
    // warn the phone with a payload-less ACK frame, seq 0xDC ("duty cycle")
    uint8_t warn[6];
    bt.write(warn, itantra_frame_mini(warn, ITANTRA_PRIO_ACK, 0xDC));
    Serial.println("duty-cycle budget exhausted, frame dropped");
    return;
  }
  int st = radio.transmit((uint8_t *)frame, len);  // blocking; frames are ~45 B
  if (st == RADIOLIB_ERR_NONE) blink();
  else Serial.printf("LoRa TX error %d\n", st);
  radio.startReceive();
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_LED, OUTPUT);
  bt.begin("iTantra-Bridge");  // pair this name from the phone

  SPI.begin(PIN_SCK, PIN_MISO, PIN_MOSI, PIN_NSS);
  int st = radio.begin(LORA_FREQ_MHZ, LORA_BW_KHZ, LORA_SF, LORA_CR,
                       RADIOLIB_SX127X_SYNC_WORD, LORA_TX_DBM, LORA_PREAMBLE);
  if (st != RADIOLIB_ERR_NONE) {
    Serial.printf("SX127x init failed: %d\n", st);
    while (true) { blink(); delay(200); }  // hard fault: flash forever
  }
  radio.setCRC(true);
  radio.setDio0Action(onRx, RISING);
  radio.startReceive();
  dutyWindowStart = millis();
  Serial.println("iTantra-Bridge up: BT SPP <-> LoRa IN865");
}

void loop() {
  // ---- BT -> LoRa ----
  while (bt.available() && btLen < sizeof(btBuf)) {
    btBuf[btLen++] = (uint8_t)bt.read();
    btLastByteMs = millis();
  }
  for (;;) {
    int r = itantra_frame_check(btBuf, btLen);
    if (r > 0) {
      txLora(btBuf, (size_t)r);
      memmove(btBuf, btBuf + r, btLen - r);
      btLen -= r;
    } else if (r < 0) {
      memmove(btBuf, btBuf + 1, --btLen);  // resync: drop one byte
    } else break;
  }
  // ponytail: stuck partial frame (garbage plen) times out after 2 s — drop a
  // byte and rescan; a smarter resync isn't worth it for 45 B frames.
  if (btLen > 0 && millis() - btLastByteMs > 2000) {
    memmove(btBuf, btBuf + 1, --btLen);
  }

  // ---- LoRa -> BT ----
  if (rxFlag) {
    rxFlag = false;
    uint8_t pkt[ITANTRA_MAX_FRAME];
    size_t n = radio.getPacketLength();
    if (n > 0 && n <= sizeof(pkt) &&
        radio.readData(pkt, n) == RADIOLIB_ERR_NONE &&
        itantra_frame_check(pkt, n) == (int)n) {
      bt.write(pkt, n);
      blink();
    }
    radio.startReceive();
  }
}
