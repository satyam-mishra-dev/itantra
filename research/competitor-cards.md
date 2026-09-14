# iTantra competitor cards — 76 public SIH26173 repos, surveyed 2026-09-15 via GitHub API (no clones)

_Per-repo evidence cards. Synthesis and roadmap in `competitor-survey.md`._

---
## Group 1

# SIH26173 competitor cards — group 1 (19 repos)

Surveyed via GitHub API trees + raw files only (no clones). "Commits" = count from `Link: rel=last` header on `commits?per_page=1`. Date = last commit.

---

## 1. Naitik328/itantra
- **Repo**: Naitik328/itantra · Kotlin · 768 MB (git history; working tree is small) · pushed 2026-09-09 · 1 commit (2026-08-29)
- **What it is**: Honest "week-1 skeleton": Compose UI (onboarding, squads, members, walkie screen), a frozen 8-byte-header wire frame with CRC-16, mic capture, loopback + Wi-Fi Direct transport. README explicitly says STT/TTS/VAD are "next". No speech models anywhere.
- **Pipeline & stack**: STT none · TTS none · translation none · encoding = raw UTF-8 text in `WireFrame` (ver/type nibble, src, dst(0xFF broadcast), lang, seq, len, payload ≤255 B, CRC-16/CCITT-FALSE) · transports: Wi-Fi Direct (WifiP2p DNS-SD service discovery + TCP socket over P2P group), Bluetooth RFCOMM (written, "unwired"), loopback · Android native Kotlin/Compose · offline.
- **Genuinely good features/ideas**:
  - Wi-Fi P2P DNS-SD advertising so only app peers show up, continuous advertise (no BT 5-minute discoverable cap); alert flag in the DNS-SD TXT record with `maybeAutoJoinAlert` (auto-connect to a peer advertising an alert).
  - Full-screen SOS notification channel (`AlertNotifier`) that takes over lockscreen; foreground `RelayService`.
  - "Squads" (group) UI model with pin/unread/search (UI only, no group protocol).
  - Wire frame designed to be mirrored on ESP32 (CRC note), broadcast dst.
- **Measured numbers claimed**: "~100 bytes per sentence" (arithmetic only, no script).
- **Maturity**: **2** — UI + transport plumbing, zero speech pipeline, single commit.
- **Weaknesses**: No STT/TTS at all; no compression (UTF-8 → 3 B/char Indic); no tests; one commit dump.
- **Threat to us**: **Low** — nothing beyond us except a nicer squads/onboarding UI and the alert-auto-join Wi-Fi Direct trick.

---

## 2. Krypto-Kumar/iTantra
- **Repo**: Krypto-Kumar/iTantra · no language · 153 MB (history only) · pushed 2026-08-25 · 1 commit
- **What it is**: README only on `main` (tree = 1 file). README describes a Compose app with sherpa-onnx STT + Piper TTS + RFCOMM and "MODEL_PACKS.md", but none of it is in the repo.
- **Pipeline & stack**: Claimed: sherpa-onnx STT, Piper/VITS TTS, BT RFCOMM, framed UTF-8 envelopes, normal/alert envelopes. Nothing verifiable.
- **Genuinely good features/ideas**: none verifiable.
- **Measured numbers claimed**: none.
- **Maturity**: **1** — empty (README only).
- **Weaknesses**: no code.
- **Threat to us**: **Low**.

---

## 3. HyperHawks/iTantra
- **Repo**: HyperHawks/iTantra · Kotlin · 100 MB · pushed 2026-09-07 · 13 commits
- **What it is**: Polished "tactical" Compose UI whose entire AI/network layer is **simulated**. `IndicSpeechToTextEngine.transcribePcmAudio` returns a canned phrase chosen by `audioSamples.size % phrases.size`; latency is clamped random 145–285 ms; WER 8.1 / CPU 9.4% are hard-coded constants. `MeshRelayManager` sets peer counts/RSSI/PDR to literals per link type. No socket code at all.
- **Pipeline & stack**: STT fake · TTS = Android `TextToSpeech` system engine (+ `ToneGenerator` siren, alarm stream) · no translation · "BinaryPacketSerializer" (own compact struct) · transports: none real (enum of LoRa/BLE/WiFi-Direct/2G/SATCOM labels) · Android native · claims TFLite/FastSpeech2/MelGAN but no model files or runtime deps.
- **Genuinely good features/ideas**:
  - UI patterns: PacketBubble showing RF-savings % and latency delta per message; TacticalTopBar with RSSI/air-gap badge; Diagnostics screen with WER/CPU gauges; SOS beacon screen; channel selector (NDRF/Border/etc.); hands-free VAD toggle vs PTT.
- **Measured numbers claimed**: "<300 ms STT delta gate, avg 195–215 ms", "98.4% RF reduction", "<12% CPU on Snapdragon 450", "WER 8.1%". **All fabricated in code** (constants).
- **Maturity**: **2** — UI demo with mock engines.
- **Weaknesses**: Fake STT, fake mesh, fake metrics presented as "Verified"; badges say SIH 2025. A jury that opens the code will penalise it.
- **Threat to us**: **Low** (Med only on stage polish if nobody reads code). Some UI ideas (per-message savings chip, diagnostics gauges) are worth noting — we already have byte chips.

---

## 4. NihalMishra3009/ITANTRA
- **Repo**: NihalMishra3009/ITANTRA · Kotlin · 55 MB (+LFS) · pushed 2026-09-14 · 57 commits (very active, last "truth pass" docs commit)
- **What it is**: Large, genuinely engineered Android app: Whisper-base-int8 STT via sherpa-onnx, VITS/Piper TTS via sherpa-onnx, per-peer ECDH/AES-GCM/HMAC, Room store-and-forward outbox, DTN-style routing (NODE_HELLO/ROUTE_REQUEST), Bluetooth RFCOMM + Wi-Fi Direct, Opus-MT translation via own JNI (vendored SentencePiece + ORT C API), atomic model-pack installer. 168 unit tests. **Their own CURRENT_STATUS.md says: no two-phone test has ever been performed, no WER/latency measured; earlier fake WER/latency tables were removed.**
- **Pipeline & stack**: STT = OpenAI Whisper base int8 (sherpa-onnx OfflineRecognizer, one model for 10 langs) · TTS = Piper VITS (hi/en/ml), Coqui VITS bn (bundled), Meta MMS-TTS→sherpa VITS for gu/mr/kn/ta/te/or (CC-BY-NC, disclosed) · translation = Helsinki Opus-MT hi↔en ONNX via JNI, EN-pivot design for 10 langs (weights not hosted yet → reports TRANSLATION_UNAVAILABLE) · VAD = adaptive energy (Silero bundled but not enabled) · encoding = `BinaryPacketCodec` v4: magic+ver+type+lang+flags+seq16 + **UTF-8 message-id string + 8 B timestamp + sender/recipient id strings + 32 B HMAC-SHA256** + UTF-8/encrypted payload (no compression) · transports: BT RFCOMM, Wi-Fi Direct (group-owner IP TCP), CompositeTransport AUTO · Android native (XML views) · fully offline.
- **Genuinely good features/ideas** (in code + unit-tested):
  - Persistent Room outbox with ACK, exponential backoff, TTL, dedup, emergency queue preemption (store-and-forward).
  - Multi-hop relay with routing table + next-hop selection, per-hop re-encryption (A→R1→B), replay protection per peer, `DeliveryTracker` state machine (QUEUED→STORED→FORWARDING→DELIVERED→ACKED).
  - Per-peer ECDH P-256 + HKDF session keys, Android Keystore, unauthenticated SESSION_START bootstrap; no global key.
  - SOS packet type that needs no STT/models; receiver forces alarm-stream max volume then restores.
  - `LocationManager` with source tagging (GNSS/WIFI_RTT/BLE_RSSI/RELAY_ANCHOR), coarse + expiry-limited advertised position.
  - Atomic model-pack install: staging dir → SHA-256 → validate → smoke test → publish with backup/rollback; license shown per pack in Models UI.
  - Sender-side translation with explicit source≠target languages; relays need no models; honest failure (no mislabeled text).
  - Live NetworkActivity (node id, neighbours, routing table); BenchmarkLogger with monotonic clock + P50/P95 CSV export.
- **Measured numbers claimed**: Only host-side: Opus-MT hi-en decode ~184 ms, en-hi ~410 ms; ONNX-vs-HF parity 12/12. WER/latency/RTF pages state "NOT VERIFIED". `evaluate_wer.py` exists but needs WAVs.
- **Maturity**: **3** (strong 3) — builds, 168 tests, one device loaded models; never run phone-to-phone; translation weights missing.
- **Weaknesses**: Whisper base is poor on Indic (their competitor Niranjan measured ~100% WER on Tamil with the same model); packet header overhead ≈ 100+ B (UUID msg-id + ids + 32 B HMAC) dwarfs our whole 45 B sentence; no text compression; MMS voices are non-commercial; no LoRa/AFSK/hardware; energy VAD only; heavy (513 MB FP32 translation packs).
- **Threat to us**: **Med** — on security/mesh/store-and-forward/model-management breadth it beats us on paper and the docs are unusually honest, which juries like. On accuracy, bytes-per-sentence, radio links and measured evidence we are clearly ahead.

---

## 5. Anubhab47677/iTantra
- **Repo**: Anubhab47677/iTantra · Python + Lovable React frontend · 42 MB (venv committed) · pushed 2026-09-08 · 17 commits
- **What it is**: Two half-projects. `iTantra/`: faster-whisper STT + pyttsx3 TTS CLI/web demo with a **fake "69-byte neural codec"** (`neural_codec.py` just truncates text to 40 bytes and hashes speaker id). `itantra-ai-network/`: a real EnCodec bitrate-sweep experiment, XOR-parity FEC, 12-byte struct packet, UDP relay server with loss simulation, MMS-TTS via transformers. Plus a Lovable-generated React dashboard.
- **Pipeline & stack**: STT = faster-whisper (auto language detect, en/hi/or; "small" int8 in benchmark) · TTS = pyttsx3 (system) in demo; `facebook/mms-tts-*` via HF transformers in ai-network · no translation · encoding: 69 B fixed struct (fake tokens) / EnCodec 24 kHz codes at 1.5–24 kbps stored as int16 · FEC = XOR parity per 4 packets · transports: WebSocket/HTTP relay server, **FSK acoustic modem** (1200/2200 Hz, 15 ms/bit ≈ 66 bps, 100 ms 1800 Hz preamble) via sounddevice · Python desktop + web · offline-capable (Whisper local) but pyttsx3.
- **Genuinely good features/ideas**:
  - Acoustic FSK modem sending packets as audio tones (same family as our AFSK, but 66 bps vs our Bell-202 1200 bps).
  - EnCodec bitrate sweep with CSV: 1.5 kbps → 938 B for a Hindi clip (170.7× vs PCM) — an audio-fallback path for when STT confidence is low.
  - XOR parity FEC block (4+1) with recovery test.
  - Urgency flag + pitch-shift/tempo bytes in packet (prosody hint idea, not derived from audio).
  - Relay server simulating 15% loss / 100 ms latency for demos; WER/CER via jiwer script.
- **Measured numbers claimed**: "69 bytes per 5 s = 72 bps, 99.9% reduction" (packet is fixed-size; tokens are text bytes — no neural codec exists). EnCodec sweep CSV is real (1.5/3/6/12/24 kbps → 938/1875/3750/7500/15000 B).
- **Maturity**: **3** — single-machine pipeline works; relay is a simulator; no phones.
- **Weaknesses**: Fake neural codec advertised as headline; pyttsx3 TTS; venv and __MACOSX committed; Lovable UI; no Indic-specific STT.
- **Threat to us**: **Low** — pitch-heavy, code-light. Only the EnCodec audio-fallback idea is notable.

---

## 6. CodeVoyager3/iTantra
- **Repo**: CodeVoyager3/iTantra · Kotlin · 26 MB (sherpa-onnx AAR committed) · pushed 2026-09-11 · 2 commits
- **What it is**: Compose Android app with real sherpa-onnx IndicConformer (nemo_ctc) STT + Silero VAD, AI4Bharat Indic-TTS FastPitch+HiFi-GAN run directly on ONNX Runtime, a phrase-bank "translator", and a big `TacticalMeshTransport` (TCP 8889, UDP beacon, BT RFCOMM, BLE advertise/scan, Wi-Fi P2P) with flood relay. Model files are **not in the repo** (manifest-driven from assets); 2 commits, so unverifiable whether it ever ran on two phones.
- **Pipeline & stack**: STT = AI4Bharat IndicConformer int8 via sherpa-onnx `OfflineNemoEncDecCtcModelConfig` + Silero VAD (sherpa `Vad`) · TTS = Indic-TTS FastPitch→HiFi-GAN via `ai.onnxruntime` directly with `frontend.json` char vocab · translation = `BundledOfflineTranslator` 56 KB Kotlin phrase bank (10 languages × N tactical phrases, fuzzy phrase match, fallback = source text) · encoding = **JSON lines** over sockets (no compression) · transports: TCP server, UDP broadcast beacon, BT RFCOMM, BLE adv/scan for discovery, Wi-Fi Direct · Android native · offline.
- **Genuinely good features/ideas**:
  - Same STT/TTS model family as ours (IndicConformer + FastPitch) — directly comparable.
  - Flood mesh: node holds multiple simultaneous TCP/BT links, `seenPacketIds` cache + TTL + `relayHops`, exclude-origin-link when rebroadcasting.
  - Receiver-side language choice: incoming text translated (phrase-bank) into each receiver's selected language; caption shows "(hi ➔ ta)" and stores original.
  - Room DB voice log; radar-sweep pairing UI; device telemetry header (battery etc.).
- **Measured numbers claimed**: none.
- **Maturity**: **3** — plausible working single-device pipeline; mesh unverified, no tests, no models shipped.
- **Weaknesses**: JSON packets (hundreds of bytes); phrase-bank "translation" only works for pre-listed sentences; 2 commits; no eval; no hardware links.
- **Threat to us**: **Med-Low** — same model stack, plus mesh + receiver-language selection; but no compression, no measurements, no radio.

---

## 7. JashThaker9/itantra-voice-transceiver
- **Repo**: JashThaker9/itantra-voice-transceiver · TypeScript (Expo/React Native) · 16 MB · pushed 2026-09-07 · 1 commit (squash publish; release APK exists)
- **What it is**: Expo RN app that works on two phones over a hotspot: OS speech recognizer (Google, `requiresOnDeviceRecognition:false` in code) → text over UDP broadcast "local mesh" (join code) → `expo-speech` system TTS. Cloud features (ntfy relay, Google/MyMemory translate) gated behind a "SIH Offline Mode" toggle. Docs candidly say sherpa-onnx integration failed (`MethodTooLargeException`) so neural STT/TTS is "interim".
- **Pipeline & stack**: STT = `expo-speech-recognition` (Android SpeechRecognizer / Google) · TTS = `expo-speech` (system engine) with voice-style scoring · translation = cloud Google/MyMemory (disabled offline) · encoding = JSON over UDP · transports: UDP broadcast on LAN/hotspot port 47832 (hello/join/msg/ack), ntfy.sh cloud relay, custom HTTP relay server with metrics · platform Expo RN (+web) · **not offline-neural**.
- **Genuinely good features/ideas**:
  - "Hey iTantra" wake-word foreground service (Android SpeechRecognizer loop) + boot receiver.
  - QR pairing (`itantra://pair?code=`) and 6-char join codes; ack with peerCount.
  - Explicit SIH-offline-mode kill-switch isolating cloud paths; OSS license doc; i18n UI in 10 languages.
  - Download landing page + APK release + QR.
- **Measured numbers claimed**: none (relay-server metrics.js counts requests/latency only).
- **Maturity**: **4-** — two phones exchange text and speak it, but with system STT/TTS and JSON/UDP.
- **Weaknesses**: Google STT/TTS (not open, needs Google packs); no compression; no encryption; no neural models integrated; single squash commit; Sentry dependency.
- **Threat to us**: **Low-Med** — demo-ready and honest, but fails the "open-source on-device neural" requirement; wake-word and QR pairing are nice UX ideas.

---

## 8. jayanarayanmenonnettath2024aids/iTantra
- **Repo**: jayanarayanmenonnettath2024aids/iTantra · Python (desktop) · 6 MB (+LFS models) · pushed 2026-09-03 · 29 commits
- **What it is**: Desktop Python two-laptop system with extensive docs/tests: whisper-tiny STT, Piper + AI4Bharat VITS-RASA TTS via sherpa-onnx, Silero VAD, mDNS discovery, HMAC-authenticated binary packet v2, FastAPI web UI with latency waterfall. Benchmarks are real scripts with reported numbers (x86 CPU).
- **Pipeline & stack**: STT = `openai/whisper-tiny` (HF transformers, CPU) · TTS = Piper VITS (en, hi, te, ml) + `vits_rasa_13` AI4Bharat multi-speaker VITS FP32 via sherpa-onnx (ta/kn/mr/bn); gu no TTS, or none · no translation · VAD = Silero ONNX · encoding = `iTantraPacketV2`: 25 B fixed header (magic, ver, type, priority, lang, seq32, ts double, audio_bytes, tag len) + 32 B raw HMAC + sender/session ids + UTF-8 payload (**107 B secure frame for 28 B text**) · transports: TCP/LAN + mDNS (zeroconf) discovery, peer_transceiver · desktop web UI · offline.
- **Genuinely good features/ideas**:
  - Priority levels NORMAL/ELEVATED/ALERT/DISTRESS with UI preemption ("distress locking"); ACK/HEARTBEAT types.
  - Zero-config mDNS peer discovery; trust store + identity (`security/`) with attack tests doc.
  - Airtime table at 300/1200/2400/9600 bps for their frame (link-budget style, like ours).
  - Honest INT8-vs-FP32 TTS finding: dynamic INT8 VITS-RASA 13.3× slower (RTF 4.6) → kept FP32.
  - Streaming decoder / playback controller; ~50 tests across STT/TTS/transport/security/VAD.
- **Measured numbers claimed**: STT 567.9 ms, TTS 182.6 ms, net 18.3 ms, E2E 750–838 ms (4 s English clip, Windows CPU); payload 34 B raw / 284 B JSON frame → 107 B binary secure frame; VITS-RASA RTF 0.32 per language table. Backed by `tools/benchmark/` scripts and docs. No WER numbers.
- **Maturity**: **4** — two-process/two-laptop end-to-end with tests and benchmark scripts; desktop only.
- **Weaknesses**: whisper-tiny (weak on Indic; they never report WER); desktop Python, no Android; 107 B overhead per message; no compression, no radio/hardware, no mesh.
- **Threat to us**: **Med-Low** — good engineering discipline and benchmark docs, but wrong platform and much heavier wire format.

---

## 9. Nik-2208/itantra-stt
- **Repo**: Nik-2208/itantra-stt · Python + Kotlin · 3.4 MB (+LFS) · pushed 2026-09-11 · 14 commits
- **What it is**: Two parts. (a) Multi-module Android app ("ASTRA") whose engines are **stubs**: `TfliteSttEngine.recognize` returns rotating canned Hindi/Marathi phrases after `delay(300)`; `BluetoothTransport.startDiscovery` returns three hard-coded fake devices. (b) `itantra_pipeline/` Python: real sherpa-onnx IndicConformer int8 streaming-chunk STT, Silero VAD, sherpa-onnx **keyword-spotting (Zipformer KWS 3.3M)** wake word, rule-based emergency keyword classifier with per-language JSON.
- **Pipeline & stack**: STT = IndicConformer int8 via sherpa-onnx (Python) / stub on Android · TTS = none real (Android `TfliteTtsEngine` stub) · translation = interface only · encoding = `MessagePacket` + CRC16 + `PacketSerializer` (core module, unit-tested) · transports: stubs (Nearby Connections planned) · Android Compose + Python Gradio/`app.py` · offline.
- **Genuinely good features/ideas**:
  - sherpa-onnx KWS wake-word ("voice trigger") with keyword file — hands-free activation without full ASR.
  - Emergency classifier: P0 vs P2 from keyword lists (emergency/location/number terms) per language, applied to partial transcripts — cheap urgency auto-detection.
  - Streaming 100 ms chunk feeding + greedy/beam toggle; hyperparameters centralised.
- **Measured numbers claimed**: none.
- **Maturity**: **2** (Android) / 3 (Python STT lab) → **2** overall.
- **Weaknesses**: Android app is a mock; no TTS; no transport; Hindi-only keyword lists filled (others ~100 B placeholders).
- **Threat to us**: **Low** — the KWS wake-word + keyword urgency classifier are borrow-able ideas.

---

## 10. RITIKAYADAV-6318/iTantra
- **Repo**: RITIKAYADAV-6318/iTantra · Python · 1.3 MB · pushed 2026-09-14 · 36 commits
- **What it is**: Python simulation of "criticality- and confidence-aware bit allocation": faster-whisper gives per-word confidence, a tagger scores criticality, allocator (greedy and a "quantum-inspired evolutionary" QIEA) assigns protection per token, a channel simulator drops/corrupts tokens by bitrate/noise, Coqui XTTS v2 re-synthesises in the speaker's cloned voice. React/FastAPI dashboard. No bytes are ever actually encoded — the "packet" is a Python dataclass of token lists.
- **Pipeline & stack**: STT = faster-whisper "small" (word probabilities) · TTS = Coqui **XTTS v2** (voice cloning from reference clip; CPML non-commercial) · translation none · encoding none (dataclass; protection floats) · transport = software channel simulator only · desktop Python + React · offline models but heavy (XTTS ~2 GB).
- **Genuinely good features/ideas**:
  - `priority = criticality × (1 − confidence)` per token → unequal protection; QIEA vs greedy benchmark with plotted curve (`QIEA_Benchmark_Curve.png`).
  - Sound-event tags in packet (`channel/sound_events.py`) — non-speech audio events carried as labels.
  - Speaker embedding + prosody vector fields in the packet schema; speaker-voice preservation via XTTS cloning.
  - Pydantic contract tests between modules.
- **Measured numbers claimed**: none numeric in README (benchmark script prints; plot committed). Languages en/hi only.
- **Maturity**: **3** — single-machine simulated pipeline.
- **Weaknesses**: No wire format, no transport, no phones; XTTS is non-commercial and huge; README says ONNX/FEC/entropy coding "roadmap claims only". IndicConformer abandoned for Whisper.
- **Threat to us**: **Low** — research-flavoured story (confidence-aware protection, speaker identity) could impress on slides but nothing ships bytes.

---

## 11. Niranjan266/iTantra
- **Repo**: Niranjan266/iTantra · Kotlin · 0.8 MB (models fetched by script; APK in Releases) · pushed 2026-09-13 · 15 commits
- **What it is**: The most rigorous Android build in this group. Frozen `ITP-1` wire format (11 B header + 1 byte/symbol + CRC16), sherpa-onnx Zipformer (en) + **IndicConformer CTC (ta)** STT, Piper (en) + self-converted MMS VITS (ta) TTS, language packs as drop-in data folders, phrase codebook (12-bit index = 16 B message) doubling as cross-language translation, flood-relay mesh wrapper, BLE-advertisement broadcast bearer, Wi-Fi multicast, Wi-Fi Direct, RFCOMM, throttle wrapper simulating 300 bps bearer, in-app WER + latency percentiles + CSV. 226 unit tests. **Gate 2 passed on two real phones** (vivo→Moto, 62 B over RFCOMM) with logs quoted.
- **Pipeline & stack**: STT = sherpa-onnx streaming Zipformer 20M int8 (en) + AI4Bharat IndicConformer nemo_ctc int8 (ta), Whisper base kept as fallback engine · TTS = Piper VITS int8 (en) + `facebook/mms-tts-tam` exported+quantised to 36.8 MB (CC-BY-NC, disclosed) · translation = codebook index only (`Translator.kt`) · VAD = own `VadGate` (energy + endpointing) · encoding = ITP-1: 11 B header (ver/flags nibble, lang, urgency, seq, session, pitch/rate/energy prosody bytes, len, CRC-8) + payload symbols (control 0–15, CLS Indic phonemes 16–119, ARPAbet 120–179, numerals 180–199; or `TEXT_MODE` UTF-8) + CRC-16; optional 32 B speaker sidecar; `PHRASE_REF` = 3 B · transports: BT RFCOMM (verified), BLE advertisement mesh (connectionless), Wi-Fi multicast 239.x TTL=1, Wi-Fi Direct, loopback; `FloodRelay` and `ThrottleWrapper` decorators · Android native Compose · offline, no server.
- **Genuinely good features/ideas**:
  - Phrase codebook: 144 English / 32 Tamil parallel phrases; message = 16 B; fingerprinted append-only list; unresolved id shown as `[phrase N — not in codebook]` rather than mis-spoken. Parallel lists give **zero-cost cross-language delivery** for codebook phrases.
  - 3-byte prosody (pitch/rate/energy) extracted from the speaker's audio and applied at TTS (`ProsodyExtractor`, 17 tests) — carries *how* it was said, not just a flag.
  - Flood relay with dedup by (session, seq), hop limit in `MeshFrame`, random rebroadcast jitter; BLE-advert bearer needs no INTERNET permission.
  - Language packs as data (`pack.json` declares model type/paths/self-test sentence); `TokensFile` validates vocab in Kotlin before native load (documented crash fix); `PackDownloader`.
  - `ThrottleWrapper` + `LinkBudget`: live in-app "at 300 bps this took 1.7 s vs Opus 61 s" comparison; bearer selectable.
  - Alert policy: DISTRESS raises alarm volume 3/7→7/7 and restores after (verified on device); `AlertRules` per urgency level.
  - In-app WER (NFC-normalised, error attribution), latency P50/P95, CSV export; "Round trip" labelled honestly.
  - Measured Whisper-base vs IndicConformer on Tamil (≈100% vs 0% WER on one sentence) and wrote it up.
- **Measured numbers claimed**: 62 B for a 49-char English sentence over RFCOMM (log quoted); 75 B/3 s utterance vs 4,500 B Opus; 16 B phrase ref; models ready in 2.8 s, pack install 190 ms, APK 99 MB arm64, 0 dropped frames on Moto Edge 60 Pro. Backed by unit tests (`PhraseCodebookTest`, `ThrottleTest`) and device logs. No corpus WER.
- **Maturity**: **4** — two-phone RFCOMM verified; Tamil TTS on phone and mesh "needs on-device run"; only 2 languages.
- **Weaknesses**: Only en + ta packs (Hindi etc. absent); text mode = raw UTF-8 (Devanagari 3 B/char — no entropy coding); phoneme-symbol mode present in symbol table but real traffic shown is TEXT_MODE; no encryption; no LoRa/AFSK/hardware; no corpus-level CER; MMS voice non-commercial; mesh/BLE untested on devices.
- **Threat to us**: **High** — closest peer. Beats us on: phrase codebook (16 B), prosody bytes, live bearer throttle demo, drop-in language packs, mesh design, BLE-advert bearer, test count, write-up honesty. We beat it on: 10 languages with measured CER, VarnaCode entropy coding (4.5–5.4 bits/char vs 24 bits/char UTF-8 Indic), AES-GCM, real radio links (LoRa firmware, AFSK), CAP alerts, roll-call.

---

## 12. shyam0607-maxx/itantra
- **Repo**: shyam0607-maxx/itantra · Python + Next.js · 0.5 MB · pushed 2026-08-25 · 1 commit
- **What it is**: FastAPI backend + Next.js single "Simulator" page: upload/record audio → faster-whisper → bit-level channel simulator (bitrate, packet loss, BPSK/AWGN BER from SNR, latency) → **edge-tts (Microsoft cloud)** with pyttsx3 fallback → WER between pre/post-channel text. Untrained PyTorch "neural codec" class. Honest deferred list.
- **Pipeline & stack**: STT = faster-whisper · TTS = edge-tts (cloud) / pyttsx3 · none · encoding = UTF-8 bytes in 32 B packets · transport = simulator only · web · **cloud TTS**.
- **Genuinely good features/ideas**:
  - Channel simulator that really mutates bytes: BER = Q(√(2·SNR)) for BPSK/AWGN, packet loss, quality classification; unit-tested.
  - Deterministic adaptive-bitrate controller; result JSONs committed.
- **Measured numbers claimed**: "1,800×–2,400× compression" (text bytes vs PCM, printed by API); channel-induced WER only (documented as not ASR WER).
- **Maturity**: **3** — single-machine web pipeline.
- **Weaknesses**: Cloud TTS; no devices; no radio; whisper only; single commit.
- **Threat to us**: **Low**.

---

## 13. Parth99128/iTantra
- **Repo**: Parth99128/iTantra · Kotlin · 0.2 MB · pushed 2026-08-30 · 2 commits
- **What it is**: Untested Android scaffold (README: "does NOT include model files, a compiled/tested APK, or on-device numbers"). Vosk STT wrapper, Silero VAD via ORT, char-level VITS ONNX TTS wrapper, RFCOMM SPP transceiver, `measure_wer.py` with placeholder pairs.
- **Pipeline & stack**: STT = Vosk (`vosk-android:0.3.70`) · TTS = char-level VITS via `onnxruntime-android` (AI4Bharat-style, user must export) · none · encoding = raw text over RFCOMM · transports: BT RFCOMM SPP · Android Compose · offline (if models added).
- **Genuinely good features/ideas**:
  - Reasoned choice of char-level native-script VITS to avoid espeak-ng on Android.
  - Alert playback path "non-interruptible max volume" in `AudioPlayer`.
- **Measured numbers claimed**: none.
- **Maturity**: **2** — never built.
- **Weaknesses**: No models, no build, Vosk has weak Indic coverage.
- **Threat to us**: **Low**.

---

## 14. Prathamesh404NotFound/Itantra-APP
- **Repo**: Prathamesh404NotFound/Itantra-APP · Kotlin · 0.17 MB · pushed 2026-09-07 · 2 commits (project duplicated in `iTantra/` subfolder; AI-Studio metadata)
- **What it is**: Compose app using Android system speech recognizer (`EXTRA_PREFER_OFFLINE`) + system `TextToSpeech`, phrase-cluster "translation", TCP 8888 + UDP beacon transport and a BT transport, Room history, WER calculator, many demo dialogs (two-phone setup, architecture diagram, interactive demo).
- **Pipeline & stack**: STT = Android `SpeechRecognizer` prefer-offline (Google packs) · TTS = Android `TextToSpeech` (alarm stream 100% for critical) · translation = `OfflineTranslationEngine` concept-cluster phrase map (10 langs) + `LanguageDetectionEngine` (Unicode-block script detect + n-grams) · encoding = `PacketCodec` "IT" magic + `writeUTF` ids/langs + longs + CRC32 + UTF-8 payload + translated text (no compression) · transports: TCP server 8888 + UDP broadcast heartbeat on hotspot, Bluetooth RFCOMM · Android native · offline only if Google packs installed.
- **Genuinely good features/ideas**:
  - Script-based language auto-detect from text (Unicode block → language, with confidence).
  - Sentence boundary detector + simple VAD; performance screen with delivery-success and WER; emergency banner.
  - Packet carries both original and translated text.
- **Measured numbers claimed**: none.
- **Maturity**: **2–3** — plausibly runs on two phones over hotspot, but engines are system Google; 2 commits, unverified.
- **Weaknesses**: Google STT/TTS; ~80+ B header via `writeUTF`; phrase-map translation; AI-Studio generated, duplicated tree.
- **Threat to us**: **Low**.

---

## 15. anvesha-bhargava/iTantra
- **Repo**: anvesha-bhargava/iTantra · Kotlin · 0.13 MB · pushed 2026-08-25 · 1 commit
- **What it is**: Android Studio "Hello World" Compose template (MainActivity 1.3 KB, theme files). No README.
- **Pipeline & stack**: none.
- **Genuinely good features/ideas**: none.
- **Measured numbers claimed**: none.
- **Maturity**: **1** — template.
- **Weaknesses**: empty.
- **Threat to us**: **Low**.

---

## 16. babbaransh12-ux/ITANTRA
- **Repo**: babbaransh12-ux/ITANTRA · no language · 0.1 MB · pushed 2026-09-07 · 2 commits
- **What it is**: A 116 KB, 2,391-line requirements/architecture document (README) with status labels; "Status: MVP TARGET — implementation in progress". **Zero code.**
- **Pipeline & stack** (all PROPOSED): IndicConformer INT8 ORT, IndicTrans2 ONNX, IndicTTS, WebRTC VAD + RNNoise, Opus fallback at 24 kbps when STT confidence < threshold, protobuf + AES-256-GCM, UDP + ARQ, GNU Radio BPSK + conv/RS FEC simulation.
- **Genuinely good features/ideas** (design only): confidence-gated text-vs-Opus adaptive mode; calibration study plan; channel simulator + ablation plan.
- **Measured numbers claimed**: none (document is explicit that all are hypotheses).
- **Maturity**: **1** — document only.
- **Weaknesses**: no implementation.
- **Threat to us**: **Low** (unless they ship; the adaptive text/audio-fallback idea is the one to watch).

---

## 17. OG-Wizards/Itantra
- **Repo**: OG-Wizards/Itantra · Kotlin · 0.09 MB · pushed 2026-09-09 · 1 commit
- **What it is**: Android app + Ktor WebSocket relay server on a laptop. Android `SpeechRecognizer` → text over WebSocket → each receiver translates (phrasebook, or **Google ML Kit** on-device translate) → Android `TextToSpeech`. Also streams raw 16 kHz PCM over WebSocket ("live voice") — the opposite of low-bitrate.
- **Pipeline & stack**: STT = Android SpeechRecognizer · TTS = Android TextToSpeech · translation = ML Kit (downloadable models, proprietary) or phrasebook · encoding = text/JSON over WS; PCM binary frames · transports: Wi-Fi LAN WebSocket via laptop server · Android native + Ktor server · not offline-neural.
- **Genuinely good features/ideas**:
  - Receiver-side translation into each phone's own language (3-phone Marathi/Hindi/English demo).
  - Emergency: vibration + high-priority notification + full-screen `EmergencyActivity` + translated TTS; foreground service keeps socket; stable deviceId dedup on reconnect.
- **Measured numbers claimed**: none.
- **Maturity**: **3–4** (multi-phone via server) but architecture violates PS (server, raw PCM, Google engines) → effectively **3**.
- **Weaknesses**: Needs laptop server; proprietary ML Kit; no compression; no radio.
- **Threat to us**: **Low**.

---

## 18. Spirit019/itantra-isro
- **Repo**: Spirit019/itantra-isro · JavaScript (React/Vite) · 0.06 MB · pushed 2026-09-01 · 3 commits
- **What it is**: Browser demo: `webkitSpeechRecognition` → fake "18-byte token" hex inspector → `speechSynthesis`. LoRa air-interface sliders (distance/SF/ToA) are UI math. `model_manifest.json` + `download_models.py` list sherpa-onnx models but nothing loads them.
- **Pipeline & stack**: STT = browser Web Speech (Google cloud) · TTS = browser speechSynthesis · none · "SCSU + Indic-BPE + RS(32,24)" claimed, not implemented · transport none · web.
- **Genuinely good features/ideas**: LoRa time-on-air calculator UI by SF/BW (presentation aid); hex byte inspector UI.
- **Measured numbers claimed**: "18 B token, 24 bps, 2,666×", "369 ms E2E latency budget", "WER 13.44%, RTF 0.14" — all unbacked (manifest strings).
- **Maturity**: **2** — landing/demo page.
- **Weaknesses**: everything simulated; cloud speech APIs.
- **Threat to us**: **Low**.

---

## 19. JashThaker9/iTantra-download
- **Repo**: JashThaker9/iTantra-download · HTML · 0.04 MB · pushed 2026-09-06 · 4 commits
- **What it is**: One-page APK download landing page (index.html + logo) for repo #7.
- **Pipeline & stack**: none.
- **Genuinely good features/ideas**: none (distribution page).
- **Measured numbers claimed**: none.
- **Maturity**: **1**.
- **Weaknesses**: n/a.
- **Threat to us**: **Low**.

---
## Group 2

# SIH26173 competitor cards — group 2 (19 repos)

Method: GitHub API tree + raw files only, no clones. Commit counts from `Link: rel="last"` with per_page=1. "Claims vs code" distinctions are explicit. Baseline for comparison: our sherpa-onnx IndicConformer → VarnaCode → AES-GCM frames → Wi-Fi/BT/LoRa/AFSK → Piper/FastPitch, ~45 B/sentence, measured FLEURS CER.

---

## 1. arpitsharma7777/iTantra
- **Repo**: arpitsharma7777/iTantra, Kotlin, 271 MB (Vosk models committed), pushed 2026-09-09, ~38 commits
- **What it is**: Working Compose walkie-talkie for Hindi + English only. README claims 10 languages, Bluetooth, VAD, emergency alerts — code has 2 languages, Wi-Fi Direct only, no alert flag, no VAD beyond Vosk's own endpointing.
- **Pipeline & stack**: STT = Vosk (Kaldi, `model-hi`/`model-en` ~50 MB each, committed). TTS = Android `TextToSpeech` system engine. No translation. Encoding = JSON `{i,l,t,ts}` UTF-8, no compression. Transport = Wi-Fi Direct (`WifiP2pManager`) + TCP socket. Platform = native Kotlin/Compose. Fully offline.
- **Genuinely good features/ideas**:
  - `MetricsManager` + `WerCalculator` (word-level Levenshtein) with a Developer screen for live STT/TTS/e2e latency; unit-tested.
  - Compose UI tests for every screen (5 androidTest files) + 4 unit test files.
- **Measured numbers claimed**: none in README; WER calculator exists but no results published.
- **Maturity**: 4 — Wi-Fi Direct + TCP two-phone path is fully wired (discovery → connect → socket → STT → send → TTS); no evidence of hardware run but code is complete.
- **Weaknesses**: 2/10 languages; Vosk Hindi is old/weak; system TTS (device-dependent, not open-source); JSON on the wire (~80+ B overhead/msg); no BT despite README; no alerts.
- **Threat to us**: Low — no axis beats baseline; only Wi-Fi Direct (vs our NSD/TCP) is a minor differentiator.

## 2. anvesha-bhargava/iTantra-master
- **Repo**: anvesha-bhargava/iTantra-master, Kotlin, 153 MB (103 MB Dolphin int8 model committed), pushed 2026-08-31, ~2 commits
- **What it is**: Bluetooth-RFCOMM walkie-talkie with a TTL-flooded "Room" mesh. Notably, `MainActivity.kt` imports `com.iTantra.app.room.RoomMeshManager` and `ui.room.*` which do NOT exist in the tree — the pushed repo does not compile as-is.
- **Pipeline & stack**: STT = sherpa-onnx `OfflineDolphinModelConfig` (DataoceanAI Dolphin CTC int8, 103 MB, one model for all langs, no language argument). TTS = sherpa-onnx VITS Piper `hi_IN-priyamvada-medium` only (espeak-ng-data copied from assets). No translation. Encoding = JSON envelope, newline-framed (UTF-8-safe `StreamFramingBuffer`). Transport = Bluetooth Classic RFCOMM server+client, multi-peer. Native Kotlin/Compose. Offline.
- **Genuinely good features/ideas**:
  - ACK + 2 s timeout retry per message with dedupe by id (`CommunicationService.sendDirectMessage`).
  - TTL-decrementing rebroadcast over all connected BT neighbours (`message.ttl - 1` forward) — real multi-hop flooding, in code.
  - Room protocol: ANNOUNCE / JOIN_REQUEST / ACCEPT / REJECT / PRESENCE / LEAVE message types (group/channel model) — but the manager class is missing from the repo.
  - Language enum for all 10 PS languages; per-message `language` field.
- **Measured numbers claimed**: none.
- **Maturity**: 3 — transport + ACK/relay logic is real but the room UI/manager is missing so the build is broken; TTS is Hindi-only.
- **Weaknesses**: Dolphin is not Indic-tuned (Hindi/Urdu script ambiguity likely); only Hindi TTS; JSON on wire; no compression; 2 commits; missing source files.
- **Threat to us**: Med — a jury reading the code would credit BT multi-hop + rooms + ACK/retry (all baseline gaps); execution quality is low.

## 3. aditya-vrm/Itantra-app
- **Repo**: aditya-vrm/Itantra-app, TypeScript (Expo/React Native), 85 MB (Vosk models), pushed 2026-08-25, ~7 commits
- **What it is**: Expo RN app: Vosk hi/en → JSON over Bluetooth Classic → expo-speech. README is the untouched Expo template; `architecture.md` describes Whisper ONNX / MarianMT / VITS / mesh / cloud WebSocket — none of that is in code.
- **Pipeline & stack**: STT = `react-native-vosk` (hi, en). TTS = `expo-speech` (system engine). No translation. Encoding = JSON `{text,lang,isAlert}` + newline. Transport = `react-native-bluetooth-classic` RFCOMM only. Platform = Expo RN. Offline.
- **Genuinely good features/ideas**:
  - `isAlert` flag: alert TTS forces volume 1.0 and is not interruptible by later messages (`ttsService.speak`).
- **Measured numbers claimed**: none.
- **Maturity**: 3 — single BT socket path wired end-to-end; plausible on two phones but small and 2-language.
- **Weaknesses**: template README, architecture doc is aspirational; 2 languages; system TTS; no compression; RN/Expo overhead on low-end phones.
- **Threat to us**: Low.

## 4. lector-sys/itantra
- **Repo**: lector-sys/itantra, Kotlin, 53 MB (50 MB sherpa-onnx AAR committed), pushed 2026-09-11, ~2 commits (large squashed pushes; 34 KB `MASTER_BUILD_PROMPT.md` — AI-driven build)
- **What it is**: The most complete engineering package in this group: Compose app with downloadable language packs, binary wire protocol with CRC + ACK + clock sync, TCP and BT RFCOMM, ESP32 reference receiver, desktop FLEURS eval scripts with committed JSON results, emulator benchmark doc. README is unusually honest about gaps.
- **Pipeline & stack**: STT = sherpa-onnx Meta **Omnilingual ASR 300M CTC INT8** (Apache-2.0, 9 Indic langs, no language arg) + Whisper tiny INT8 for English. VAD = Silero (in APK). TTS = Piper lessac (en) + **MMS VITS per language** (CC-BY-NC). No translation. Encoding = raw UTF-8 in a 12-byte binary header (`IT` magic, ver, type, flags, lang id, u32 msgId, u16 len) + CRC-16/CCITT, optional 16 B timing; no text compression. Transport = TCP (host/join by IP) + Bluetooth Classic RFCOMM; BLE fragmentation implemented but unused. ESP32 BluetoothSerial (SPP) receiver firmware. Native Kotlin/Compose. Offline after pack download.
- **Genuinely good features/ideas**:
  - **Language-pack system**: in-app HF download with SHA-256 + retry/backoff, USB sideload scripts, `packs.json` manifest → APK stays 24–34 MB.
  - **Urdu→Devanagari transliterator** (`UrduToDevanagari.kt`, unit-tested) to rescue Hindi output that Omnilingual emits in Perso-Arabic ~50% of the time.
  - ALERT preempts NORMAL at a *clause boundary*, interrupted message resumes afterwards; alerts replay once after 1 s; clause-by-clause TTS into streaming `AudioTrack` (first clause 48–677 ms).
  - ACK_REQ / 800 ms × 3 retransmit / dedupe; **NTP-style clock sync** (PING/PONG, min-RTT of 20 samples) for true one-way latency measurement.
  - ESP32 firmware parses same frames, CRC-checks, ACKs, pulses buzzer on ALERT (SPP, not LoRa).
  - Debug-hook broadcast receiver for headless e2e (`DEBUG_SEND`, `DEBUG_STT_FILE`, `DEBUG_EXPORT` CSV); every utterance saved as WAV in debug builds.
  - Foreground service (`specialUse`) so receiver keeps speaking with screen off; auto-rejoin backoff.
  - 26 unit tests (protocol, clock sync, normaliser, transliteration); instrumented model verification test; UI strings translated into all 10 languages.
- **Measured numbers claimed** (all emulator/desktop, with scripts + JSON in `tools/eval/results/`): FLEURS 12-sample WER/CER — en 18.9/7.2, hi 31.7/13.0, or 53.4/17.3, ta 24.0/17.8, bn 39.4/9.2 %; STT RTF 0.064–0.09 (omnilingual), 0.04 (whisper); TTS first clause 48 ms en / 677 ms hi, RTF 0.035 / 0.213; TTS round-trip CER 1.1 % en / 7.5 % hi; RSS 534 MB after STT decode; APK 23.9 MB armv7 / 33.5 MB arm64. Evidence: `bench_stt.py`, `eval_wer_fleurs.py`, result JSONs present. No phone numbers.
- **Maturity**: 5 — two-emulator e2e verified + ESP32 firmware + eval scripts; honest that hardware BT/phone runs are missing.
- **Weaknesses**: Hindi CER 13 % vs our 2.9 %; Omnilingual script-flipping hack; MMS TTS is CC-BY-NC (violates "open-source only" spirit); no text compression at all (raw UTF-8: a Hindi sentence is ~3× our bytes); no LoRa/AFSK; no encryption; emulator-only numbers; 2 commits looks AI-generated in one shot.
- **Threat to us**: **High** — on engineering polish, pack management, protocol docs, latency instrumentation and honesty it would impress a jury; we beat it on accuracy, bytes/sentence, radio transports, encryption and real-speech CER.

## 5. HarshCoder1122/iTantra
- **Repo**: HarshCoder1122/iTantra, Kotlin, 42 MB (26 MB sherpa AAR + 2.9 MB demo.mp4), pushed 2026-09-05, ~9 commits
- **What it is**: Tactical-styled Compose app with a real multi-transport flood mesh, IndicConformer STT + FastPitch/HiFi-GAN TTS via raw ONNX Runtime — but **model weights are not in the repo** (2.3 GB, "regenerate with tools/"). "Cross-language translation" is a 15-phrase phrasebook + word dictionary.
- **Pipeline & stack**: STT = sherpa-onnx `OfflineNemoEncDecCtcModelConfig` IndicConformer INT8 (~141 MB/lang) + Silero VAD. TTS = AI4Bharat Indic-TTS FastPitch INT8 + HiFi-GAN fp32 via `OrtSession` (~118 MB/lang), sentence-chunked streaming. Translation = `BundledOfflineTranslator` phrasebank (15 phrases × 10 langs) + concept dictionary; word-by-word only for hi↔mr. Encoding = JSON (`type/text/ttl/...`), no compression. Transport = UDP 8888 beacon/broadcast + TCP 8889 + BT RFCOMM + Wi-Fi Direct init; BLE = scan/advertise only (no GATT data path). Native Kotlin/Compose, Room DB. Offline.
- **Genuinely good features/ideas**:
  - **Flood relay**: node holds several TCP/BT links at once, forwards unseen packets with `ttl-1`, `seenPacketIds` cache with exclude-source — real A→B→C mesh in code.
  - `CRITICAL_DISTRESS` broadcast: siren tone, forced max volume, haptic pattern (`AlertAudioManager`).
  - Per-device role: transceiver / STT-only / TTS-only (accessibility for hearing- or speech-impaired users).
  - Telemetry header: battery, RSSI, link quality, IP, RAM.
  - Model manifest (`model_manifest.json`) + `BundledModelManager` that reports a language "unavailable" rather than faking; `tools/model_conversion/PROGRESS.md` is a frank 31 KB engineering log.
  - Demo video committed.
- **Measured numbers claimed**: only model sizes (STT 141 MB int8/lang; TTS 63+56 MB/lang; debug APK ~2.3 GB). No WER/latency.
- **Maturity**: 3 — pipeline code is complete and a demo video exists, but repo cannot run STT/TTS without regenerating 2.3 GB of weights; mesh not shown on hardware.
- **Weaknesses**: no weights → not reproducible; "translation" is a phrasebook; JSON wire; no compression; BLE is decorative; APK size absurd; Wi-Fi Direct only initialised.
- **Threat to us**: Med — mesh relay + SOS siren + role modes are visible differentiators in a pitch; accuracy/bytes/radio we win.

## 6. udaisankars/iTantra
- **Repo**: udaisankars/iTantra, Kotlin, 20 MB, pushed 2026-09-08, 1 commit ("Initial commit")
- **What it is**: English+Tamil-only transceiver with real BLE GATT transport and ML Kit translation. README description says "offline multilingual STT, translation and TTS" — code has 2 languages.
- **Pipeline & stack**: STT = sherpa-onnx Whisper tiny/small (en, ta). TTS = sherpa-onnx VITS (`tts_en`, `tts_ta`). Translation = **Google ML Kit on-device translate** (`com.google.mlkit:translate`, proprietary, needs one-time online model download) + verified-phrase table (`HybridTranslationEngine`). Encoding = JSON v2 envelope, ≤1500 chars. Transport = **BLE GATT** (server+client, MTU negotiation 23→247, advertising with manufacturer data) + Wi-Fi TCP transceiver; receiver runs as a Service. Native Kotlin/Compose.
- **Genuinely good features/ideas**:
  - Real BLE GATT data path with MTU request + fallback timer and chunking (`BleTextTransceiver`, 37 KB).
  - Background `ITantraRecieverService` so messages are spoken while app is backgrounded.
  - Legacy plain-text packet fallback for protocol-version migration.
- **Measured numbers claimed**: none.
- **Maturity**: 3 — single-commit dump, plausible two-device BLE/Wi-Fi but unverified; 2 languages.
- **Weaknesses**: Whisper for Tamil (weak); ML Kit is proprietary + requires internet once; 2/10 languages; JSON; no compression; no alerts.
- **Threat to us**: Low — BLE GATT and translation are the only things we lack; jury would notice proprietary ML Kit.

## 7. NipunAdarsh/Itantra
- **Repo**: NipunAdarsh/Itantra, TypeScript-tagged (actually Kotlin; 653-file tree bloated with `.agents/` Stitch/Codex skill dirs), 12 MB (models via LFS, not in tree sizes), pushed 2026-09-03, ~18 commits
- **What it is**: Compose walkie-talkie with hardware-measured (and self-corrected) 10-language benchmark; README explicitly retracts earlier fake numbers. Wi-Fi path field-tested; BT written but not tested.
- **Pipeline & stack**: STT = sherpa-onnx IndicConformer 120M INT8 shared (hi + 5 "known broken") + **dedicated kn/te/ta checkpoints**, SenseVoice Small INT8 for English (with ITN). VAD = Silero v5 (30 ms chunks, 500 ms pause) for "phone mode". TTS = Piper VITS **INT8-requantized** for 7 langs (en, hi, bn, ml, mr, te, ta), Android system TTS for gu/kn/or. No translation. Encoding = plain text `[LANG:xx][ALERT]<text>`, no compression. Transport = UDP 9999 discovery + TCP 8888; BT RFCOMM with device picker. Native Kotlin/Compose. Offline.
- **Genuinely good features/ideas**:
  - `BenchmarkActivity` on-device runner emitting JSON (WER/CER/RTF/TTS latency) + WAV export; 30 test cases.
  - INT8 requantization of Piper voices (470 → 138 MB) with "zero regression" check.
  - `IndicScriptConverter`: Unicode block-offset remap Devanagari→bn/gu/or/ml (<1 ms) — hacky but a real attempt at the shared-checkpoint script problem.
  - `[ALERT]` → `USAGE_ALARM` + STREAM_ALARM max volume.
  - PTT vs hands-free auto-VAD mode toggle.
  - 59 KB research dossier + pitch deck committed; honest about 5 broken languages.
- **Measured numbers claimed**: on two Xiaomi phones — WER en 5.6 %, hi 4.2 %, kn 41.7 %, ta 33.3 %, te 66.7 %, mr 81.9 %, gu 91.1 %, bn 94.4 %, ml 130.6 %, or 160 %; model sizes 229 MB SenseVoice, 188 MB shared IC, 134 MB × 3 dedicated, 138 MB TTS; APK 823 MB, ~1.8 GB installed. Evidence: `BenchmarkActivity.kt` exists — **but ground-truth audio is synthesized by the app's own Piper TTS**, so WER measures TTS→STT round-trip, not real speech.
- **Maturity**: 4 — two-phone Wi-Fi verified with logged benchmark; BT untested.
- **Weaknesses**: 5/10 languages effectively unusable; 823 MB APK; circular benchmark; plain-text wire, no compression; 3 langs on device TTS.
- **Threat to us**: Med — honest hardware numbers and a benchmark activity resemble our Evaluation Mode; our real-FLEURS CER across all 10 languages, 45 B/sentence and ~140 MB/lang beat it outright.

## 8. DakshG26/itantra-android
- **Repo**: DakshG26/itantra-android, Kotlin, 5.5 MB (6 MB APK committed), pushed 2026-09-02, ~7 commits
- **What it is**: Classic-Views Android app using **Google `SpeechRecognizer` + system TTS**, claiming "18-byte quantized neural token packets (2,666× compression)". `TokenCompressor` truncates text to 11 UTF-8 bytes and pads with fixed "pitch tokens"; the actual wire payload is a Gson JSON `RadioPacket` with full text + a hard-coded `tokensHex`. Misleading.
- **Pipeline & stack**: STT = Android `SpeechRecognizer` (Google, may hit cloud). TTS = Android `TextToSpeech`. No translation. Encoding = Gson JSON; fake 18-byte packet displayed in UI. Transport = BT RFCOMM + UDP auto-discovery + TCP + Wi-Fi Direct manager. Native Kotlin (XML layouts). Companion web app on Vercel (separate repo).
- **Genuinely good features/ideas**:
  - 3-digit "radio channel" number UX (`#001`) instead of IP entry.
  - SOS flag with priority vibration on all nodes.
  - Committed APK + web demo link (easy for jury to try).
- **Measured numbers claimed**: "18-byte packet, 2,666× compression" — computed from `(3 s × 32 kB/s) / 18`; not real (text truncated, JSON actually sent).
- **Maturity**: 3–4 — transports likely work phone-to-phone; the "neural" pipeline is Google services.
- **Weaknesses**: proprietary/cloud STT; fabricated compression claim; JSON on wire; no models.
- **Threat to us**: Low — a technical jury would see through it; the channel-number UX is the only idea worth borrowing.

## 9. itz-Arun-001/iTantra-version2
- **Repo**: itz-Arun-001/iTantra-version2, Python (+Next.js UI), 2.6 MB, pushed 2026-09-10, ~37 commits
- **What it is**: Desktop (Windows laptop, GPU) prototype: Silero VAD → Whisper large-v3-turbo (en) / IndicConformer 600M RNNT (hi/ta/te) → gzip → UDP with ACK/retry → Indic Parler-TTS. Honest README: Android "not started".
- **Pipeline & stack**: STT = HF `transformers` Whisper-large-v3-turbo + `ai4bharat/indic-conformer-600m-multilingual` (PyTorch/CUDA). TTS = AI4Bharat Indic Parler-TTS (heavy). No translation. Compression = gzip, skipped when it doesn't shrink. Transport = real UDP between two laptops, throttled to target bitrate, sequence numbers + missing-packet retry; web UI uses in-process simulated loss. Platform = Python CLI + Flask + Next.js + Tkinter. Offline models but desktop-scale.
- **Genuinely good features/ideas**:
  - Priority-aware reliability: Emergency packets get more retry attempts (`packet_reliability.py`, `network_sender.py`).
  - Bitrate-mode simulator (8k/4k/1k/0.5k bps) with transmission-time readout.
  - Side-by-side Whisper vs IndicConformer transcript evidence in README (Tamil).
- **Measured numbers claimed**: "98.44 % bandwidth reduction at LOW" (bytes of text vs recorded audio file — script exists); no WER, no latency logs.
- **Maturity**: 3 — two-laptop UDP link proven, but nothing on-device/mobile; 4/10 languages.
- **Weaknesses**: not Android; GPU-scale models; Parler-TTS impractical on phones; gzip on short Indic text rarely helps.
- **Threat to us**: Low — well-documented but off-platform.

## 10. Barath410/iTantra
- **Repo**: Barath410/iTantra, Kotlin, 1.2 MB (models via LFS), pushed 2026-09-12, ~9 commits
- **What it is**: Ambitious multi-module clean-architecture skeleton (core/{common,database,datastore,designsystem,location,mlcore,network}, data, domain, feature/*) with a spec-driven binary protocol, X25519+AES-GCM crypto, LZ4, BLE GATT transport — but Tamil-only ML, dozens of 0-byte files, `r8-error.txt` (2.3 MB) and `mlcore-error.txt` committed → build currently failing. No README.
- **Pipeline & stack**: STT = raw `OrtSession` IndicConformer Tamil int8 with own `MelSpectrogram` + `CtcGreedyDecoder`. VAD = Silero via ONNX + `VadStateMachine`. TTS = MMS VITS Tamil (`VitsTokenizer`). NMT = `IdentityNmtEngine` (stub). Encoding = binary TLV packets (`FieldId`: TEXT, LANG, TIMESTAMP, GPS_LAT/LNG, USER_NAME, MEDICAL_SUMMARY, ACK_SEQ, DEVICE_ID, ROLE, PUBLIC_KEY, SESSION_ID), header with session/seq/frag index+count/nonce, **LZ4 block** (skipped <20 B), **X25519 ECDH + HKDF-SHA256 + AES-128-GCM** session keys. Transport = **BLE GATT** (advertiser, scanner, client, server, HelloBeacon); `WifiDirectTransport.kt` is 0 bytes. Native Kotlin/Compose, Hilt, Room.
- **Genuinely good features/ideas**:
  - Authenticated key exchange over BLE handshake (X25519 → session key) — stronger than our pre-shared AES-GCM.
  - TLV packet with optional GPS lat/lng, medical summary, user role (civilian/rescuer) → SOS packet carries location + medical info.
  - Fragmentation fields in header for BLE MTU.
  - Room entities for emergency contacts, medical info, SOS events, peer devices, offline map tile metadata (map/tiles code is stubbed).
  - 5 protocol/crypto/compression unit test files (`PacketRoundTripTest` etc.).
- **Measured numbers claimed**: none.
- **Maturity**: 2 — extensive scaffolding, Tamil-only engines, build broken, feature screens (conversation, SOS) are empty files.
- **Weaknesses**: doesn't build; 1 language; LZ4 is useless on <100 B Indic text; MMS TTS (CC-BY-NC); no README; over-architected.
- **Threat to us**: Low now, Med if finished — the ECDH handshake + GPS/medical SOS TLV design is a genuinely better protocol story than ours on paper.

## 11. abdulsamad1366/iTantra--Indian-Multilingual-TTS-STT-
- **Repo**: abdulsamad1366/iTantra--Indian-Multilingual-TTS-STT-, Dart/Flutter, 0.7 MB, pushed 2026-09-12, ~8 commits
- **What it is**: Flutter UI shell with a real binary packet codec and TCP socket, but **STT and TTS are stubs**: `SttService.transcribe` sleeps 180 ms and returns a hard-coded per-language emergency sentence; `TtsService.speak` sleeps 120 ms and returns. README/ARCHITECTURE describe sherpa-onnx pipelines that aren't wired.
- **Pipeline & stack**: STT/TTS = stubs (sherpa_onnx pub dependency present, unused). No translation. Encoding = `iT` magic + type + src/tgt lang + i64 ts + 8-byte id + u16 len + **zlib** payload (23-byte header). Transport = TCP `ServerSocket`/`Socket` on LAN; BT RFCOMM enum only. Flutter (Android + macOS runner). CI workflow for flutter test.
- **Genuinely good features/ideas**:
  - Packet codec with source AND target language fields (translation-ready) + unit test (`packet_codec_test.dart`).
  - Model management screen + `download_models.sh` (UI only).
- **Measured numbers claimed**: "<100 bytes per sentence, <500 bps, >98.4 % reduction" — no script; STT is fake so nothing measured.
- **Maturity**: 2 — UI + codec only; speech pipeline is simulated.
- **Weaknesses**: fake STT/TTS; zlib adds ~11 B overhead making short packets bigger; no BT.
- **Threat to us**: Low.

## 12. sulagnapatra2006/iTantra_project
- **Repo**: sulagnapatra2006/iTantra_project, Python, 0.5 MB, pushed 2026-09-06, ~11 commits
- **What it is**: 2-file Streamlit demo: Whisper-tiny (HF pipeline) → `mtranslate` (Google Translate scraping) → gTTS (Google cloud TTS). `app.py` header still says "OmniEdu AI". No transport.
- **Pipeline & stack**: STT = `openai/whisper-tiny` via transformers. Translation = mtranslate (cloud). TTS = gTTS (cloud). No encoding, no transport. Python/Streamlit.
- **Genuinely good features/ideas**: none beyond a translate step.
- **Measured numbers claimed**: none.
- **Maturity**: 1 — demo script, cloud-dependent, no transmission.
- **Weaknesses**: everything cloud; whisper-tiny for Indic; no link.
- **Threat to us**: Low.

## 13. Sridharpeddamanishi9710/itantra-backend
- **Repo**: Sridharpeddamanishi9710/itantra-backend, TypeScript, 0.2 MB, pushed 2026-09-14, ~11 commits
- **What it is**: Turborepo cloud backend: Next.js "C2 portal" (REST: auth token, channels, ingest, SOS, telemetry, transmissions sync, model manifest/download, incidents) + Prisma/Postgres schema (Transceiver, Transmission with compact text + priority + lat/lng, EmergencyIncident) + `ws` stream gateway with callsign registration and EMERGENCY_BROADCAST channel. No STT/TTS/app; the Android client is elsewhere or non-existent. README is the create-next-app template.
- **Pipeline & stack**: none on-device. Transport = HTTPS REST + WebSocket to a server. Cloud only.
- **Genuinely good features/ideas**:
  - Command-and-control concept: store-and-forward sync endpoint (`transmissions/sync`), SOS incident lifecycle with responder assignment, callsign-based addressing, priority levels, tactical map component, OTA model manifest/download API.
- **Measured numbers claimed**: none.
- **Maturity**: 2 — backend-only, no client, contradicts the offline PS.
- **Weaknesses**: requires internet + Postgres; irrelevant to low-bitrate link problem.
- **Threat to us**: Low — but the "C2 dashboard that ingests field messages" is an idea a jury might like as an add-on.

## 14. JayPol559/iTantra
- **Repo**: JayPol559/iTantra, Kotlin, 0.16 MB, pushed 2026-09-07, ~2 commits (Google AI Studio-generated; `public/assets/aistudio/`, `firebase.ai` dep)
- **What it is**: Feature-rich-looking Compose app (5 screens, 8 dialogs incl. "Architecture diagram", "Two phones setup", "Accuracy testing") built on **Google `SpeechRecognizer` + system `TextToSpeech`**; translation is a 7-cluster phrasebook; language detection is Unicode block counting.
- **Pipeline & stack**: STT = Android `SpeechRecognizer` (offline preference flag). TTS = Android `TextToSpeech`. Translation = `TranslationEngine` phrase clusters (NEED_HELP, FIRE_ALERT, MEDICAL_ALERT…). Encoding = custom binary via `DataOutputStream` (magic, version, UTF strings, seq, priority byte) + CRC32. Transport = TCP 8888 + UDP 8889 discovery (`LocalNetworkTransport`) + `BluetoothTransport` RFCOMM. Room DB history. Native Kotlin/Compose. Depends on Firebase AI SDK (cloud) though usage unclear.
- **Genuinely good features/ideas**:
  - Unicode-block script auto-detection of incoming text (`LanguageDetectionEngine`).
  - `SentenceBoundaryDetector` + simple energy VAD classes.
  - Emergency categories + `EmergencyAlertBanner`; `PerformanceMonitor` + `WerCalculator`; in-app "Two phones setup" wizard dialog.
- **Measured numbers claimed**: none.
- **Maturity**: 2–3 — code is plausible but generated in 2 commits; Google STT/TTS; untested.
- **Weaknesses**: proprietary STT/TTS; Firebase dependency; phrasebook "translation".
- **Threat to us**: Low.

## 15. shashiproduction90-bit/iTantra
- **Repo**: shashiproduction90-bit/iTantra, Kotlin (build/ intermediates committed), 0.13 MB, pushed 2026-09-12, ~9 commits
- **What it is**: Self-described "Kotlin starter": one `MainActivity.kt` (12 KB) + `NsdHelper`. NSD discovery, `RecognizerIntent` (Google) STT, system TTS, no socket send. README lists team-member placeholders 1–6 and wrong PS id (SIH26103).
- **Pipeline & stack**: STT = `RecognizerIntent`. TTS = system. Transport = NSD discovery only, no data path. Native Compose.
- **Genuinely good features/ideas**: none.
- **Measured numbers claimed**: none ("metric placeholders").
- **Maturity**: 2 — UI only, admits it.
- **Weaknesses**: everything.
- **Threat to us**: Low.

## 16. radspatidar/iTantra
- **Repo**: radspatidar/iTantra, JavaScript (React 19 + Vite + Capacitor), 0.1 MB, pushed 2026-09-12, ~2 commits (Figma Make export)
- **What it is**: Browser demo; "STT" is `mockSTT()` returning canned sentences; TTS = Web Speech; "mesh transport" = `BroadcastChannel` between tabs of the same browser. Capacitor Android wrapper is an empty shell. README claims BLE/Wi-Fi Direct native drivers that don't exist.
- **Pipeline & stack**: STT = mock. TTS = `speechSynthesis`. Encoding = JSON. Transport = BroadcastChannel (same device only). Web/Capacitor.
- **Genuinely good features/ideas**:
  - Keyword-based automatic priority classification (`priority.js`: emergency/important keyword lists in en + hi) → auto-escalate a message to Emergency with full-screen red override + manual ACK + replay.
  - Three priority tiers (normal / important / emergency).
- **Measured numbers claimed**: none.
- **Maturity**: 2 — UI prototype.
- **Weaknesses**: nothing real.
- **Threat to us**: Low.

## 17. Chiraag2006/Vaanix---iTantra
- **Repo**: Chiraag2006/Vaanix---iTantra, no language, 0.09 MB, pushed 2026-09-13, ~23 commits (all .gitkeep/docs)
- **What it is**: Empty skeleton — 15 `.gitkeep` dirs, 4 short docs, `requirements.txt` (faster-whisper, silero-vad, msgpack, reedsolo, crcmod, GNU Radio intent). Every status checkbox unchecked.
- **Pipeline & stack**: planned only: faster-whisper, Silero, msgpack packets, CRC + Reed-Solomon FEC, GNU Radio/SDR.
- **Genuinely good features/ideas**: (planned, not implemented) Reed-Solomon FEC + SDR transmission, 4-level priority byte in packet spec.
- **Measured numbers claimed**: none.
- **Maturity**: 1 — empty.
- **Weaknesses**: no code.
- **Threat to us**: Low.

## 18. saiharsha2512-tech/iTantra
- **Repo**: saiharsha2512-tech/iTantra, Dart/Flutter, 0.05 MB, pushed 2026-09-04, ~2 commits
- **What it is**: Flutter UI (splash, language grid, walkie-talkie screen) with `speech_to_text` plugin (Google/Apple STT); `CommunicationService` is an interface whose implementation has empty method bodies; `nearby_connections` and `hive` in pubspec unused; native `STTEngine.kt`/`VADEngine.kt`/`CommunicationEngine.kt` are 0-byte files. README = Flutter template.
- **Pipeline & stack**: STT = `speech_to_text` (platform/Google). TTS = interface only. Transport = none (stub). Flutter.
- **Genuinely good features/ideas**: none.
- **Measured numbers claimed**: none.
- **Maturity**: 2 — UI only.
- **Weaknesses**: no transport, no TTS, proprietary STT.
- **Threat to us**: Low.

## 19. Bhaktee2323/itantra
- **Repo**: Bhaktee2323/itantra, HTML/JS, 0.03 MB, pushed 2026-09-04, 1 commit ("Add files via upload")
- **What it is**: Single-page browser demo: Web Speech API STT → keyword "semantic analysis" (intent/destination/time/entity/priority) → estimated "compression %" → simulated lossy channel → tiny dictionary translation (mr/hi/en) → `speechSynthesis`, with Azure Speech cloud fallback for Marathi TTS (`server.js` not in tree). README honestly labels everything as simulated.
- **Pipeline & stack**: STT = browser Web Speech (cloud). TTS = browser + Azure. Translation = small dictionary. Transport = none (JS simulation). Web.
- **Genuinely good features/ideas**:
  - Semantic-field extraction idea (intent + destination + time + entities) as the transmitted unit rather than raw text; priority queue with emergency-first and retry — all heuristic/simulated.
- **Measured numbers claimed**: compression "%" displayed but README says "estimated metrics, not a real encoder".
- **Maturity**: 1 — landing-page demo.
- **Weaknesses**: cloud STT/TTS, no transport, no models.
- **Threat to us**: Low.

---
## Group 3

# SIH26173 competitor cards — group 3 (19 repos)

Method: GitHub trees API + raw file reads only (no clones). Commit counts from `commits?per_page=1` Link header. Surveyed 2026-09-15.

---

## 1. HaRsHa91544/iTantra-sih
- **Repo**: HaRsHa91544/iTantra-sih, Java, 229 MB (37 MB sherpa-onnx AAR + Vosk + Piper model in assets), pushed 2026-09-08, ~19 commits
- **What it is**: Native Java Android app, English-only STT→Wi-Fi Direct→TTS loop. README is 21 bytes; the real docs are their own audit files (BASELINE_RESULTS.md, REPOSITORY_AUDIT.md) which honestly say "End-to-end NOT TESTED — requires 2 physical devices".
- **Pipeline & stack**: STT = Vosk `model-en-in` (offline, Indian English only). TTS = Piper `en_IN-spicor-medium` via sherpa-onnx OfflineTts + bundled espeak-ng-data. No translation. No compression — JSON `{text,senderId,timestamp,language}` with 4-byte length prefix over TCP. Transport = Wi-Fi Direct (WifiP2pManager, group-owner = server) only. Platform = Android native Java. Fully offline.
- **Genuinely good features/ideas**:
  - Clean interface split (STTEngine / TTSEngine / MessageTransport / SocketConnection) so engines are swappable
  - Server accept-loop reconnect, length-prefixed framing, TTS stop-request latency handling
  - Self-audit documents comparing branches (rare honesty)
- **Measured numbers claimed**: "APK 202.73 MB", "estimated 3–5 s end-to-end, unmeasured". No STT/TTS accuracy or latency numbers; no eval script.
- **Maturity**: 3 — compiles, single-device static pass; their own doc says two-device runtime never tested.
- **Weaknesses**: English only (0 of 9 Indic languages), 200 MB APK, no compression, JSON wire format, no Bluetooth, no tests beyond template.
- **Threat to us**: Low — nothing beats our baseline on any axis; English-only disqualifies it on the PS's core requirement.

---

## 2. Spirit019/iTantra-ISRO-SIH26173
- **Repo**: Spirit019/iTantra-ISRO-SIH26173, Kotlin (listed HTML due to 2.6 MB portal snapshot), 142 MB (mostly a PDF catalogue + research JSON + ~100 AI-agent orchestration markdown files under `.agents/`), pushed 2026-09-07, ~19 commits
- **What it is**: README claims "100% Offline", "Open-Source Only", milestone 2 "on-device TTS complete", and describes a `org/isro/itantra/tts/` tree. **The actual code is `com/itantra/voice/` and the entire STT→translate→TTS pipeline is Sarvam AI cloud (Saaras v3 STT, Mayura v1 translate, Bulbul v3 TTS) over OkHttp with an API key in BuildConfig.** README architecture does not match the tree. Heavy AI-generated project scaffolding.
- **Pipeline & stack**: STT = Sarvam Saaras (cloud). Translation = Sarvam Mayura (cloud). TTS = Sarvam Bulbul (cloud, 37 named speakers). Compression = none (Unishox2 is "queued"); wire = 4-byte length + UTF-8 JSON TransportMessage {messageId UUID, timestamp, type, sourceLanguage, targetLanguage, text, priority}. Transport = Wi-Fi Direct + persistent TCP socket (Phase A implemented). Platform = Android Kotlin + Compose. Cloud-dependent.
- **Genuinely good features/ideas**:
  - Source→target language selection with swap; receiver auto-speaks in its own language (translation in the loop, albeit via cloud)
  - TelemetryBar showing STT / Trans / TTS / NET / Total ms per message
  - Message types TRANSLATION / ALERT / HANDSHAKE / PING with priority int
  - Thumbs-up/down FeedbackRepository persisted locally
  - 20 unit-test files (mostly against a Sarvam mock)
- **Measured numbers claimed**: "T_synth 329 ms, RTF 0.172, tap-to-ear 490 ms" — for a milestone-2 on-device TTS that no longer exists in the tree; no script reproduces it.
- **Maturity**: 3 — Wi-Fi Direct transport + cloud pipeline probably runs on device with a key, but claims of offline/on-device are false.
- **Weaknesses**: Entirely cloud (violates PS "no proprietary/cloud APIs"), README contradicts code, no compression, 100 MB of agent-logs noise.
- **Threat to us**: Low — a jury that asks "does it work in airplane mode?" ends it. Only the telemetry bar and per-message translation UX are worth noting.

---

## 3. gogul098/itantra-repo
- **Repo**: gogul098/itantra-repo, Kotlin + Python (listed HTML), 82 MB (committed `build/` dir with APK + onnxruntime .so files, 3 PPTX decks), pushed 2026-09-08, ~2 commits
- **What it is**: A conceptual "semantic transceiver" skeleton: text → SONAR 1024-d sentence embedding → int8 → BLE L2CAP → cosine cache / SONAR decoder → Piper. ASR is a hard-coded mock ("dummy transcription result"), SONAR tokenizer is mocked (`longArrayOf(101,202,303,404)`), `demo.py` is a `time.sleep` print script.
- **Pipeline & stack**: STT = stub (comment says IndicConformer via sherpa-onnx, not wired). Semantic = SONAR encoder/decoder ONNX via onnxruntime (model file absent → "Mock Mode"). VAD = Silero ONNX (real asset, 2.3 MB). TTS = PiperTtsEngine (1 KB stub). Compression = int8 quantization of 1024-d embedding → **1028 bytes + 4-byte lang tag per utterance**. Transport = BLE L2CAP CoC + RFCOMM classes (written, untested). Platform = Android Kotlin. Python tooling has a differentiable "AnalogRadioChannel" (bandpass 300–3000 Hz + AWGN + fades) for training a neural channel autoencoder — training script present, no results.
- **Genuinely good features/ideas**:
  - Cosine-similarity cache of pre-rendered phrase WAVs on the receiver (Room DB) for a ~120 ms "fast path" — interesting idea for fixed tactical phrases
  - ASR confidence gate (abort TX below 0.70)
  - Differentiable analog-radio channel simulator (torchaudio) for training
- **Measured numbers claimed**: "1028 bytes payload", "cache hit ~120 ms / miss ~2.5 s" — printed by a sleep script, no measurement.
- **Maturity**: 2 — skeleton with mocks; payload is 20× larger than our 45 B.
- **Weaknesses**: Nothing real end-to-end; semantic embedding is language-agnostic but 1 KB/utterance defeats the low-bitrate premise; committed build artifacts.
- **Threat to us**: Low — the "send meaning not text" pitch could sound novel to a jury, but nothing runs.

---

## 4. rishikafrfr/iTantraaa
- **Repo**: rishikafrfr/iTantraaa, Kotlin, 50 MB, pushed 2026-09-14, ~4 commits (bulk pushes; last msg "WORKING PROTOTYPE")
- **What it is**: The most complete engineering effort in this group. Native Kotlin/Compose app with sherpa-onnx STT/TTS, sideloadable model "packs", binary CRC16 wire protocol with ACK/retransmit, TCP + Bluetooth RFCOMM links, foreground service, and a real eval harness with FLEURS numbers and emulator two-device e2e logs. README is 1 byte; docs/ has BENCHMARKS.md, MODELS.md, PROTOCOL.md, LICENSES.md, DEMO_SCRIPT.md, MASTER_BUILD_PROMPT.md (AI-driven build, but real).
- **Pipeline & stack**: STT = Meta **Omnilingual ASR 300M CTC INT8** via sherpa-onnx (one 365 MB model for all 10 languages, auto script detection), optional Whisper tiny/base/small INT8 packs for English. VAD = Silero. TTS = Piper en_US-lessac + **MMS VITS per language (CC-BY-NC)** via sherpa-onnx, clause-by-clause streaming into AudioTrack (splits on danda). No translation. **No compression** — payload is raw UTF-8 inside a 12-byte header + CRC16 frame. Transport = TCP (host/join, auto-rejoin backoff 2/5/10 s) + Bluetooth RFCOMM; BLE NUS fragmentation codec written (MTU-3 chunks) but no BLE link. ESP32 firmware referenced in PROTOCOL.md but **not in the tree**. Platform = Android Kotlin + Compose. Fully offline after pack install (packs downloaded from HF with SHA-256 verification, or sideloaded via SAF).
- **Genuinely good features/ideas**:
  - Binary wire protocol: magic "IT", version, type (HELLO/TEXT/ACK/PING/PONG/PARTIAL/BYE), flags (ALERT/ACK_REQ/FINAL/HAS_TIMING), lang id, uint32 msg id, CRC-16/CCITT, magic-hunting resync
  - ACK + retransmit (800 ms × 3) with dedupe by msg id; sender UI shows acked/failed
  - ALERT queue preempts NORMAL queue; preempted message returns to front; alerts replay once after 1 s
  - NTP-style clock sync (PING/PONG, best-of-20 lowest RTT) to measure true cross-device speech-end→audio-start latency
  - Pack catalog with HF resolve URLs, SHA-256, licence per pack; install/delete UI; per-language TTS engine cache
  - HELLO handshake exchanges supported TTS languages
  - Foreground service (specialUse) so receiver keeps speaking with screen off on Android 15
  - Urdu-script→Devanagari transliterator to fix Omnilingual emitting Urdu for Hindi audio
  - TextNormaliser (numbers etc.), danda clause splitting for first-clause latency
  - Debug hook BroadcastReceiver + adb scripts for headless e2e on two emulators
  - Per-ABI release APK 23.9 MB (armeabi-v7a)
- **Measured numbers claimed** (all backed by scripts in tools/eval and JSON results committed): FLEURS 12-sample screening, desktop: CER en 7.2 / hi 13.0 / or 17.3 / ta 17.8 / bn 9.2 %; WER hi 31.7 %. Emulator: STT RTF 0.064–0.066, Piper first-clause 48–50 ms, MMS-hi first-clause 619–677 ms, TTS round-trip CER 1.1 % (en) / 7.5 % (hi). Two-emulator e2e HELLO/ALERT/ACK/screen-off all pass. Honest caveat: "emulator numbers on desktop CPU, phone numbers TODO".
- **Maturity**: 4 — two-device e2e demonstrated (emulators), engines real, evidence committed. Not 5: no real phone numbers, no hardware link, ESP32 missing.
- **Weaknesses**: Zero text compression (our 45 B vs their ~100–200 B UTF-8 Indic); MMS TTS is CC-BY-NC (they flag it); Omnilingual 365 MB pack far over budget and their Hindi CER 13 % vs our 2.9 %; no translation; 4 commits = low visible git history; no LoRa/AFSK.
- **Threat to us**: **High** — the strongest all-round competitor in this group. A jury would see a comparably professional app with better link reliability (ACK/retransmit, clock-synced latency, alert preemption, pack manager). We beat them on accuracy (IndicConformer), payload size (VarnaCode), transports (LoRa/AFSK), and licence cleanliness.

---

## 5. DevDevotee-DD/iTantra
- **Repo**: DevDevotee-DD/iTantra, Kotlin, 40 MB, pushed 2026-08-31, ~1 commit ("done")
- **What it is**: Single-commit Compose app: Vosk English STT → Google Nearby Connections → Android system TTS. Works as a text relay in principle; no README.
- **Pipeline & stack**: STT = Vosk `vosk-model-small-en-us-0.15` loaded from filesDir (user must push it; installer class present). TTS = Android `TextToSpeech` system engine (locale mapped from language code). No translation. No compression — JSON bytes via `Payload.fromBytes`. Transport = Google Nearby Connections (Play Services — proprietary SDK). Platform = Android Kotlin + Compose. Offline but Play-Services-dependent.
- **Genuinely good features/ideas**:
  - `CommunicationMessage` carries speechEnd/sttStart/sttEnd/txStart timestamps; `PerformanceMetrics` computes STT finalization delay, TTS start latency, estimated raw-PCM bytes vs payload bytes (honest: "network latency null — unsynchronized clocks")
  - Emergency-alert message type + priority field
  - 20 KB `AppLanguage.kt` UI i18n table for all 10 languages
- **Measured numbers claimed**: none.
- **Maturity**: 3 — plausible single pipeline; unverified across devices.
- **Weaknesses**: English-only US model, system TTS, Nearby (Play Services) transport, no tests, one commit.
- **Threat to us**: Low.

---

## 6. Vishal-4356/itantra-v2
- **Repo**: Vishal-4356/itantra-v2, Dart/Flutter + Kotlin, 19 MB, pushed 2026-09-13, ~18 commits
- **What it is**: Flutter "tactical transceiver" whose README claims purged Google ML Kit / SpeechRecognizer / TextToSpeech and a "100% open-source offline Indic NMT engine". **In code: `MainActivity.kt` uses Android `SpeechRecognizer` and `TextToSpeech`; `SherpaAiIsolateManager` is an explicit mock returning empty audio; `tool/setup_models.dart` fabricates fake ONNX files by writing a header + repeating byte pattern to reach target sizes (45 MB "zipformer encoder", 18 MB × 10 "piper" files).** The "NMT" is a hard-coded phrase dictionary + English suffix stemmer. `assets/models/nmt/vocab.json` has 7 tokens.
- **Pipeline & stack**: STT = Android SpeechRecognizer (platform, often Google-backed). TTS = Android TextToSpeech system engine. Translation = static phrase dictionary (`OfflineIndicTranslator`, ~800 lines of phrases) for 10 languages. Compression = **Mode 1: 4-byte intent packet** (8-bit header, 4-bit lang, 12-bit intent id, 2-bit priority, 6-bit seq); Mode 2: msgpack text frame + CRC32; Mode 3: raw WAV. FEC = XOR parity block (K data + 1 parity, frame magic 0xFC). Transport = UDP broadcast discovery on 255.255.255.255:19876 + embedded HTTP server on :18080 over hotspot LAN; nearby_connections and flutter_blue_plus fallbacks. Platform = Flutter. Offline (but platform STT may go to Google).
- **Genuinely good features/ideas**:
  - 4-byte fixed intent codes for a 16-intent phrasebook — genuinely tiny for canned emergencies
  - XOR-parity FEC engine with unit tests (test/protocol_and_fec_test.dart)
  - Zero-config hotspot pairing via UDP broadcast ping + HTTP `/announce`
  - DND override + STREAM_ALARM max volume via MethodChannel
  - Locale JSONs for 10 languages; native-script range detection incl. Odia U+0B00–0B7F
  - `checkLanguagePacks()` reports which system TTS voices are installed and deep-links to install
- **Measured numbers claimed**: "32-bit payload", "P2P (1 Connected) within 1 second" — the 4-byte figure is real by construction; no latency/accuracy evidence.
- **Maturity**: 2.5 — transport/protocol layer is real and tested; the "neural" layer is fake models + platform APIs.
- **Weaknesses**: Fabricated model files, README misrepresents stack, relies on Google platform STT, phrasebook "translation" only, no Indic ASR at all.
- **Threat to us**: Low–Med — the 4-byte intent + FEC + zero-config LAN story is a slick demo, but any technical probe collapses it.

---

## 7. Musa2609/iTantra-
- **Repo**: Musa2609/iTantra-, Python (Flask web UI), 11 MB, pushed 2026-09-13, ~39 commits
- **What it is**: Desktop/laptop Python pipeline with a Flask sender/receiver web UI and a separate `communication/` acoustic bridge. Multi-mode: Opus voice, 10-bit semantic intent, UTF-8 text, EnCodec. Transmits between two laptops **through speakers/mic using ggwave FSK tones**. References "parity with Android PacketProtocol.kt/FecEngine.kt" but no Android code exists in the repo.
- **Pipeline & stack**: STT = AI4Bharat `indic-conformer-600m-multilingual` via HF transformers (gated repo, PyTorch, ~2.5 GB download), OpenAI Whisper base fallback. Translation = IndicTrans2 dist-200M (indic↔en). TTS = AI4Bharat Indic Parler-TTS (heavy, non-mobile) in acoustic bridge; Windows SAPI / espeak / formant fallback in Flask app. Compression = modes: Opus bitstream (via libsndfile), 10-bit semantic payload (4-bit type / 4-bit intent / 2-bit severity = 2 bytes), raw UTF-8 text, EnCodec 1.5–24 kbps codes. Packet = magic 'I' + ctrl byte + uint16 seq + len + CRC16; CRC32 for ggwave packets. FEC = XOR parity per 2 data frames. Transport = **ggwave audible acoustic modem** (140-byte MTU, chunked), software loopback. Platform = Python desktop only.
- **Genuinely good features/ideas**:
  - Acoustic data-over-sound link (ggwave) demonstrated between two physical laptops — a genuine "any analog channel" demo, similar in spirit to our AFSK
  - Hybrid keyword intent classifier → 2-byte semantic payload with severity; emergency flag drives TTS "mode"
  - Real Opus and EnCodec neural-codec comparisons (test_encodec.py claims up to 940× vs PCM)
  - Auto language detection via IndicConformer + IndicTrans2 translation to a target language before send
  - Chunk/reassemble with missing-count reporting; CRC-gated delivery
- **Measured numbers claimed**: "EnCodec up to 940× compression", "140-byte acoustic MTU". No WER/latency table; test scripts exist but no results committed.
- **Maturity**: 3 — single-laptop pipeline real, two-laptop acoustic test documented as a procedure ("PHYSICAL ASR/TTS TEST: PASS" printed by script), nothing mobile.
- **Weaknesses**: Not Android; 2.5 GB PyTorch models; Parler-TTS unusable on phones; gated HF models; ggwave is a third-party modem (our AFSK is our own); README of subfolder points to a different repo.
- **Threat to us**: Low–Med — the acoustic-modem and Opus/EnCodec comparison make a good slide, but it is not an app.

---

## 8. sritanvi10/iTantra
- **Repo**: sritanvi10/iTantra, Kotlin + vendored C/C++, 3.8 MB (+ whisper.cpp and libpiper sources; 1496 tree entries), pushed 2026-09-03, ~2 commits
- **What it is**: Honest, well-documented **skeleton** ("buildable Android Studio project skeleton"; PROGRESS_LOG: "Not done this session: actually compiling this project"). Vendored whisper.cpp Android JNI example + a libpiper JNI bridge that "cannot link yet". Model files are 133-byte LFS pointers.
- **Pipeline & stack**: STT = whisper.cpp (ggml) via vendored Kotlin JNI. TTS = Piper via libpiper JNI (unbuilt) with Android system TTS fallback. No translation. No compression — 4-byte length + JSON {type,text,lang,alert,ts,seq}. Transport = Bluetooth Classic RFCOMM only. VAD = energy RMS. Platform = Android Kotlin (view-binding).
- **Genuinely good features/ideas**:
  - Two modes: walkie-talkie PTT vs "phone call" continuous duplex with energy VAD sentence detection
  - Alert keyword detection → interrupt playback, USAGE_ALARM max volume
  - PTT_START/PTT_END/HEARTBEAT/MODE_SYNC control messages
  - docs/LICENSING.md flags piper1-gpl GPLv3 chain
- **Measured numbers claimed**: none ("Real-device testing / latency & WER measurement: not done").
- **Maturity**: 2 — never compiled, no models.
- **Weaknesses**: Whisper (weak Indic), GPL TTS, BT only, JSON, no tests, never run.
- **Threat to us**: Low.

---

## 9. itz-Arun-001/iTantra
- **Repo**: itz-Arun-001/iTantra, Python + Next.js UI, 2.4 MB, pushed 2026-09-04, ~19 commits
- **What it is**: Honest desktop prototype: mic → Silero VAD → Whisper → gzip → simulated/throttled UDP link with loss + retry → Indic Parler-TTS, with Flask API + Next.js UI and a Tkinter UI. README status table explicitly lists Android, real transport, PTT as "not started".
- **Pipeline & stack**: STT = `openai/whisper-large-v3-turbo` via transformers (README says whisper-small; 4 languages en/hi/ta/te). VAD = Silero. TTS = AI4Bharat Indic Parler-TTS. No translation. Compression = gzip (skipped when it doesn't help). Transport = UDP between two laptops (`network_sender.py`, hard-coded IP) throttled to 8000/4000/1000/500 bps, plus in-process simulation. Platform = Python desktop + web UI.
- **Genuinely good features/ideas**:
  - Priority-aware retry (emergency 5 attempts vs normal 3) with receiver NACK of missing seqs
  - Bitrate-mode simulator (HIGH/MEDIUM/LOW/EXTREME) with live "transmission stats" UI
  - VAD onset/offset padding to avoid clipping first/last word
- **Measured numbers claimed**: "98.44 % bandwidth reduction at LOW mode" (computed from bitrate ratio, not measured); "no formal WER benchmarking yet".
- **Maturity**: 3 — working single-device pipeline; two-laptop UDP script exists.
- **Weaknesses**: Whisper-large-v3-turbo + Parler-TTS = GB-scale desktop models; gzip on short Indic text inflates; no Android; 4/10 languages.
- **Threat to us**: Low.

---

## 10. sachinsoni27/itantra
- **Repo**: sachinsoni27/itantra, TypeScript/Electron, 1 MB, pushed 2026-06-10, ~5 commits
- **What it is**: **Unrelated** — a fork of "CodeInterviewAssist / interview-coder" (screenshot → Gemini/OpenAI solution generator, stealth typer). Nothing to do with SIH26173. Name collision only.
- **Pipeline & stack**: n/a (OpenAI/Gemini APIs, Electron).
- **Genuinely good features/ideas**: none relevant.
- **Measured numbers claimed**: none.
- **Maturity**: 1 (for this PS).
- **Weaknesses**: n/a.
- **Threat to us**: None.

---

## 11. helo-ayush/iTantra
- **Repo**: helo-ayush/iTantra, Kotlin, 632 KB source (models hosted on HF `helo-ayush/itantra-models`, ~268 MB per language pack, catalogue live), pushed 2026-09-14, ~34 commits
- **What it is**: Large Compose "disaster mesh" app (SOS beacon, walkie-talkie, rescue radar, model hub) — 172 KB ViewModel, 130 KB screens. Real ONNX Runtime inference code for IndicConformer int8 STT (own log-mel front end) + FastPitch/HiFi-GAN TTS with downloadable packs, falling back to Google `SpeechRecognizer` and system TTS. Mesh sends **both** translated text and **raw 16 kHz PCM voice frames** over UDP broadcast.
- **Pipeline & stack**: STT = ORT IndicConformer int8 (`filesDir/models/{tag}/stt/indicconformer_int8.onnx` + vocab; comment admits "input names/shapes cannot be verified without device") → fallback GoogleSttEngine. TTS = ORT FastPitch + HiFi-GAN → fallback system TextToSpeech. Translation = **Google ML Kit Translate** (on-device but proprietary) hi↔en + emergency dictionary. Compression = none. Framing = 'IT' preamble, 8-byte node id, **TTL hop byte**, msg type, len, CRC32. Transport = Wi-Fi Direct group + UDP broadcast :8889; BLE advertising/scanning with 22-byte manufacturer-data distress beacon. Platform = Android Kotlin + Compose. Offline except model download.
- **Genuinely good features/ideas**:
  - BLE distress beacon in advertisement payload (no connection needed) with Kalman-smoothed RSSI distance estimator and compass minimap of victims
  - TTL field in frame header for multi-hop relay (relay logic itself not verified)
  - SOS triggers: PanicShakeDetector, PowerButtonSosDetector; TacticalMeshService foreground
  - Model hub with remote catalogue JSON, SHA-256, download/delete/restore UI, per-language packs
  - Peer profile (name/age/gender) and translation-capability beacons
  - Battery indicator, TX power / beacon interval / hop-limit settings
  - Light/dark tactical theme, host-testable pure-JVM codecs with unit tests
- **Measured numbers claimed**: none (README markets features, no metrics).
- **Maturity**: 3 — lots of real code, but STT/TTS ONNX path self-described as unverified; sends raw PCM voice frames which contradicts the PS.
- **Weaknesses**: Raw PCM over mesh; ML Kit + Google STT fallbacks (proprietary); 268 MB/lang packs; no compression; no eval; monolithic 172 KB ViewModel.
- **Threat to us**: Med — feature breadth (SOS beacon, radar, mesh settings, model hub) will impress a non-technical jury; on the PS's core axes (bytes/sentence, offline open-source ASR accuracy, latency numbers) it has nothing.

---

## 12. Prathamesh404NotFound/Itantra ("Wake Takie")
- **Repo**: Prathamesh404NotFound/Itantra, TypeScript (React/Vite PWA + Express), 447 KB, pushed 2026-09-07, ~9 commits
- **What it is**: Browser PWA built with an AI app builder (metadata.json: `MAJOR_CAPABILITY_SERVER_SIDE_GEMINI_API`). STT = browser Web Speech API, TTS = `speechSynthesis`, peers via WebRTC DataChannel with **Firebase** signalling.
- **Pipeline & stack**: STT = `webkitSpeechRecognition` (Chrome → Google cloud). TTS = Web Speech `speechSynthesis`. Translation = phrase-cluster dictionary. Compression = none; binary packet with 'TANT' magic, 28-byte header, CRC32 (zod-validated). Transport = WebRTC DataChannel (STUN) + Firebase Realtime fallback. Platform = web PWA. Cloud-dependent.
- **Genuinely good features/ideas**:
  - In-app WER calculator with benchmark sentences per language (AccuracyTestingDialog)
  - Performance screen with bandwidthReductionPercent per packet, delivery-state machine (QUEUED…PLAYING)
  - Two-phones setup wizard, architecture diagram dialog, PWA install
- **Measured numbers claimed**: per-packet computed reduction %; no real evaluation.
- **Maturity**: 2.5 — web demo works online; not offline, not Android-native.
- **Weaknesses**: Cloud speech APIs, Firebase, Gemini; no on-device models.
- **Threat to us**: Low.

---

## 13. SomrajBanik/SankatLink
- **Repo**: SomrajBanik/SankatLink, Kotlin, 194 KB, pushed 2026-09-09, ~11 commits
- **What it is**: Polished Compose UI with three screens (Emergency voice note, Walkie-talkie, Phone mode) and a long README describing Silero VAD + IndicConformer + IndicTrans2 + sherpa-onnx TTS + Wi-Fi Direct/BLE mesh. **All four engine files are Kotlin `interface`s with TODO comments; no sherpa-onnx dependency in gradle; no transport implementation.**
- **Pipeline & stack**: STT/TTS/translation/mesh = interfaces only. Real code = EmergencyAudioController (audio focus + STREAM max volume + vibration), waveform visualizer, language dialog, ViewModel with mock messages. Platform = Android Kotlin + Compose.
- **Genuinely good features/ideas**:
  - One-tap pre-translated SOS phrase broadcast concept; per-message "📦 72 Bytes via BLE" footprint chip in UI
  - Named channels (Emergency SOS / Medical / Evacuation) in the UI
- **Measured numbers claimed**: "~60–120 bytes", ">99.5 % reduction" — arithmetic, no code.
- **Maturity**: 2 — UI only.
- **Weaknesses**: No AI, no transport.
- **Threat to us**: Low.

---

## 14. Aashi-Tiwari2006/iTantra
- **Repo**: Aashi-Tiwari2006/iTantra, Kotlin, 144 KB, pushed 2026-09-13, ~7 commits
- **What it is**: Simple Android chat app: Android `SpeechRecognizer` → Gson JSON over Bluetooth RFCOMM or plain TCP (:8888) → Android `TextToSpeech`. Plus an unrelated Flask `stt-server/` using Whisper base.en + IndicConformer (server-side).
- **Pipeline & stack**: STT = platform SpeechRecognizer (10 locales listed). TTS = system TextToSpeech. Compression = none (Gson DataPacket {language,type,message}). Transport = BT RFCOMM (SPP UUID) + TCP socket. Platform = Android Kotlin (Activities). Two sherpa `tokens.txt` assets present with no sherpa dependency.
- **Genuinely good features/ideas**:
  - Message type normal/alert/emergency in packet
  - Both BT and Wi-Fi socket paths exist
- **Measured numbers claimed**: none.
- **Maturity**: 3 — likely works phone-to-phone as a text relay using platform engines.
- **Weaknesses**: Platform STT/TTS (Google), no compression, no models, no tests.
- **Threat to us**: Low.

---

## 15. uditya001/iTantra
- **Repo**: uditya001/iTantra, no language, 134 KB, pushed 2026-09-14, ~67 commits
- **What it is**: **README only** (single file in tree). 67 commits editing a marketing README that describes Vosk STT + Nearby Connections + PTT. No code.
- **Pipeline & stack**: claimed Vosk + Google Nearby Connections + on-device TTS; nothing implemented.
- **Genuinely good features/ideas**: none in code.
- **Measured numbers claimed**: none.
- **Maturity**: 1.
- **Weaknesses**: Empty.
- **Threat to us**: None.

---

## 16. Durgesh-18/iTantra
- **Repo**: Durgesh-18/iTantra, Kotlin, 99 KB, pushed 2026-08-24, ~5 commits
- **What it is**: Compact, well-reasoned native app: sherpa-onnx Dolphin CTC / IndicConformer STT, Piper TTS, three transports (Wi-Fi TCP :7947, Nearby, BT SPP), language pack zips with manifests, RAM policy (swap STT/TTS engines on <4 GB phones), metrics CSV. Last commit "Finish the offline Hindi/English demo path". No numbers recorded.
- **Pipeline & stack**: STT = sherpa-onnx `OfflineDolphinModelConfig` (DataoceanAI Dolphin CTC int8, Apache-2.0) or NeMo CTC (IndicConformer export script). VAD = Silero. TTS = Piper int8 via sherpa-onnx (explicitly refuses MMS for CC-BY-NC). No translation. No compression — 4-byte length + JSON RadioMessage {v,id UUID,t0,lang,kind,prio,text}. Transports = Wi-Fi TCP, Google Nearby P2P_STAR, Bluetooth Classic SPP. Platform = Android Kotlin + Compose + foreground service. Fully offline after pack import.
- **Genuinely good features/ideas**:
  - RamPolicy: measures total/avail RAM and PSS, sequential engine swap on <4 GB, `swap_ms` metric — directly targets the PS efficiency rubric
  - Pack manager (zip import via SAF, MANIFEST.json per language, model files kept out of the APK; APK only carries ~2 MB VAD)
  - Roles STT / TTS / PHONE with PTT on/off; idle path = VAD only (1 thread) for low idle CPU
  - Metrics CSV columns stt_ms, radio_ms, tts_ms, rtf, e2e_ms, swap_ms + live overlay
  - JSON schema for wire format; "ESP32 can open TCP and print text" note
  - Licence hygiene doc (Piper model cards, MMS forbidden)
- **Measured numbers claimed**: none — README says targets ("idle CPU <3 %") and "until a real PSS measurement is recorded".
- **Maturity**: 3 — pipeline real and coherent; no evidence of a two-phone run or numbers.
- **Weaknesses**: JSON payload (~150 B+ per message with UUID), no compression, no translation, Dolphin's Indic coverage/accuracy unknown, 5 commits and stale since Aug 24.
- **Threat to us**: Med — design quality is close to ours on efficiency thinking (RAM policy, pack size) and it hits the rubric language directly; it lacks our codec, links, and measured CER.

---

## 17. kedarpatil2612-wq/iTantra-
- **Repo**: kedarpatil2612-wq/iTantra-, Kotlin, 88 KB, pushed 2026-09-05, ~1 commit
- **What it is**: Untouched Android Studio Compose "Hello World" template (MainActivity 1.3 KB + theme files). Empty README.
- **Maturity**: 1. **Threat**: None.

---

## 18. thanzeelfathima8-eng/ITantra_Project
- **Repo**: thanzeelfathima8-eng/ITantra_Project, Python, 42 KB, pushed 2026-09-07, ~3 commits ("Add files via upload")
- **What it is**: Tidy Python simulation package (no Android): VAD → STT → **Huffman-or-zlib text compressor** → packetize → Hamming(7,4) FEC → BPSK/QPSK baseband modem over AWGN channel with packet loss → CRC → **packet-loss concealment (word repair)** → TTS. Mock backends by default; real backends = IndicConformer-600M and Indic Parler-TTS via HF. Streamlit UI + benchmark script producing a WER-vs-SNR curve.
- **Pipeline & stack**: STT = mock / AI4Bharat IndicConformer (transformers). TTS = mock / Indic Parler-TTS. Compression = per-message Huffman over code points (table shipped in JSON!) vs zlib, pick smaller. FEC = Hamming(7,4). Modem = BPSK/QPSK numpy simulation. Transport = simulated channel only. Platform = Python. Bitrate presets 300/600/1200 bps.
- **Genuinely good features/ideas**:
  - **Prosody side-channel**: quantised mean pitch / energy / speaking-rate sent with text to steer TTS tone (8–32 bins)
  - **Speaker embedding** sent once per session (MFCC mean/std stand-in) to condition TTS voice
  - Packet-loss concealment: rule-based or masked-LM fill-in of lost words, with repaired words highlighted in UI
  - Hamming FEC + BPSK/QPSK + AWGN simulator and `benchmark.py` WER-vs-SNR robustness curve
  - Unit tests for FEC, modem, packetize, compressor, e2e
- **Measured numbers claimed**: bitrate presets are design targets; benchmark script exists but no results committed.
- **Maturity**: 2.5 — simulation-only, mock ASR/TTS by default.
- **Weaknesses**: No device, no real link, Huffman table shipped per message (kills gains on short text — the opposite of our fixed per-script tables), heavy HF models for real mode.
- **Threat to us**: Low — but the prosody/speaker side-channel and loss-concealment ideas are the most interesting "research" angle in the group.

---

## 19. shreyapazuru/SIH26173- ("NEXA VOICE")
- **Repo**: shreyapazuru/SIH26173-, Python, 30 KB, pushed 2026-09-10, ~11 commits
- **What it is**: Streamlit dashboard with hard-coded fake footprint bars ("RAM ~350 MB", "CPU idle ~1.2 %"), a text-box "simulation" computing savings from string length, faster-whisper tiny (offline) or Google SpeechRecognition (online), pyttsx3 / gTTS, and a ~40-word dictionary "translator".
- **Pipeline & stack**: STT = faster-whisper tiny int8 or Google Web Speech API. TTS = pyttsx3 (system) or gTTS (cloud). Translation = word dictionary. Compression = none (byte count only). Transport = none (`link_sim.py` computes a percentage). Platform = Python/Streamlit.
- **Genuinely good features/ideas**: none beyond a dashboard mock-up.
- **Measured numbers claimed**: fabricated progress bars; "savings %" from string length.
- **Maturity**: 1.5.
- **Weaknesses**: Everything is mocked or cloud.
- **Threat to us**: None.

---
## Group 4

# SIH26173 competitor cards — group 4 (19 repos)

Method: GitHub tree API + raw file reads only (no clones). "Claimed" = README; "implemented" = seen in source.

---

## 1. Cmcyooo/iTantra
- **Repo**: Cmcyooo/iTantra, Kotlin, 142 MB, pushed 2026-09-09, ~25 commits (models in git as LFS pointers, release APK v1.0.0 published)
- **What it is**: Real, heavily-tested native Android walkie-talkie with modular downloadable language packs (10 langs), per-language on-device STT/TTS, Silero VAD, auto language-ID, three transports, and a zero-config emergency flow. README matches code; large instrumented-test + benchmark corpus in repo.
- **Pipeline & stack**: STT = Vakyansh wav2vec2-base INT8 ONNX per language via generic ONNX Runtime CTC greedy decoder (`GenericOnnxCtcSttEngine`), Whisper-tiny INT8 via sherpa-onnx for English; TTS = sherpa-onnx VITS (Piper/MMS per language); LID = sherpa-onnx `SpokenLanguageIdentification` on Whisper-tiny; VAD = Silero v4 ONNX; no translation; encoding = kotlinx JSON newline-delimited (`P2PMessage` with UUID, timestamp, text, priority) — no compression; transports = Wi-Fi NSD/TCP, Wi-Fi Direct, Bluetooth RFCOMM; platform = native Kotlin/Compose; fully offline after pack download (packs from GitHub Release or ZIP import).
- **Genuinely good features/ideas**:
  - Modular language packs: base APK ~96 MB + per-language STT/TTS pack download or offline ZIP import (`LanguagePackManager`, `LanguagePackManagementDialog`)
  - Single-active-model memory policy (unload previous language before loading next)
  - Spoken language auto-detect (sherpa Whisper-tiny SLID) with `LanguageReliabilityPolicy` + `LanguageSafetyRoutingTest`
  - Zero-config emergency flow: state machine SEARCHING→CONNECTING→SENDING→WAITING_FOR_ACK→DELIVERED with ACK watchdog + retries + auto transport switch
  - ALERT/HIGH priority message type with alarm-stream playback (`AlertPlaybackManager`)
  - Silero VAD with ~320 ms pre-speech buffer
  - Very large instrumented benchmark suite (per-language FLEURS benchmark tests, TTS benchmark, networking payload benchmark, reliability stress test, LID benchmark, device profiler) with markdown reports per language
  - `IndicDomainNormalizer` for domain text normalisation
- **Measured numbers claimed** (backed by instrumented-test reports in `benchmarks/indic_stt/*_android_validation.md`, Samsung S24, 12 FLEURS samples/lang, on-device): Hindi WER 17.35 / CER 5.41; Gujarati 31.06 / 8.61; Telugu 34.34 / 6.67; Kannada 38.34 / 8.35; Tamil 50.00 / 25.68; Bengali 54.27 / 15.25; Malayalam 52.84 / 13.84; Marathi 61.58 / 20.22; Odia 78.54 / 24.08. RTF 0.15–0.32 on 2 threads; Hindi model load 502 ms; peak PSS 884 MB; VAD 12.4 ms/32 ms chunk; E2E latency 620–800 ms. Payload benchmark computes text bytes vs raw PCM (no compression, JSON packet). 4 GB/6 GB device tiers "Pending".
- **Maturity**: 5 — end-to-end over 3 transports + published APK + on-device benchmark evidence for all 10 languages.
- **Weaknesses**: No text compression (JSON with UUID ~150+ B/msg); Vakyansh CER is 2–5× worse than our IndicConformer numbers (Tamil 25.7 vs our 13.9, Hindi 5.4 vs 2.9); needs 884 MB PSS (fails their own 4 GB tier so far); no encryption; no mesh/relay; no radio/LoRa/AFSK; no translation; STT models are 117 MB each.
- **Threat to us**: **High** — the most rigorous eval story in the group (per-language on-device reports, published release, language-pack UX, auto-LID, emergency ACK flow). A jury would rate its engineering rigor and UX above ours; we beat it on accuracy, bytes-on-wire, and radio/hardware links.

---

## 2. Precise-Goals/iTantra-Communication-Ecosystem
- **Repo**: Precise-Goals/iTantra-Communication-Ecosystem, Kotlin, 73 MB, pushed 2026-09-07, ~58 commits
- **What it is**: Substantial native Android app: IndicConformer STT (9 langs), VITS TTS (5 langs), Wi-Fi Direct + BT RFCOMM, protobuf wire format, resumable SHA-256-verified model downloads, plus an on-device Phi-3 "tactical assistant". README is detailed and mostly honest (claims two-device verification; roadmap admits gaps).
- **Pipeline & stack**: STT = AI4Bharat IndicConformer INT8 ONNX (per-language export, hand-rolled 80-bin log-mel + pure-Kotlin CTC greedy decoder, ONNX Runtime 1.18); TTS = sherpa-onnx VITS (Piper hi/ml/en, Mimic3 gu, Coqui bn); VAD = adaptive energy (Silero bundled but not active); translation = none (dst_lang field only); encoding = protobuf-javalite `TransceiverMessage` with 4-byte length prefix (~50–300 B claimed) — no text compression; transports = Wi-Fi Direct (TCP :8765) primary, BT RFCOMM fallback; LLM = Phi-3-mini GGUF q4 via llama.cpp (optional 2.4 GB) + keyword fallback; platform = native Kotlin/Compose, foreground service; offline after model download (OkHttp from HF/GitHub).
- **Genuinely good features/ideas**:
  - Protobuf wire schema with SPEECH/ALERT/ACK/PING types, sequence number, confidence
  - Resumable, SHA-256-verified model download manager with `.part` resume + tar.bz2 extraction; 23-pack model catalog
  - Peer authorization whitelist persisted in Room
  - Ping/ACK RTT loop every 5 s feeding a "Radar" peer screen
  - ALERT playback on STREAM_ALARM at max volume + DND-bypass attempt
  - On-device LLM tactical assistant (first-aid/disaster Q&A) with keyword fallback across 9 languages
  - Unicode-script + keyword language detector (Hindi/Marathi disambiguation, romanised "Hinglish" match)
  - `validate_wer.py` script (INT8 vs FP32 regression gate) — script exists, no results committed
- **Measured numbers claimed**: "~50–300 bytes" per message (protobuf; plausible, not benchmarked). No WER/CER/latency numbers anywhere. `validate_wer.py` defines targets (Hindi WER <8%) but no results.
- **Maturity**: 4 — README asserts two-device end-to-end verification over Wi-Fi Direct/BT; code supports it; no eval evidence.
- **Weaknesses**: No compression beyond protobuf; no encryption; TTS only 5/10 languages; energy VAD; heavy (Phi-3 is a gimmick for the PS); no tests beyond 4 small unit tests; no measured accuracy.
- **Threat to us**: **Med-High** — same STT model family as ours, polished app with model-download UX, protobuf framing and an "AI assistant" that juries like. We beat it on bytes/msg, eval evidence, radio links, encryption.

---

## 3. naitik2424/iTantra
- **Repo**: naitik2424/iTantra, Kotlin, 153 MB (100 MB Dolphin ONNX committed), pushed 2026-09-02, 1 commit ("Add iTantra project")
- **What it is**: Single-drop native Android app with a real sherpa-onnx STT/TTS loop, Bluetooth RFCOMM, a multi-hop flood mesh relay layer with AES-256-GCM "rooms". No README; `context.md` describes transport/security accurately vs code.
- **Pipeline & stack**: STT = sherpa-onnx `OfflineDolphinModelConfig` (DataoceanAI Dolphin int8 multilingual CTC, 104 MB); TTS = sherpa-onnx VITS Piper `hi_IN-priyamvada-medium` only; no VAD, no translation; encoding = JSON envelopes with UUID packetId/envelopeId, newline-delimited (`MessageSerializer`) — no compression; transports = Bluetooth RFCOMM only (multi-client server + client), mesh flood over RFCOMM links; platform = native Kotlin/Compose; fully offline.
- **Genuinely good features/ideas**:
  - Multi-hop mesh relay (`MeshRelay`): TTL=5, hopCount, seenNodeIds loop prevention, seenPacketIds dedup, forward-to-all-except-source; 3-node A→B→C simulated in unit tests (`MeshMultiHopRoutingTest`)
  - Encrypted "rooms": PBKDF2-SHA256 (10k iters, 16 B salt) → AES-256-GCM per room; relays forward ciphertext without the key (zero-trust relay); room announce packets
  - Bluetooth server accepting multiple concurrent clients (`BluetoothManager` map of links)
  - DATA/ACK protocol envelope
  - 7 JUnit test files for crypto/room/mesh
- **Measured numbers claimed**: none.
- **Maturity**: 3 — single-device pipeline plausible, mesh only proven in JVM tests; one commit, no evidence of two-phone run.
- **Weaknesses**: JSON+UUID envelopes (~300 B/msg, mesh header adds more); Dolphin model accuracy on Indic unknown (no eval); Hindi-only TTS; BT-only; no VAD; 100 MB model in git; single commit dump.
- **Threat to us**: **Med** — a working multi-hop encrypted mesh is a headline feature we lack; otherwise thin.

---

## 4. Sanchit-044/iTantra
- **Repo**: Sanchit-044/iTantra, Kotlin, 3.5 MB, pushed 2026-09-10, ~76 commits (multi-author, PRs)
- **What it is**: Well-architected core/android/app split (133 core unit tests claimed) with Compose UI (Talk/Alert/Analysis/Radar), ECDH+AES-GCM packets, floor control, store-and-forward queue, dictionary translation. README is stale (says "no UI"); `.cursor/PROJECT.md` is the accurate brief. **No ONNX weights in git**; TTS currently falls back to Android system TextToSpeech.
- **Pipeline & stack**: STT = IndicWav2Vec CTC on ONNX Runtime (`OnnxCtcSttEngine`, own 800 ms `SilenceEndpointer`, partials every 600 ms) — weights must be copied/downloaded; TTS = `VitsOnnxTtsEngine` intended (Indic-TTS VITS), **Android `TextToSpeech` used at runtime when ONNX absent**; LID = script-based `ScriptLanguageId`; translation = `DictionaryTranslationEngine` phrase table (IndicTrans2 ONNX planned, not present); encoding = binary packet: 16 B header (ver/type/lang/flags/seq/ts) as GCM AAD + 12 B nonce + 4 B len + ciphertext (~48 B overhead) — no text compression; transports = Wi-Fi Direct, BT RFCOMM, LAN, plus BLE/Wi-Fi alert broadcast + BLE radar scan; crypto = ECDH P-256 (Keystore) → HKDF → AES-256-GCM with 6-digit SAS pairing; platform = native Kotlin/Compose/Hilt; offline (INTERNET only for optional pack download).
- **Genuinely good features/ideas**:
  - ECDH key agreement + AES-GCM with header as AAD (alert-flag tamper detection tested) and 6-digit pairing code confirmation
  - Floor control (FLOOR_REQUEST/GRANT/DENY/RELEASE) — half-duplex PTT arbitration, host wins ties
  - `ChannelArbiter`: alerts jump the send queue
  - Store-and-forward: `OutboundMessageQueue` with TTL when disconnected, `FlushQueuedMessagesUseCase` sends QUEUED (0x09) on reconnect; receiver inbox with Play/Dismiss (no autoplay)
  - Receiver-side translation into listener's language (phrase table now; IndicTrans2 hook)
  - BLE advertise/scan "Radar" proximity plot from RSSI bands; alert broadcast over BLE + Wi-Fi to unpaired nearby phones
  - TTS text normalisation: Indic number lexicon (lakh/crore), abbreviation lexicon, clause chunking on danda, pipelined chunked speaking (starts playback before last chunk synthesised)
  - Operator profile exchange packet (name + tiny JPEG)
  - WER/CER scoring harness (`Wer.kt`, `SttEvaluationHarness`) and diagnostics snapshot screen — explicitly reports `null` for unmeasured values
  - `docs/MEASUREMENTS.md`: honest "nothing has been measured"
- **Measured numbers claimed**: none — repo explicitly states no figures are measurements.
- **Maturity**: 3 — rich logic layer with unit tests; models absent, TTS via system engine; two-phone run not evidenced.
- **Weaknesses**: No models shipped; system TTS fallback violates open-source-only constraint; 48 B packet overhead per message; translation is a demo phrase table; no eval numbers; single-peer only (no mesh by design).
- **Threat to us**: **Med** — strongest security/protocol design in group (ECDH pairing, floor control, store-and-forward, AAD-authenticated alert flag) and honest docs; but no models, no numbers, no radio.

---

## 5. vishallr821/iTantra
- **Repo**: vishallr821/iTantra, Kotlin, 8.7 MB, pushed 2026-09-12, ~3 commits (+ large `pushed_models/` incl. 17 MB tokenizer)
- **What it is**: Native Android prototype with Whisper-tiny STT, Piper/VITS TTS, a bit-packed "Mode 1 semantic / Mode 2 text" packet protocol with CRC16 + XOR FEC, a link emulator, and a MiniLM-embedding intent classifier verified on one phone. `PROJECT_CONTEXT.md` honestly separates "code present" vs "verified on hardware".
- **Pipeline & stack**: STT = sherpa-onnx Whisper-tiny (en/hi/ta packs); TTS = sherpa-onnx Piper (en Amy) / VITS Rasa (hi/ta); VAD = own `VadManager`; intent = `paraphrase-multilingual-MiniLM-L12-v2` quantized ONNX (118 MB) + pure-Kotlin SentencePiece tokenizer + keyword fast-path; no translation; encoding = custom binary: magic + control byte (mode/loc flag/4-bit lang) + 16-bit seq + len + optional location (2 B index or 8 B lat/lon) + payload (Mode 1 = 16-bit packed intent, Mode 2 = UTF-8) + CRC16; XOR-parity FEC blocks; transports = Wi-Fi Direct sockets (code present, unverified OTA), loopback link emulator; platform = native Kotlin (XML layouts); offline.
- **Genuinely good features/ideas**:
  - Mode 1 semantic packets: 16-bit intent payload (8 emergency categories) when classifier confidence ≥ 0.65, else Mode 2 free text — "10 bits vs ~400 bits" HUD
  - On-device sentence-embedding intent classifier with contrastive softmax margin confidence; 24/24 on-device test matrix across en/hi/ta
  - Location field in packet (grid index 2 B or float lat/lon 8 B)
  - XOR-parity FEC (`FecEngine`, `FecPacketWrapper`) with unit tests
  - Link emulator: bitrate throttle 20–1000 bps, packet loss %, bit corruption, FEC parity sweep — runs test matrix in-app
  - Live engineering metrics HUD (payload bits, STT/TTS latency, FEC state)
  - Language pack switching (en/hi/ta, ~2.5 s)
- **Measured numbers claimed** (from `PROJECT_CONTEXT.md`, single vivo 1920 device, logged): ASR load 1.3 s (en) / ~3 s (hi/ta); TTS load ~1.25 s; pack switch 2.58 s; embedding inference ~25 ms; intent routing 24/24 correct; Mode 1 = 10 bits semantic vs ~400 bits text; APK 136 MB. No WER/CER. Two-phone latency and FEC delivery explicitly "NOT YET MEASURED".
- **Maturity**: 3 — single-device loop + classifier verified on hardware; transport unverified over the air.
- **Weaknesses**: Whisper-tiny for Hindi/Tamil (known ~100%+ WER on Indic per other repos' benchmarks); 3 languages only; Wi-Fi Direct never tested between phones; 118 MB classifier for a 16-bit output; no encryption.
- **Threat to us**: **Med** — the semantic-intent Mode 1 + link emulator + FEC story is a compelling "low-bitrate" narrative that beats our 45 B/sentence on the slide; accuracy and transports are far behind.

---

## 6. sarancode-bits/itantra
- **Repo**: sarancode-bits/itantra, Kotlin, 979 KB, pushed 2026-09-09, ~31 commits
- **What it is**: Native Android app (Hilt/Room/Compose) with Whisper-tiny STT + Piper TTS in an isolated `:ai_engine` AIDL process, Google Nearby Connections transport, hands-free VAD mode, SOS override. Models not in git (`TTS_MODELS_TODO.md` asks for downloads that mostly don't exist for Indic Piper).
- **Pipeline & stack**: STT = sherpa-onnx Whisper-tiny INT8 (one model, language hint); TTS = sherpa-onnx Piper VITS per language (only en bundled; others "TODO"); VAD = energy-based; no translation; encoding = JSON payload — no compression; transports = Nearby Connections `P2P_CLUSTER` (BT + Wi-Fi Direct via Play Services), mock flavor for demo; platform = native Kotlin; offline at runtime but needs Google Play Services.
- **Genuinely good features/ideas**:
  - STT/TTS run in a separate `:ai_engine` process over AIDL (UI never blocks; native crash isolation)
  - Hands-free VAD walkie mode (auto-segment on pause)
  - SOS override: max-volume siren on STREAM_ALARM + vibration + camera flashlight strobe
  - Latency/RTF developer overlay persisted in Room
  - `mock`/`prod` Gradle flavors with Hilt module swap for single-device demo
  - `flaws.md`: candid analysis of range/relay/battery/panic UX gaps
- **Measured numbers claimed**: "~165 MB models in APK"; RTF overlay exists; no figures published.
- **Maturity**: 3–4 — two-phone Nearby transport is realistic and simple; models incomplete for 9/10 languages.
- **Weaknesses**: Whisper-tiny on Indic; Nearby Connections = Google Play Services dependency (not open-source, not AOSP); JSON on wire; no encryption; Indic TTS voices missing.
- **Threat to us**: **Low-Med** — clean app and SOS UX, but weak STT and proprietary transport.

---

## 7. Vishal-4356/iTantra-App
- **Repo**: Vishal-4356/iTantra-App, Dart/Flutter, 19 MB, pushed 2026-09-13, 1 commit
- **What it is**: Flutter app whose AI layer is **simulated**: `tool/setup_models.dart` writes random bytes with a fake ONNX header as "quantized models"; the isolate never calls sherpa-onnx — it does RMS energy "VAD", then keyword-matches a caller-supplied transcript or picks intent 9 (SOS) if loud. Real code exists for packet encoding, XOR FEC, CRC32, ML Kit translation, and a Nearby/UDP/HTTP/BLE network manager.
- **Pipeline & stack**: STT = none real (sherpa_onnx dep declared, unused); TTS = Piper JSON configs only, no weights; translation = Google ML Kit on-device translator (`google_mlkit_translation`, downloads models); encoding = msgpack + custom 4-byte Mode 1 semantic packet (4-bit lang, 12-bit intent, 2-bit priority, 6-bit seq) / Mode 2 text / Mode 3 raw WAV; CRC32; XOR FEC frames; transports = `nearby_connections` P2P_STAR, UDP broadcast, embedded HTTP server, `flutter_blue_plus` BLE fallback; platform = Flutter; 10 locale JSONs.
- **Genuinely good features/ideas**:
  - 4-byte Mode 1 semantic packet layout (lang/intent/priority/seq) — cleanly specified and unit-tested (`protocol_and_fec_test.dart`)
  - XOR parity FEC block framing with magic byte, tested
  - 4-level priority incl. sosCritical
  - ML Kit translation wrapper with pre-warm download
  - Multi-transport fallback chain (Wi-Fi Direct → UDP → HTTP → BLE)
  - UI localisation in 10 Indian languages
- **Measured numbers claimed**: none.
- **Maturity**: 2 — UI + protocol skeleton; no speech models; STT faked.
- **Weaknesses**: Fake models and fake inference; ML Kit is proprietary; single commit.
- **Threat to us**: **Low** — demo would be exposed on first question about the STT model.

---

## 8. Kaustavmp/iTantra
- **Repo**: Kaustavmp/iTantra, Kotlin + Python, 98 KB, pushed 2026-09-12, ~3 commits
- **What it is**: Android scaffold where `SttEngine.transcribe()` **sleeps 350 ms and returns canned Hindi/English strings** based on RMS; TTS = Android system `TextToSpeech`; JSON `SemanticPacket` over a local TCP socket. Python side has a Whisper/Vosk benchmark script and a keyword urgency detector. README shows "Avg WER 4.2%" as sample output — not a measurement.
- **Pipeline & stack**: STT = simulated (Whisper-tiny/Vosk mentioned, not wired); TTS = Android system TextToSpeech; urgency = keyword list (`UrgencyDetector`); encoding = JSON ~120–180 B; transport = plain TCP `LocalSocketTransport` on shared Wi-Fi; platform = native Kotlin/Compose; Python `benchmark_stt.py`, `packet_validator.py` (JSON schema).
- **Genuinely good features/ideas**:
  - Keyword urgency detector (Hindi+English) → HIGH flag → receiver alarm + vibrate
  - Metrics screen (latency, bytes, WER counter) concept
  - Test sentence set with ground-truth transcripts for WER
- **Measured numbers claimed**: "~150 bytes packet", "Avg WER 4.2%" — illustrative README text, no evidence.
- **Maturity**: 2 — UI + transport skeleton with fake STT.
- **Weaknesses**: No real STT; system TTS; JSON; TCP on infrastructure Wi-Fi only.
- **Threat to us**: Low.

---

## 9. LingeshSuriya/iTantra---SIH-2026
- **Repo**: LingeshSuriya/iTantra---SIH-2026, Kotlin, 2 MB, pushed 2026-09-14, 1 commit
- **What it is**: Self-described "Scaffold · Mock Build": Wi-Fi Direct TCP transport + Silero VAD are real; `MockSttEngine` emits `[sim-stt segment #n]`, `MockTtsEngine` = Android TextToSpeech, `MockTranslationEngine`. Interfaces ready for model swap.
- **Pipeline & stack**: STT = mock (real Silero VAD ONNX + segmenter); TTS = Android system TTS; translation = mock; encoding = `Payload` JSON with timestamp chain; transports = Wi-Fi Direct TCP (`WifiDirectSocketTransport` 19 KB, real), Bluetooth stub; platform = native Kotlin/Compose; model download manager stub.
- **Genuinely good features/ideas**:
  - Latency debug card driven by a payload timestamp chain (Δ network, Δ TTS start)
  - Floor state (PTT vs "Phone" continuous VAD mode)
  - Alert with max volume + exclusive audio focus
- **Measured numbers claimed**: none.
- **Maturity**: 2 — honest scaffold.
- **Weaknesses**: No STT/TTS models; single commit.
- **Threat to us**: Low.

---

## 10. HarikrishnaD1905/iTantra_Android_App
- **Repo**: HarikrishnaD1905/iTantra_Android_App, Kotlin, 592 KB, pushed 2026-09-10, ~3 commits
- **What it is**: LAN UDP-broadcast text chat with sherpa-onnx Piper English TTS reading incoming messages. No STT.
- **Pipeline & stack**: STT = none; TTS = sherpa-onnx Piper `en_US-amy-medium`; encoding = raw UTF-8 UDP datagrams on port 8888; transport = UDP broadcast on same Wi-Fi subnet; platform = native Kotlin/Compose.
- **Genuinely good features/ideas**: 16 KB page-size compatible sherpa .so build note; TTS queue via coroutine channel. That's it.
- **Measured numbers claimed**: none.
- **Maturity**: 2.
- **Weaknesses**: No STT, English only, needs infrastructure Wi-Fi.
- **Threat to us**: Low.

---

## 11. Siddharthrk17/iTantra--Indian-Multilingual-…
- **Repo**: Siddharthrk17/iTantra--…-low-bitrate-links, Kotlin, 125 KB, branch master, pushed 2026-09-07, 1 commit, no README
- **What it is**: Android app using **Google `SpeechRecognizer`** (system, with `EXTRA_PREFER_OFFLINE`) for STT, Android system TTS, **Google ML Kit** language-ID + translation, protobuf envelope, Nearby Connections + Wi-Fi Direct + BLE transports, Room message store.
- **Pipeline & stack**: STT = Android system SpeechRecognizer (Google); TTS = Android TextToSpeech; translation = ML Kit on-device; encoding = protobuf `ITantraEnvelope` (string timestamps, ack_required) + `ITantraAck`; transports = Play Services Nearby, Wi-Fi Direct sockets, BLE GATT (`BleTransport`); platform = native Kotlin/Compose; Vosk dependency declared, not used.
- **Genuinely good features/ideas**:
  - Cross-language flow: ML Kit language-ID → translate to target_language before TTS
  - ACK protocol with DELIVERED/FAILED
  - Three transports incl. BLE GATT
  - Room persistence of messages + nodes
- **Measured numbers claimed**: none.
- **Maturity**: 3 — plausible working loop on system engines; no evidence.
- **Weaknesses**: Entirely proprietary Google speech/translation stack (violates open-source/offline spirit; Indic offline packs vary by OEM); no compression; no README; no tests.
- **Threat to us**: Low — translation demo may impress, but the stack is disqualifying under the PS constraints.

---

## 12. snairmeenakshy/SIH26173_iTantra_offline
- **Repo**: snairmeenakshy/SIH26173_iTantra_offline, Kotlin, 74 KB, pushed 2026-09-11, ~4 commits
- **What it is**: Compose walkie-talkie UI on Android system SpeechRecognizer (on-device recognizer on API 31+) and system TTS; `P2PTransportManager` is a **stub** (hard-coded `connectedDeviceName = "Redmi 12"`, state CONNECTED, no sockets). Priority queue for SOS is in-memory only.
- **Pipeline & stack**: STT = Android SpeechRecognizer; TTS = Android TextToSpeech; VAD = own `VadDetector`; "dialect-aware" and "speech reconstruction" engines are thin wrappers; encoding = in-memory `SpeechPacket` data class (includes optional raw PCM); transport = none real; platform = native Kotlin/Compose.
- **Genuinely good features/ideas**: 4-level priority enum with SOS preemption concept; emergency alert controller. Nothing else implemented.
- **Measured numbers claimed**: `rtfScore = 0.18f` hard-coded default — fake.
- **Maturity**: 2 (UI only; single device with system engines).
- **Weaknesses**: No transport, proprietary engines, fabricated metric field.
- **Threat to us**: Low.

---

## 13. akkinenisvabhu-web/itantra_devise
- **Repo**: akkinenisvabhu-web/itantra_devise, TypeScript + Kotlin + Python, 46 MB (committed `.next` build), pushed 2026-08-27, ~3 commits
- **What it is**: Three half-projects: (a) Android Kotlin app with sherpa-onnx streaming Zipformer **English** STT + Piper en_US-amy TTS + BT SPP + `[1B type][2B len]` framing + 300 bps throttle (README status table: STT/TTS/BT all "Further Testing Required"); (b) Next.js web demo using browser Web Speech API + `speechSynthesis` over a Node WebSocket relay; (c) FastAPI backend with faster-whisper + pyttsx3 + throttle tests.
- **Pipeline & stack**: Android STT = sherpa-onnx streaming Zipformer en; TTS = Piper en; transport = BT RFCOMM; encoding = custom binary type/len/payload; web = Web Speech API (cloud), WebSocket relay; backend = faster-whisper. No Indic models anywhere.
- **Genuinely good features/ideas**:
  - `ChannelThrottle` 300 bps channel simulation (Android + backend token bucket) with fairness tests
  - Compact binary framing `[type][len16][payload]`
  - Honest implementation-status table
- **Measured numbers claimed**: "78,336 bytes captured in runtime test"; "20–60 bytes per 3 s utterance" (estimate). No accuracy numbers.
- **Maturity**: 2 — Android loop unverified; web demo works via cloud APIs.
- **Weaknesses**: English-only models; cloud Web Speech in demo; committed build artefacts; abandoned since Aug 27.
- **Threat to us**: Low.

---

## 14. anumitha21/Itantra-Models-bt
- **Repo**: anumitha21/Itantra-Models-bt, Python, 30 MB (Kathbath transcripts committed), pushed 2026-09-12, ~14 commits
- **What it is**: Desktop Python STT/TTS benchmarking harness (no app, no transport): compares IndicConformer (sherpa-onnx INT8) vs Whisper tiny/small (CTranslate2) vs Meta MMS on Kathbath clean/noisy for hi/ta/te; TTS round-trip intelligibility (AI4Bharat VITS vs MMS-TTS judged by IndicConformer); Streamlit dashboard with manual MOS.
- **Pipeline & stack**: STT engines = sherpa-onnx IndicConformer INT8, faster-whisper, transformers MMS; TTS = AI4Bharat Indic-TTS VITS, MMS-TTS VITS; VAD = stub; no transport, no compression, no Android; Python + Streamlit.
- **Genuinely good features/ideas**:
  - Deterministic Kathbath clean+noisy manifest sampling (`dataset/manifest.py`)
  - Matrix benchmark runner (models × langs × conditions) → CSV with WER/CER/RTF/RAM/model size/composite score
  - TTS round-trip WER (synthesise → ASR judge) as automated intelligibility proxy, plus manual MOS CSV
  - Single-model RAM discipline in `ModelManager`
- **Measured numbers claimed** (backed by `results/results.csv`, 10 samples/condition, CPU 2 threads): IndicConformer INT8 — hi WER 11.1% / CER 2.5% clean, 12.5 / 4.0 noisy; ta 28.6 / 4.7 clean, 28.6 / 5.3 noisy; te 20.5 / 3.9 clean, 19.0 / 2.8 noisy; RTF ~0.06; RAM ~1.05 GB; model 188 MB. Whisper-tiny hi WER 98%, CER 85%; Whisper-small hi WER 62%.
- **Maturity**: 3 (eval pipeline works; not a transceiver).
- **Weaknesses**: No app, no transport, no compression; it is a component study only.
- **Threat to us**: **Low-Med** — not a competitor product, but its Kathbath clean/noisy and Whisper-vs-IndicConformer comparison is the kind of table a jury asks for; our FLEURS CER numbers are consistent with theirs (hi 2.9 vs 2.5), which is reassuring.

---

## 15. anuow/itantra
- **Repo**: anuow/itantra, Flutter + Python, 290 KB, pushed 2026-09-09, ~3 commits ("idk i just did it")
- **What it is**: Default Flutter template with a `record` mic widget, plus Python `stt_benchmark.py` (IndicConformer-600M via HF transformers, jiwer WER on hi/bn/ta Vistaar samples) and `tts_benchmark.py`; 30 transcript .txt per language committed (WAVs not).
- **Pipeline & stack**: Python-only STT eval (torch IndicConformer); no TTS/transport in app; Flutter skeleton.
- **Genuinely good features/ideas**: Vistaar dataset download script; per-language RTF/WER loop. Nothing in-app.
- **Measured numbers claimed**: none committed.
- **Maturity**: 1.
- **Weaknesses**: Empty app.
- **Threat to us**: Low.

---

## 16. DakshG26/itantra-web
- **Repo**: DakshG26/itantra-web, JavaScript + Python, 180 KB, pushed 2026-09-02, ~7 commits (Android app in a separate repo `itantra-android`, not in this list)
- **What it is**: React/Vite web demo (PeerJS WebRTC data channel between browsers) + FastAPI backend: faster-whisper STT, **Bhashini ULCA API** / pyttsx3 TTS, zlib/LZ4 "compressor", token-bucket bitrate throttle with BER injection. README's "18-byte neural tokenizer, 2,666×, 369 ms" is marketing; compressor is stdlib zlib best-of.
- **Pipeline & stack**: STT = faster-whisper tiny (server); TTS = Bhashini cloud API (default) or pyttsx3; compression = best-of zlib-9 / lz4 / raw; transport = WebRTC PeerJS (needs signalling server) + `laptop_transceiver.py` adb-forward bridge; radio = software throttle (bps + BER); platform = web + Python server.
- **Genuinely good features/ideas**:
  - Token-bucket bitrate throttle with bit-error injection (`radio_link/throttle.py`) for live demo of 24–2400 bps
  - Metrics dashboard comparing bits vs audio codecs
  - Google-Stitch-designed 4-screen UI
- **Measured numbers claimed**: "18-byte packet", "2,666×", "369 ms" — no script produces these; zlib on a short Indic sentence cannot reach 18 B.
- **Maturity**: 2 (web demo works with cloud backend).
- **Weaknesses**: Cloud STT/TTS (Bhashini), server-based, claims unbacked.
- **Threat to us**: Low (slick demo, hollow).

---

## 17. Spirit019/itantra-isro-web
- **Repo**: Spirit019/itantra-isro-web, JavaScript, 140 KB, pushed 2026-09-01, ~9 commits
- **What it is**: Browser-only "transceiver simulator" (73 KB `App.jsx`): canned Indic samples, browser `SpeechRecognition`/`speechSynthesis`, an 18-byte hex "inspector", LoRa time-on-air sliders, radar canvas, fake NavIC SOS. `scripts/pipeline_runner.py` = `simulate_compression()` with struct packing. Model manifest JSON but no models.
- **Pipeline & stack**: STT/TTS = Web Speech API (cloud); compression = simulated; transport = none (same-page nodes); platform = web.
- **Genuinely good features/ideas**:
  - Packet hex inspector UI (header / lang / priority / speaker-embedding / payload / RS+CRC bytes) — as a visualisation idea
  - LoRa link budget calculator: distance, SF7–SF12, ToA
  - Hardware tier table (BLE / HC-12 433 MHz / SX1262) as a pitch
- **Measured numbers claimed**: "369 ms latency budget", "24 bps", "2,666×" — pure design targets, nothing measured.
- **Maturity**: 1–2 (landing/simulator).
- **Weaknesses**: Nothing real.
- **Threat to us**: Low — but their polished packet-inspector and LoRa-ToA visuals are worth stealing for our demo.

---

## 18. vaibhavbutul-work/iTantra
- **Repo**: vaibhavbutul-work/iTantra, TypeScript, 42 KB, pushed 2026-09-06, 1 commit, no README
- **What it is**: React/Tailwind UI mock (PTT button, radar, packet-flow animation, telemetry panel) driven by a Zustand store with `setTimeout`-scripted fake events. No speech, no network.
- **Pipeline & stack**: none; web mock.
- **Genuinely good features/ideas**: Packet-flow animation and diagnostic drawer as UI references only.
- **Measured numbers claimed**: none.
- **Maturity**: 1.
- **Weaknesses**: Pure mock.
- **Threat to us**: Low.

---

## 19. xarjunpatil/SIH26173-iTantra-…
- **Repo**: xarjunpatil/SIH26173-iTantra-Indian-Multilingual-TTS-STT-Aided-Neural-Transceiver-Radio, HTML + Python, 25 KB, pushed 2026-08-31, 1 commit
- **What it is**: Auto-generated generic SIH template (badge says "Acoustic Deepfake & Voice Shield"): FastAPI with `/telemetry/ingest`, `/audit/logs`, `/action/dispatch` endpoints and a glassmorphic Chart.js dashboard. Nothing related to STT/TTS/radio.
- **Pipeline & stack**: none relevant.
- **Genuinely good features/ideas**: none.
- **Measured numbers claimed**: none.
- **Maturity**: 1.
- **Weaknesses**: Template.
- **Threat to us**: Low.

