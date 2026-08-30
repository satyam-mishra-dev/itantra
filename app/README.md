# iTantra Android app (P3 — VAD sentence streaming, Evaluation Mode, dual bearers)

Native Kotlin. Package `com.nullpointers.itantra`. AGP 9.3.2 · Gradle 9.7.1 · Java 17 target.

## Build

```sh
export JAVA_HOME=/opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home
cd app
# one-time: fetch the sherpa-onnx AAR (v1.13.6, ~49 MB, gitignored)
curl -sL -o libs/sherpa-onnx.aar \
  https://github.com/k2-fsa/sherpa-onnx/releases/download/v1.13.6/sherpa-onnx-1.13.6.aar
./gradlew assembleDebug   # APK at build/outputs/apk/debug/
./gradlew test            # 7 JVM protocol tests — no AAR native code, no models needed at runtime
```

`local.properties` must point at the SDK (`sdk.dir=/opt/homebrew/share/android-commandlinetools`).

## Codebooks (VarnaCode v1 — corpus-trained, 4.45–5.36 bits/char)

`src/main/assets/codebooks.json` + test resources are **generated** from the
Python reference. Re-run after any p0/varnacode or codebooks.json change:

```sh
python3 tools/export_codebooks.py && ./gradlew test
```

`pythonInteropVectors` asserts Kotlin `pack()` is byte-identical to
`p0/frame.pack()` on 30 vectors — wire compatibility is tested, not assumed.

## Model packs (sideload for now)

```
adb push <lang-pack>/stt/  /sdcard/Android/data/com.nullpointers.itantra/files/models/<lang>/stt/
adb push <lang-pack>/tts/  /sdcard/Android/data/com.nullpointers.itantra/files/models/<lang>/tts/
```

- `stt/model.onnx` + `stt/tokens.txt` — IndicConformer NeMo-CTC ONNX (sherpa-onnx `OfflineNemoEncDecCtcModelConfig`). Sideload the **int8** variant (rename `model.int8.onnx` → `model.onnx` when pushing): 140 MB vs 493 MB fp32, measured CER 1.6% vs 0.8%, RTF 0.059 vs 0.047 — phone-sized at ±1 pt accuracy
- `tts/model.onnx` + `tts/tokens.txt` [+ `tts/espeak-ng-data/`] — Piper/VITS voice (e.g. `vits-piper-hi_IN-pratham-medium`, same files as `p0/models/`)

**Graceful degradation:** missing STT pack → typed-text stub still transmits;
missing TTS pack → platform `TextToSpeech` speaks. The app never hard-crashes
without models.

## What's real (P3)

- VarnaCode v1 + frame protocol, wire-compatible with p0 (30 interop vectors byte-identical)
- **Silero VAD sentence streaming**: a long PTT hold is chunked at pauses; sentence 1
  is recognized and transmitted while sentence 2 is still being spoken (the PS's
  "detect pauses, form sentences, stream instantly"). VAD model ships in assets (630 KB)
- Dual bearers behind one `Transport` interface: NSD/TCP (Wi-Fi) + **Bluetooth RFCOMM**
  (bonded devices, zero Wi-Fi infra); frames go out on both
- 16 kHz PCM capture → **sherpa-onnx OfflineRecognizer**; **OfflineTts** (VITS/Piper) playback
- ALERT: max volume (MUSIC+ALARM), `AUDIOFOCUS_GAIN_TRANSIENT_EXCLUSIVE`, 2× repeat
- **Evaluation Mode screen**: per-language model-pack inventory (✓/✗ + MB), reference-sentence
  read test scoring live CER/WER (CER is the honest Indic metric — arXiv 2203.16601),
  per-utterance RTF, last receive→first-audio ms, 5-s idle-CPU sample (/proc/self/stat)
- Graceful degradation everywhere: no STT pack → typed text; no TTS pack → platform TTS

## IndicConformer STT packs (desktop-verified)

`tools/convert_indicconformer.py <lang> <outdir>` downloads the community
IndicConformer ONNX (trysem/indicconformer-120m-onnx, 12 Indic languages,
~493 MB fp32 each) and fixes it for sherpa-onnx NeMo-CTC: tokens.txt from
vocab.json + `<blk>` appended, and injected metadata
(`vocab_size`, `normalize_type=per_feature`, `subsampling_factor=4`,
`model_type=EncDecCTCModel`) — the raw export lacks all of these and
`subsampling_factor=8` silently truncates transcripts.

Add `--int8` to also emit `model.int8.onnx` — onnxruntime dynamic weight
quantization with the sherpa-onnx metadata re-injected (the quantizer strips
it). Measured on the p0 Piper wavs (desktop, sherpa-onnx 1.13.6, the exact
`OfflineNemoEncDecCtcModelConfig` path the app uses):

| Hindi model | Size | Load | RTF | CER vs ref |
|---|---|---|---|---|
| fp32 | 493 MB | 0.7 s | 0.047 | 0.8% |
| int8 | **140 MB** | 0.5 s | 0.059 | 1.6% |

int8 vs fp32 transcripts differ by 0.8% CER (anusvara/candrabindu variants —
e.g. जाएँ→जाए). Recipe generalizes: Bengali converts+quantizes to the same
140 MB and loads clean. The official AI4Bharat int8 ONNX remains a HF-gated
alternative; ours removes that dependency.

## P5 next

In-app pack downloads, store-and-forward queue on disconnect, AES-GCM frame
envelope, ESP32 LoRa bridge firmware.
