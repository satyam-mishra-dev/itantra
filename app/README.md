# iTantra Android app (P1 spine)

Native Kotlin, no third-party runtime deps in P1. Package `com.nullpointers.itantra`.

## Build

```sh
export JAVA_HOME=/opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home
cd app
./gradlew assembleDebug   # APK at build/outputs/apk/debug/
./gradlew test            # JVM protocol tests (mirrors p0/test_p0.py + python interop vectors)
```

`local.properties` must point at the SDK (`sdk.dir=/opt/homebrew/share/android-commandlinetools`).

## Codebooks

`src/main/assets/codebooks.json` and the test resources are **generated** from the
Python reference — re-run after any p0/varnacode change:

```sh
python3 tools/export_codebooks.py
```

The `pythonInteropVectors` test asserts Kotlin `pack()` is byte-identical to
`p0/frame.pack()`, so the two ends stay wire-compatible.

## What's real vs stubbed (P1)

- Real: VarnaCode + frame protocol (wire-compatible with p0), NSD discovery +
  TCP transport, foreground service (microphone type), PTT mic capture,
  ALERT playback at max volume via platform TTS, 10-language selector.
- Stubbed: STT (typed text stands in for the transcript) and neural TTS
  (platform `TextToSpeech` speaks received text).

## P2 — sherpa-onnx

sherpa-onnx is not on Maven Central. Download the Android AAR from
https://github.com/k2-fsa/sherpa-onnx/releases (e.g. `sherpa-onnx-<ver>.aar`)
into `app/libs/sherpa-onnx.aar` — the build picks it up automatically (see
`build.gradle.kts`). Then: streaming IndicConformer int8 for STT on PTT audio,
Piper/AI4Bharat ONNX voices for TTS, model packs under
`getExternalFilesDir()/models/<lang>/` (download-on-demand or ADB sideload).
