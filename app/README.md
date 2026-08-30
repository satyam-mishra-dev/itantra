# iTantra Android app (P2 — real on-device speech)

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

- `stt/model.onnx` + `stt/tokens.txt` — IndicConformer int8, NeMo-CTC ONNX export (sherpa-onnx `OfflineNemoEncDecCtcModelConfig`)
- `tts/model.onnx` + `tts/tokens.txt` [+ `tts/espeak-ng-data/`] — Piper/VITS voice (e.g. `vits-piper-hi_IN-pratham-medium`, same files as `p0/models/`)

**Graceful degradation:** missing STT pack → typed-text stub still transmits;
missing TTS pack → platform `TextToSpeech` speaks. The app never hard-crashes
without models.

## What's real (P2)

- VarnaCode v1 + frame protocol, wire-compatible with p0 (tested)
- NSD discovery + TCP transport, foreground service (microphone type)
- 16 kHz PCM capture while PTT held → **sherpa-onnx OfflineRecognizer** on release
- **sherpa-onnx OfflineTts** (VITS/Piper) playback via AudioTrack
- ALERT: max volume (MUSIC+ALARM streams), `AUDIOFOCUS_GAIN_TRANSIENT_EXCLUSIVE`, 2× repeat
- Latency stamps in transcript: `stt <ms> (RTF x.xx)` on send, `tts-first-audio <ms>` on receive — Evaluation Mode's seed

## P3 next

10-language pack manager UI (download/sideload status per language), Silero VAD
sentence chunking during long PTT holds, streaming partials while held,
in-app Evaluation Mode screen (CER vs reference, idle CPU, footprints),
Bluetooth RFCOMM second transport.
