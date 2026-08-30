# iTantra LoRa Bridge (P5)

ESP32 + SX127x node that extends the walkie-talkie loop to km range:

```
phone A ⇆ Bluetooth SPP ⇆ ESP32 ⇆ LoRa IN865 ⇆ ESP32 ⇆ Bluetooth SPP ⇆ phone B
```

Frames pass through verbatim (same `ver|lang|prio|seq|len|CRC-16` format as
`p0/frame.py` and the Android app) — the bridge only validates CRC and
enforces the IN865 duty cycle.

## Hardware (₹ prices, Indian market)

| Item | Price | Note |
|---|---|---|
| ESP32 + SX1278 LoRa + 0.96" OLED board (433/865 MHz variants — buy **865–867 MHz**) | ₹1,650–1,990 | Compo India / Robu.in / Robocraze / Zbotic |
| or: ESP32 DevKit (₹380) + Ra-01H SX1276 868/915 module (₹350) | ~₹730 | needs hand wiring per pin map below |
| Antenna (865 MHz, SMA, usually bundled) | ₹0–150 | never TX without antenna |
| **Per node** | **~₹730–1,990** | two nodes for the full demo |

## Wiring / pin map

TTGO LoRa32 V1 and Heltec WiFi LoRa 32 already wire SX127x this way
(nothing to do). For a bare DevKit + module, follow `src/main.cpp`:

| SX127x | ESP32 |
|---|---|
| SCK | 5 |
| MISO | 19 |
| MOSI | 27 |
| NSS | 18 |
| RST | 14 |
| DIO0 | 26 |

LED: GPIO 2 (DevKit) — TTGO onboard LED is GPIO 25, change `PIN_LED`.

## Flash

```bash
pip install platformio
pio run -t upload        # from this directory
pio device monitor       # 115200 baud
```

## Pair with the Android app

1. Android Settings → Bluetooth → pair with **iTantra-Bridge** (SPP, no PIN).
2. In iTantra choose the Bluetooth transport; the app connects to bonded
   devices and streams frames — the bridge relays them over LoRa.

## Radio parameters & Indian law (IN865)

865.0625 MHz · 125 kHz BW · SF9 · CR 4/5 · CRC on · 17 dBm TX.
The 865–867 MHz band is license-exempt in India (DoT GSR 564(E)): max
30 dBm ERP, **1% duty cycle** — the firmware tracks airtime and refuses to
exceed 36 s TX per hour, sending a payload-less ACK frame (`seq=0xDC`) back
to the phone when the budget is exhausted. 868 MHz EU-plan hardware is NOT
legal in India — buy the 865–867 variant.

## Airtime / capacity math (45-byte frame)

LoRa airtime, SF9 / 125 kHz / CR 4/5 / explicit header / CRC:
symbol time 4.096 ms, preamble 12.25 symbols ≈ 50 ms, payload
8 + ceil((8·45 − 4·9 + 44) / 36)·5 = 63 symbols ≈ 258 ms → **~308 ms per
sentence frame**.

1% duty budget = 36 s/hour → **~116 sentences/hour ≈ 2 per minute
sustained** — fine for disaster traffic on one channel. Need more?
`LORA_SF 7` cuts airtime to ~92 ms (**~390 sentences/hour**) at reduced
range; the three IN865 channels can also be split across node pairs.

Range expectation: 1–3 km urban, 3–10 km rural line-of-sight at SF9
(Meshtastic-class hardware, same band/settings).

## Tests without hardware

```bash
python3 test_frame_compat.py   # compiles src/itantra_frame.h on the host and
                               # asserts accept/reject parity with p0/frame.py
pio run                        # firmware compiles for esp32dev
```
