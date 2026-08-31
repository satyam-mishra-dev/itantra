# iTantra — the offline multilingual semantic transceiver

**SIH 2026 · PS SIH26173 (ISRO) · Team Null Pointers**

Voice that travels as text. Push-to-talk speech is transcribed **on-device** in any of 10 Indian languages, compressed by **VarnaCode** to ~45 bytes per sentence, sent over whatever link survives — Wi-Fi, Bluetooth, a ₹1,650 LoRa node, or 0.3 s of audio through any analog radio — and re-synthesized as natural speech at the far end. Fully offline. Open-source only.

| | Measured (not estimated) |
|---|---|
| One spoken sentence on the wire | **45 B** — 169× less than cellular voice (AMR-NB), 889× less than raw (G.711) |
| VarnaCode, all 10 languages | **4.45–5.41 bits/char** — beats Unishox2 and SCSU head-to-head on identical sentences |
| Real human speech (FLEURS, int8 140 MB packs) | CER hi **2.9%** · bn 4.0% · te 7.8% · ml 9.2% · ta 13.9% · RTF 0.06 |
| Encrypted sentence (AES-128-GCM) | 73 B — still ~100× under cellular voice |
| Tests | 222 Python assertions · 127 firmware parity cases · 12 Android tests |
| APK | 54.9 MB incl. full speech runtime; two-phone loop proven on emulators incl. ALERT |

## Layout

| Path | What |
|---|---|
| `docs/` | Idea document (`SIH2026-iTantra-idea-doc.pdf`, §0–§14), the 6-slide idea deck (`SIH2026-iTantra-idea-PPT.pptx` + `build_ppt.py`), mermaid diagram sources and charts in `assets/` |
| `research/` | Seven research dossiers: STT, TTS, low-bitrate comms, GitHub prior art, India context, text compression, robustness + jury meta, wow-factor search |
| `p0/` | Python reference pipeline — `varnacode.py`, `frame.py` (v1 + AES-GCM v2 + prosody byte), `prosody.py`, `rollcall.py`, `afsk.py`, `cap_bridge.py`, evaluation harnesses (`eval_real.py`, `bench_compression.py`, `quantize_stt.py`), `RESULTS.md` with every measured number |
| `app/` | Native Kotlin Android app — sherpa-onnx STT/TTS/VAD, NSD+TCP and Bluetooth RFCOMM transports, PTT UI, Evaluation Mode, `tools/convert_indicconformer.py` (community ONNX → sherpa-onnx, `--int8`), screenshots |
| `firmware/lora-bridge/` | ESP32 + SX127x PlatformIO firmware — Bluetooth SPP ⇆ LoRa IN865 relay with duty-cycle guard; C frame parser parity-tested against `p0/frame.py` |

## Run it

```bash
# Reference pipeline + all tests
cd p0 && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # or see p0/README.md
.venv/bin/python test_p0.py            # 222 assertions
.venv/bin/python bench_compression.py  # VarnaCode vs UTF-8 / gzip / Unishox2 / SCSU / AMR / Codec2

# Android (needs JDK 17+, Android SDK 34; sherpa-onnx AAR download documented in app/README.md)
cd app && ./gradlew assembleDebug test

# Firmware (no hardware needed to compile)
cd firmware/lora-bridge && pio run && python3 test_frame_compat.py
```

Model packs (int8 STT ~140 MB + Piper TTS ~63 MB per language) are not in git — `app/README.md` has the conversion and sideload commands.

## Honesty notes

- All accuracy numbers are on desktop CPU; on-device RTF on a budget phone is the first thing Evaluation Mode measures on real hardware.
- A GTCRN speech-enhancement stage was measured and **rejected** — it raised CER at every SNR. We ship without a denoiser and say so.
- The arithmetic-coding VarnaCode v2 won by 0.03 bits/char and was **not** adopted; Huffman v1 stays the wire format.
