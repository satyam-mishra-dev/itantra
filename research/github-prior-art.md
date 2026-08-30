# iTantra (SIH26173) — GitHub Prior Art & Android Implementation Landscape

PS SIH26173: "iTantra — Indian Multilingual TTS & STT Aided Neural Transceiver Radio Access for low bitrate links." Organization: **ISRO**. Category: Miscellaneous. No official long description found publicly — title only, in the SIH 2026 problem-statement set. Read literally, ISRO's framing ("Radio Access for low bitrate links") points at an actual RF/low-bitrate-link transceiver; the team's working interpretation — offline Android walkie-talkie over Wi-Fi/Bluetooth as the prototype substrate — is a reasonable demo-able substitute for a 36–48h hackathon, but worth flagging explicitly in the pitch as "phone radios standing in for the low-bitrate link" rather than claiming literal RF hardware integration.

Research date: 2026-08-31. Star/license/last-push numbers pulled live from the GitHub API on this date.

---

## 1. Offline STT on Android

| Repo | Stars | License | Last push | Notes |
|---|---|---|---|---|
| [k2-fsa/sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) | 14,495 | Apache-2.0 | 2026-08-30 (active) | The single strongest asset for this PS. STT+TTS+VAD+diarization, ONNX Runtime, Android/iOS/embedded. Ships prebuilt `.aar`/JNI bindings, Kotlin sample apps, and pretrained streaming Zipformer/Paraformer/Whisper models incl. **Indian-language multilingual models** (Hindi and others come from ICEFALL/community exports). Actively maintained, near-daily commits. |
| [alphacep/vosk-api](https://github.com/alphacep/vosk-api) | 15,086 | Apache-2.0 | 2026-08-09 | Older, very mature. Kaldi-based, ~50MB models, 20+ languages incl. Hindi. `vosk-android-demo` (1,056 stars, alphacep) is the reference Android integration — JNI wrapper, streaming recognizer, straightforward to embed. Weaker language coverage/accuracy for regional Indian languages than sherpa-onnx's newer Zipformer models; worth benchmarking both before committing. |
| [vilassn/whisper_android](https://github.com/vilassn/whisper_android) | 688 | MIT | 2026-03-18 (active) | Whisper via TFLite specifically for Android — closest fit if the team wants "TFLite" checked as a compliance box literally. Demonstrates the TFLite delegate + Recorder pattern end to end. |
| [futo-org/voice-input](https://github.com/futo-org/voice-input) | 318 | Source-first (not OSI, flag for compliance) | 2025-09-16 | Polished, shipping product (Whisper + newer Parakeet-TDT ONNX backend), but FUTO's license is "Source First," not a standard open-source license — **do not rely on this for "open-source only" compliance** without checking the PS's exact license bar. Good UX reference regardless (model download flow, on-device diarization-free streaming). |
| [soupslurpr/Transcribro](https://github.com/soupslurpr/Transcribro) | 741 | ISC | 2025-08-29 | Clean whisper.cpp + Silero VAD Kotlin/Compose keyboard-service architecture. English-only today but the VAD+whisper.cpp pairing pattern (chunk on silence, feed to whisper.cpp) is directly reusable for push-to-talk segmentation. |
| [mikeesto/whispercpp-android](https://github.com/mikeesto/whispercpp-android) | 21 | MIT | 2024-07 (stale) | Minimal whisper.cpp JNI reference, good for learning the NDK/CMake wiring, not for production reuse (unmaintained). |
| [ishizuki-tech/WhispersCpp-Android] | — | — | — | Similar minimal whisper.cpp+Compose reference app; same use as above (learning wiring, not adopting wholesale). |

**What this proves:** offline multilingual STT on-device Android is a solved, well-trodden problem with mature open-source libraries. There is no reason to hand-roll model inference — sherpa-onnx or Vosk cover it.

**What to reuse:** sherpa-onnx's Android `.aar` + JNI bindings directly, or Vosk's `vosk-android-demo` as the integration skeleton. Both ship streaming recognizer APIs (partial + final results) which map cleanly onto push-to-talk (start on PTT-down, feed audio chunks, flush+finalize on PTT-up).

---

## 2. Offline TTS on Android

| Repo | Stars | License | Last push | Notes |
|---|---|---|---|---|
| [k2-fsa/sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) (TTS module) | shared repo, 14,495 | Apache-2.0 | active | Same library does TTS: VITS/Piper/Kokoro voices via ONNX. This is the recommended path — **one dependency covers both STT and TTS**, one JNI surface, one model-management pattern, minimizes APK/integration surface area. |
| [woheller69/ttsengine](https://github.com/woheller69/ttsengine) ("SherpaTTS") | 769 | GPL-3.0 | 2026-07-20 (active) | Full Android TTS *system service* (implements Android's `TextToSpeech` engine interface) wrapping sherpa-onnx, with in-app model downloader for Piper/Coqui voices. Best reference for "how do I expose sherpa-onnx TTS as a proper Android TTS engine / or just call it directly from app code." GPL-3.0 — copyleft, fine to study/adapt patterns from but don't vendor its code into a differently-licensed app without honoring GPL. |
| [CodeBySonu95/VoxSherpa-TTS](https://github.com/CodeBySonu95/VoxSherpa-TTS) | 215 | GPL-3.0 | 2026-08-23 (active) | Newer, explicitly multilingual (Hindi + 50 languages), Kokoro/Piper/VITS backends. Good UX/voice-selection reference. |
| [espeak-ng/espeak-ng](https://github.com/espeak-ng/espeak-ng) (android/ dir) | 6,791 | GPL-3.0 | 2026-08-19 (active) | Formant-synthesis fallback — robotic-sounding but tiny footprint (no neural model download), broad language coverage including many Indic languages via phoneme rules. Good as a low-resource fallback voice or for languages sherpa-onnx doesn't yet have a trained voice for. |
| [Olga-Yakovleva/RHVoice](https://github.com/Olga-Yakovleva/RHVoice) | 6 (this fork; upstream mirrors vary) | LGPL-2.1 | 2025-05-13 | Statistical-parametric TTS, decent quality, but language set is Russian/English/Portuguese/etc — **no Indian language coverage**, not directly useful for this PS beyond architectural reference. |

**What this proves:** neural offline TTS integration into Android is a solved pattern (system-TTS-engine wrapper around sherpa-onnx). The team should NOT build a custom TTS engine.

**What to reuse:** sherpa-onnx TTS module (same dependency as STT). Study woheller69/ttsengine's model-download-and-manage-screen pattern if end users need to pick/download voice packs for 10 languages (large combined model set — plan storage budget, likely need per-language on-demand download rather than bundling all 10 in the APK).

---

## 3. Walkie-talkie / P2P transport layer

| Repo | Stars | License | Last push | Notes |
|---|---|---|---|---|
| [berty/berty](https://github.com/berty/berty) | 9,283 | mixed (NOASSERTION at repo root; check per-subpackage) | 2026-08-17 (active) | Most sophisticated prior art: offline-first P2P messaging over BLE + mDNS + libp2p, works with zero internet/servers. Heavyweight (Go + React Native + libp2p stack) — too large to vendor wholesale into a hackathon timeline, but its BLE+mDNS dual-discovery pattern (and docs on why pure BLE mesh doesn't scale past a few peers) is the best design reference for "how do real offline P2P apps discover peers." |
| [permissionlesstech/bitchat-android](https://github.com/permissionlesstech/bitchat-android) | 7,587 | GPL-3.0 | 2026-08-30 (very active) | Modern (2026), Kotlin, BLE mesh chat, dual-transport (mesh + optional Nostr relay online). Directly relevant scale and stack (pure Kotlin, no Go/RN). Good source for BLE GATT service/characteristic design for a small ad-hoc mesh, message-store-and-forward pattern, and battery/duty-cycle handling for BLE scanning. Worth cloning and reading `BluetoothMeshService`-equivalent classes directly. |
| [meshtastic/Meshtastic-Android](https://github.com/meshtastic/Meshtastic-Android) | 1,818 | GPL-3.0 | 2026-08-30 (very active) | Companion app pattern for LoRa mesh radios over BLE. Relevant less for the transport (needs external LoRa hardware) and more for its Kotlin Multiplatform BLE architecture (`meshtastic-sdk`, Kable library) and PhoneAPI handshake/ACK/retry design — good reference if the team later adds LoRa hardware as the literal "low bitrate link" ISRO's title implies. |
| [bridgefy/sdk-android](https://github.com/bridgefy/sdk-android) | 30 | proprietary SDK (NOASSERTION, closed binary) | 2026-04-15 | **Flag: closed-source commercial SDK**, disqualifies for an "open-source only" constraint even though it's free-tier accessible. Do not depend on it; only useful as a UX/API-shape reference (their `BridgefyClient` discovery/connect/send API is a clean model to imitate with a from-scratch implementation). |
| [briar/briar](https://github.com/briar/briar) | 688 | proprietary-ish core / GPL variants across submodules, check per-package | 2026-07-13 | Same idea as Berty (BT/Wi-Fi sync when internet is down, Tor when it's up) but Java, older, heavier (full onion-routing stack). Reference only for the "sync over multiple transports with automatic fallback" abstraction — likely overkill for a 2-phone hackathon demo. |
| [devapro/LANwalkieTalkie](https://github.com/devapro/LANwalkieTalkie) | 43 | MIT | 2025-06-15 (recently touched) | **Closest direct fit.** Simple serverless PTT-over-local-WiFi Android app, MIT licensed, small codebase. This is a realistic starting skeleton for the audio-transport half of iTantra: UDP/socket audio streaming over the same WiFi network, PTT button wiring, no server. Worth forking/reading in full rather than just citing. |
| [murtaza98/Walkie-Talkie](https://github.com/murtaza98/Walkie-Talkie) | 104 | MIT | 2020 (stale) | WiFi-Direct-based two-phone PTT app. Good reference for WiFi Direct's actual pairing flow/pain points (see §5) even though stale — the WiFi Direct API itself hasn't changed much since. |
| [fajf/P2P-WalkieTalkie](https://github.com/fajf/P2P-WalkieTalkie) | 6 | GPL-3.0 | 2019 (stale) | Same category, less polished, low stars — skip unless stuck on murtaza98/devapro. |
| [gms298/Android-Walkie-Talkie](https://github.com/gms298/Android-Walkie-Talkie) | 72 | none declared | 2017 (stale) | Bluetooth RFCOMM-based PTT, old but shows the RFCOMM audio-streaming approach (see §5) works and has prior art. |
| [warren-bank/Android-PTT-Bluetooth-Speaker](https://github.com/warren-bank/Android-PTT-Bluetooth-Speaker) | 28 | GPL-2.0 | 2023-01 | Clean minimal sender/receiver pair over Bluetooth SPP/RFCOMM streaming raw mic audio to `AudioTrack` on the other end — smallest, most readable reference for the raw-audio-over-socket mechanics regardless of transport chosen. |

**What this proves:** nobody has built a polished, actively-maintained, small-footprint "two Android phones, offline, PTT, WiFi-or-BT, open source" app that's also production quality. The closest (LANwalkieTalkie, murtaza98) are small hobby projects, several years stale. This is real whitespace — iTantra's differentiator isn't the transport (that's a solved, if unglamorous, problem) but marrying it with the STT→text→TTS multilingual translation relay, which nobody in this list does.

---

## 4. Prior SIH attempts on this exact PS

No public GitHub repos, YouTube demos, or team writeups found for PS SIH26173 / "iTantra" specifically. This problem statement is new for **SIH 2026** (not 2025 — initial assumption in the task brief was wrong; ISRO's iTantra PS number SIH26173 confirms it's a 2026 addition, sourced from `NoBugNinja/Smart-India-Hackathon-SIH-2026-Problem-Statements`). No prior team's weaknesses to learn from — the team is first-movers on public prior art for this exact title. Do not spend more search budget hunting for a prior iTantra team; there isn't one publicly.

The nearest *conceptual* prior art (not on this PS, but same problem shape) is **RTranslator** (§7) — an app already doing offline STT→translate→TTS between two phones in "conversation mode," which is functionally 80% of what iTantra needs minus the multilingual-Indian-language model set and the walkie-talkie-style PTT UX.

---

## 5. Android transport & audio specifics

- **Foreground service for PTT:** mandatory on Android 8+ (background mic/audio access is killed otherwise). Use a `Service` with `startForeground()` + a persistent notification the moment PTT is armed/listening; Android 14 also requires declaring the foreground service type (`microphone`, `connectedDevice` if using BT/WiFi transport) in the manifest. All the walkie-talkie repos above skip or under-handle this for modern Android — expect to write this fresh, it's the single most common reason old sample apps (2017-2020 vintage, several in §3) crash or get killed on modern OS versions.
- **Audio focus:** request `AUDIOFOCUS_GAIN_TRANSIENT_EXCLUSIVE` during PTT transmit/receive so it behaves like a real radio (ducks/pauses music, doesn't get stomped by other apps). None of the older sample repos model this correctly — build it fresh using `AudioManager.requestAudioFocus` (or `AudioFocusRequest` builder on API 26+).
- **AudioRecord/AudioTrack + Oboe:** [google/oboe](https://github.com/google/oboe) (4,099 stars, Apache-2.0, active) is Google's official low-latency C++ audio library (AAudio on API 27+, OpenSL ES fallback). Recommended if the pipeline needs tight latency budgets end-to-end (mic → STT chunking → network → TTS → speaker). If using Kotlin/JNI to ONNX/TFLite anyway, Oboe integration is a natural sibling native dependency rather than staying on plain `AudioRecord`/`AudioTrack` Java APIs, which have materially higher and less predictable latency.
- **Wi-Fi Direct (P2P):** works without an existing network but has a well-documented rough pairing UX (system dialog handoff, `WifiP2pManager` connection can silently fail/timeout on some OEM skins, group-owner negotiation flakiness). murtaza98/Walkie-Talkie (§3) demonstrates it works but the API surface is notoriously OEM-inconsistent — treat as higher-risk for a hackathon demo unless the demo devices are pre-tested.
- **Plain hotspot + socket (what LANwalkieTalkie does):** simplest, most reliable for a hackathon demo — one phone starts a local hotspot (or both join existing WiFi/router), the other joins, then plain TCP/UDP sockets. **Recommended default for the hackathon prototype** given time constraints; trades off "works without any pre-existing network" (Wi-Fi Direct's actual advantage) for reliability.
- **Wi-Fi Aware:** newer, cleaner API (no group-owner negotiation dance) but requires Android 8+ AND specific hardware support (`FEATURE_WIFI_AWARE`) which is not universal on budget Indian-market phones — real risk of unsupported demo devices. Flag as a stretch-goal upgrade path, not the initial build target.
- **Bluetooth RFCOMM/SPP:** proven (gms298, warren-bank repos above) for raw PCM/audio streaming over BT sockets; works everywhere BT works, no WiFi network dependency, good fallback/second transport option. Lower bandwidth than WiFi but the PS title itself says "low bitrate links," so BT's constraints are arguably more on-theme than WiFi's.
- **Nearby Connections API — FLAG:** Google's `com.google.android.gms.nearby.connection` is fully offline in operation (device-to-device via WiFi/BT once connected) but ships as part of **Google Play Services**, a closed-source proprietary component. If "open-source only" is a hard PS/rulebook constraint, this almost certainly disqualifies Nearby Connections even though the *runtime data path* never touches the internet — the *dependency* itself is proprietary. **Recommend the team explicitly ask the mentor/rulebook whether "open-source" restricts app code only or also forbids proprietary system libraries; default to NOT using it and building on NSD/sockets or raw WiFi Direct/BT instead**, since that's unambiguously safe.
- **NSD (Network Service Discovery) / mDNS:** `NsdManager`, part of the Android platform (not Play Services) — safe, open, standard. Good pairing partner for the plain-socket approach: advertise a service (`_itantra._tcp`) on one phone, discover+resolve on the other, then open a socket. `drulabs/LocalDash` and `aroio/android-nsd-flow` are small reference wrappers if a Kotlin-Flow-based NSD API is wanted over the raw callback API.

---

## 6. Kotlin vs Flutter vs React Native

No head-to-head repo or benchmark specifically covering "TFLite/ONNX JNI + low-latency audio" was found, but the consistent finding across every relevant demo app surveyed above (all of §1, §2, and the most-active §3 repos) is that **every one of them is native Kotlin/Java** — not a single actively-maintained sherpa-onnx/whisper.cpp/Vosk/walkie-talkie Android demo uses Flutter or React Native as the primary app layer. The few Flutter/RN wrappers that exist (`react-native-sherpa-onnx-offline-tts`, `XDcobra/react-native-sherpa-onnx`) are thin bridges over the same native library, not full-app frameworks, and exist specifically because cross-platform teams still need the native binding underneath.

Technical reasoning matches the ecosystem's behavior: Flutter's platform channels add JNI/serialization/thread-hop overhead on every native call, which is fine for occasional calls but a bad fit for (a) continuous low-latency audio streaming and (b) frequent JNI round-trips into an ONNX/TFLite inference loop — exactly this app's hot path. **Recommendation: Kotlin, native.** Don't spend build time evaluating Flutter/RN for this PS — the ecosystem has already answered this question by simply not building it that way.

---

## 7. STT → text-link → TTS as a comms system (closest existing match)

**[niedev/RTranslator](https://github.com/niedev/RTranslator)** — 10,367 stars, Apache-2.0, actively maintained (pushed 2026-08-26). This is the single closest prior-art match to iTantra's actual pipeline, found via "speech to text walkie talkie ... translation" search:

- **Fully offline**, on-device: Whisper-Small-244M (with KV-cache optimization for speed) for STT, on-device translation models (v3.0 moved from NLLB to Bergamot/Madlad/HY-MT options), system or on-device TTS for output.
- **Conversation Mode** (2 phones): Phone A mic → STT → text sent to Phone B → Phone B translates + TTS-plays in the other language, bidirectionally. This is structurally almost identical to what iTantra needs, minus (a) Indian-language model coverage and (b) push-to-talk radio-style UX (RTranslator is closer to a live two-way call than a PTT walkie-talkie).
- **WalkieTalkie Mode** (single phone, both parties speak into one device): listens for either of two configured languages, auto-detects which was spoken, translates, and plays back — a genuinely relevant UX pattern to study even though it's single-device, not two-device.
- License (Apache-2.0) and active maintenance make it safe and worthwhile to study its source directly (particularly the KV-cache Whisper optimization and its Bluetooth-headset audio routing) rather than only reading the README.

No other repo found combines STT+text-relay+TTS as a comms system; this is the strongest single reference for the overall pipeline architecture.

---

## Build strategy

**Reuse, don't rebuild:**
- STT + TTS: **sherpa-onnx** (k2-fsa) for both, one dependency, one JNI surface, actively maintained, proven multilingual model zoo. Fall back to Vosk only if a specific Indian language's sherpa-onnx model is missing/weak, and to eSpeak-NG as a last-resort tiny-footprint TTS voice for languages with no trained neural voice yet.
- Low-latency audio: **Oboe** (google/oboe) instead of raw AudioRecord/AudioTrack — matches naturally with the JNI-to-ONNX pipeline the team is already building.
- Transport skeleton: fork the pattern from **devapro/LANwalkieTalkie** (plain socket over existing WiFi/hotspot) as the primary path; use **NSD** (`NsdManager`, platform-native, not Play Services) for peer discovery instead of hardcoding IPs. Keep Bluetooth RFCOMM (pattern from warren-bank/Android-PTT-Bluetooth-Speaker) as a second transport for the "works with zero WiFi infra" case, since the PS explicitly says "low bitrate links" and BT fits that framing better than WiFi anyway.
- Pipeline shape: **RTranslator's Conversation Mode** is the architecture to imitate — mic → STT (on-device) → text over the socket/BT link (this is the actual "low bitrate" payload: text, not audio, which also directly answers ISRO's "low bitrate" framing) → TTS on the receiving phone. Sending recognized *text* rather than raw/compressed audio between phones is both the natural low-bitrate answer and reuses the STT step the app already has to do — don't build a separate audio codec/streaming path unless a stretch goal wants a live "raw voice passthrough" mode too.

**Don't reuse (build fresh, deliberately):**
- Foreground service + audio focus handling — every old sample app in §3/§5 is stale on this exact point; Android's requirements changed under them. Budget real time for this, it's the most common demo-day crash source.
- Wi-Fi Direct as primary transport — real but OEM-flaky; keep as a stretch/upgrade path, not the hackathon-day critical path.

**Flag explicitly in the pitch/mentor conversation:**
- Nearby Connections API is offline-in-operation but ships via proprietary Google Play Services — verify with mentors whether "open-source only" excludes it before even considering it; default answer here is no, don't use it.
- FUTO Voice Input's "Source First" license is not standard open-source — don't cite it as compliant prior art if the rulebook checks licenses.
- No public prior team has attempted PS SIH26173 specifically — there's no direct competitor blueprint to react to or improve on; RTranslator is the nearest analog to study instead.
