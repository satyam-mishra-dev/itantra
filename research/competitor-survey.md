# Competitor survey — every public SIH26173 "iTantra" repo vs. ours

_Surveyed 2026-09-15. 83 repos found via GitHub search ("itantra", "SIH26173", variants); 76 non-empty ones read (README + file tree + 2–5 key source files each, via API — no clones). Per-repo evidence cards: `competitor-cards.md`. Everything below distinguishes what a repo's code does from what its README claims._

## 1. The field at a glance

| Maturity | Count | What that looks like |
|---|---|---|
| 1 — empty / template / landing page | 22 | Hello-World Android template, README-only, marketing site with "100% offline" badges on a cloud backend |
| 2 — skeleton / UI only / faked engine | 39 | Compose screens, `sleep(); return "canned text"` STT, random-bytes ".onnx" files, Google SpeechRecognizer + system TTS behind an "AI" label |
| 3 — single-device pipeline works | 34 | Real sherpa-onnx / Vosk / Whisper + Piper, one phone or Python only |
| 4 — two devices end-to-end | 12 | Logged phone↔phone or emulator↔emulator run |
| 5 — e2e + hardware / eval evidence | 4 | Committed benchmark reports or firmware |

(Counts include a few decimals the agents used; ~55% of the field is ≤2.)

Threat to us: **4 High**, ~15 Med, ~57 Low. Named below.

**Stack consensus in the field:** sherpa-onnx is the de-facto runtime (≈20 repos). STT splits between IndicConformer (≈6, same as us), Omnilingual-300M (2), Vakyansh wav2vec2 (1), Dolphin (3), Whisper tiny/base (≈6), Vosk (≈4), Google/Bhashini cloud (≈10). TTS: Piper (≈10), MMS-TTS (3 — CC-BY-NC, they don't notice), FastPitch/HiFi-GAN (3), Android system TTS (≈15). Wire format: JSON (≈25), raw UTF-8 (≈8), protobuf (2), custom binary with CRC (≈6). **Nobody entropy-codes text.** Transports: Wi-Fi TCP (most), BT RFCOMM (≈15), BLE GATT (≈6), Wi-Fi Direct (≈6), Nearby Connections (≈5), ESP32 SPP (1), LoRa (0 in code — several in slides), acoustic modem (1: ggwave), AFSK (0).

## 2. Where we are ahead — and by how much

| Axis | Ours | Best rival | Gap |
|---|---|---|---|
| Bytes per spoken sentence | **45 B** (VarnaCode 4.45–5.41 b/char, beats Unishox2/SCSU head-to-head) | Niranjan266: 62 B for a 49-char *English* sentence, raw UTF-8; Precise-Goals protobuf "50–300 B"; everyone else JSON 100–400 B | Only entropy-coded text in the field. On Indic scripts (3 B/char UTF-8) rivals are 4–6× our size. |
| STT accuracy (real speech) | Hindi CER **2.9%** (FLEURS), bn 4.0, te 7.8 | Cmcyooo on-device: hi 5.4 / bn 15.3 / ta 25.7; lector-sys & rishikafrfr: hi 13.0 (Omnilingual); anumitha21's Kathbath run of IndicConformer (hi CER 2.5) independently corroborates ours | 2–5× better CER than any rival that measured |
| Analog-radio path | AFSK Bell-202, frame = 0.3 s audio, works at 6 dB SNR | Musa2609: ggwave (third-party lib, laptops only) | Unique |
| LoRa | ESP32+SX127x IN865 firmware, duty-cycle guard, 127 parity cases vs Python | lector-sys: ESP32 BluetoothSerial receiver with OLED (no radio) | Unique in code; ~10 repos only have LoRa on a slide |
| Disaster-alert ingestion | CAP/SACHET XML → spoken ALERT | none | Unique |
| Encryption | AES-128-GCM frames, Python↔Kotlin vectors | NihalMishra / Barath410 / Sanchit-044 / naitik2424 have ECDH designs (see gap I) | Ours ships; theirs mostly don't compile — but their *design* is better |
| Languages measured | 10 codec, 5 real-speech CER | Cmcyooo 9 on-device; lector-sys 5 emulator; most: 1–2 | Ahead |
| Evidence honesty | GTCRN measured & rejected, arithmetic-coding v2 rejected, "never say 889× vs cellular" | sarancode-bits `flaws.md`; NipunAdarsh self-retracting README; Niranjan266 brutally honest writeup | Peers exist — not a differentiator any more, just table stakes |
| Tests | 222 py + 127 fw + 12 Android | Niranjan266 226; NihalMishra 168 | Parity |

## 3. Where rivals are ahead — the gap matrix

Clustered, with how many repos have it *in code*, the best implementation to copy, and my read on jury value.

| # | Gap | Repos | Best implementation | Jury value | Effort for us |
|---|---|---|---|---|---|
| **A** | **On-device benchmark reports on real phones** (WER/CER/RTF/PSS/latency, committed as md+CSV) | 4 | **Cmcyooo** (Samsung S24, per-language `*_android_validation.md`), NipunAdarsh (two Xiaomi phones), lector-sys (JSON results + scripts) | **Very high** — our numbers are desktop-only and we say so. "Show me on a phone" is the first jury question. | Low — Evaluation Mode already exists; needs two phones + an afternoon |
| **B** | **ACK / retransmit / dedup / priority retries** (msg-id, 800 ms × 3, emergency gets 5 retries, NACK missing seqs, per-message ✓/✗ state) | 8 | lector-sys & rishikafrfr (CRC-16 frames + ACK watchdog), itz-Arun-001 (priority retries + NACK), Sanchit-044 (`ChannelArbiter`) | High — reliability is the PS's word | Low — frame has seq; add ACK type + timer |
| **C** | **Multi-hop flood relay** (TTL byte, seen-cache, random rebroadcast jitter, as a Transport decorator) | 6 | Niranjan266 (decorator design), **naitik2424** (unit-tested A→B→C over RFCOMM), HarshCoder1122 (TCP+RFCOMM simultaneously) | High — extends range with zero hardware; 3 emulators demo it | Low–Med — our frames are 45 B so relay cost is trivial |
| **D** | **Downloadable / importable language packs** (catalogue JSON, SHA-256, resumable, install/delete UI, SAF sideload, licence display) + **RAM policy** (one engine at a time, engine swap on <4 GB) | 7 | lector-sys / rishikafrfr (HF catalogue), NihalMishra (atomic staged install + rollback), Durgesh-18 (PSS-measured swap policy), Cmcyooo (96 MB base APK) | High — "how does a villager get Tamil?" Our answer today is `adb push`. | Med |
| **E** | **ALERT preemption + clause-streamed TTS + forced alarm volume** (alert interrupts at danda boundary, interrupted message resumes, alert replays once; STREAM_ALARM to max then restore; DND bypass; strobe/haptic) | ~10 | lector-sys / rishikafrfr (preemption), Sanchit-044 (clause chunking + Indic number normalisation lakh/crore), HarshCoder1122 (siren), Niranjan266 (volume verified on device) | High for the demo moment | Low |
| **F** | **Phrase codebook / semantic intent packets** (12-bit index → 16 B message; 4 B intent+priority+seq via on-device MiniLM; parallel per-language lists = free translation of the phrasebook) | 5 | **Niranjan266** (16 B, fingerprinted, append-only), vishallr821 (MiniLM classifier 24/24 on hardware, keyword fast-path), Vishal-4356, Musa2609 (2 B) | High — a "VarnaCode mode 0" that makes emergency phrases 3× smaller *and* cross-language | Low–Med — fits our frame flag byte |
| **G** | **Hands-free "phone mode"** (Silero/sherpa VAD auto-segmentation, ~320 ms pre-roll, PTT_START/END + HEARTBEAT control msgs) | 6 | Cmcyooo, NipunAdarsh, Durgesh-18 (idle = VAD only, 1 thread) | Med | Low — we already run sherpa VAD |
| **H** | **Translation between languages** | 8 | ML Kit (udaisankars, helo-ayush, OG-Wizards — proprietary), Opus-MT JNI (NihalMishra — Apache, unfinished), IndicTrans2 (Musa2609, Python only), phrase tables (HarshCoder, CodeVoyager, Sanchit) | Med — juries like it; PS doesn't demand it | Med–High if real (IndicTrans2 distilled ≈200 MB/direction); Low if phrasebook-only (= F) |
| **I** | **Key exchange instead of pre-shared key** (ECDH P-256/X25519 → HKDF → AES-GCM, 6-digit SAS confirmation, header as GCM AAD so ALERT bit can't be flipped, encrypted group rooms via PBKDF2, relays forward ciphertext blind) | 4 | **Sanchit-044** (AAD + SAS), naitik2424 (rooms + zero-trust relays), NihalMishra (per-hop re-encrypt) | Med–High if we add mesh (C): mesh + PSK is weak | Med |
| **J** | **Clock sync for true one-way latency** (PING/PONG min-RTT window) | 2 | lector-sys / rishikafrfr | Med — makes Evaluation Mode's latency honest cross-device | Low |
| **K** | **In-app link emulator** (bps throttle 20–1000, loss %, bit corruption, FEC sweep matrix; live airtime vs Opus/PCM) | 4 | vishallr821 (full matrix), Niranjan266 (300 bps live demo) | High for demo — 45 B at 300 bps is 1.2 s; Opus is 12 s. Nobody can beat that slider. | Low |
| **L** | **FEC** (XOR-parity blocks K+1, Hamming(7,4), unit-tested recovery; unequal error protection by criticality × (1−STT confidence)) | 5 | vishallr821, Anubhab47677, Musa2609, RITIKAYADAV (UEP idea) | Med — matters on the AFSK/LoRa path where we actually have bit errors | Low–Med |
| **M** | **Location / SOS beacon** (2 B grid index or 8 B lat/lon in frame; BLE-advert connectionless 22 B beacon; RSSI radar; TLV with medical/role) | 6 | vishallr821 (2 B grid), Barath410 (TLV design), helo-ayush (BLE beacon + Kalman RSSI), NihalMishra (source-tagged) | Med–High — ISRO = NavIC; a 2–4 B grid cell fits our frame | Low for the field, Med for beacon |
| N | Floor control for half-duplex PTT (REQUEST/GRANT/DENY/RELEASE) | 1 | Sanchit-044 | Low–Med | Low |
| O | Language auto-detect (sherpa Whisper-tiny SLID with safety routing; Unicode-block detect on text) | 4 | Cmcyooo (SLID), several (script detect) | Med | Low (text) / Med (audio) |
| P | UI localisation into all 10 languages; UI-language ≠ speech-language | 3 | lector-sys, Vishal-4356, Sanchit-044 | Med — cheap "we mean it" signal | Low |
| Q | Accessibility roles: STT-only / TTS-only device | 2 | HarshCoder1122, Durgesh-18 | Med — hearing/speech-impaired framing | Low |
| R | Groups / rooms / channels (announce/join/leave; encrypted rooms) | 3 | anvesha-bhargava (protocol), naitik2424 (crypto) | Med | Med |
| S | Urdu→Devanagari transliteration guard for wrong-script ASR output | 1 | lector-sys | Low–Med (Hindi-specific bug we may also have) | Low |
| T | STT confidence gate / audio fallback tier (Opus/EnCodec when confidence low) | 3 | gogul098, babbaransh, Musa2609 | Med — good architecture story, but we argued text-only on purpose | Med |
| U | Isolated `:ai_engine` process via AIDL (crash isolation) | 1 | sarancode-bits | Low | Med |
| V | Zero-config pairing UX (QR / 6-char join code / 3-digit "channel", UDP broadcast + `/announce`) | 4 | JashThaker9, DakshG26, Vishal-4356 | Med — NSD already gives us zero-config on Wi-Fi; BT still needs pairing | Low |
| W | Engineering HUD per message (payload bits vs text bits vs audio; per-stage latency chain; RF-savings chip) | 4 | vishallr821, HyperHawks (UI), Spirit019 | Med — we have byte chips; extend | Low |
| X | Candid `flaws.md` | 1 | sarancode-bits | — | we have Honesty notes |

Things rivals have that we should **not** copy: ML Kit / Sarvam / Bhashini cloud (violates our offline+open rule; several repos hide this), MMS-TTS (CC-BY-NC), XTTS speaker cloning (non-commercial), Phi-3 first-aid chatbot (Precise-Goals — scope creep), Nearby Connections (proprietary, already rejected), BLE "radar" minimaps (demo gimmick with fake precision).

## 4. Roadmap — ranked by (jury value × fit) / effort

**Tier A — do before finals (each ≤ 1 day, all demo-visible):**
1. **A. Real-phone benchmark report.** Run Evaluation Mode on two real phones (budget + mid), commit `app/benchmarks/<device>_<lang>.md` + CSV: CER on FLEURS clips, RTF, PSS, e2e latency. This converts our biggest weakness into our biggest number (we'll be 2–5× better than Cmcyooo's S24 report). Add **J** (clock sync) so cross-device latency is honest.
2. **K. Link-emulator slider in Evaluation Mode.** 20–1000 bps throttle + loss %. Live comparison chip: "this sentence: 45 B → 1.2 s at 300 bps; Opus would be 12 s". Cheapest wow in the list; nobody's payload is small enough to make it look this good.
3. **B. ACK/retransmit/dedup with priority retries.** Frame already has seq; add ACK type, 800 ms timer ×3 (×5 for ALERT), seen-cache. Per-bubble ✓ / ✗ state.
4. **E. ALERT preemption + alarm volume + clause chunking.** Interrupt at danda, resume, replay once; STREAM_ALARM max then restore; Indic number normalisation (lakh/crore) before TTS.
5. **F. Phrase codebook as VarnaCode mode 0.** ~64 fingerprinted emergency phrases × 10 languages, 12-bit index → ~16 B frame; receiver renders in *its* language = free translation for the phrasebook. Reuse the flag byte. Bench it into `bench_compression.py` next to Unishox2/SCSU.

**Tier B — high value, 1–3 days each:**
6. **C. Flood relay with TTL** as a Transport decorator (Niranjan266's design, naitik2424's test). Demo on 3 emulators A→B→C. Pairs with:
7. **I. ECDH pairing + AAD header.** X25519→HKDF→AES-GCM, 6-digit SAS; header in AAD so the ALERT/priority bits are authenticated; relays forward ciphertext blind. Needed once C exists.
8. **D. In-app language-pack import (SAF) + SHA-256 + one-engine-at-a-time RAM policy.** Full HF-catalogue download is optional; SAF import alone removes `adb push` from the story.
9. **M. Location field.** 4 B lat/lon grid (~10 m) in the frame behind a flag; ISRO/NavIC framing. Skip the BLE radar.
10. **L. XOR-parity FEC on the AFSK/LoRa path** (K+1 blocks), unit-tested recovery; report BER→frame-loss curve.
11. **G. Hands-free mode** with our existing VAD; idle = VAD thread only.

**Tier C — cheap polish:** P (UI strings in 10 languages), Q (STT-only/TTS-only role toggle), O (script auto-detect on text), S (Urdu-script guard), W (extend byte chips with per-stage latency).

**Skip, and say why in the deck:** cloud/proprietary translation (H via ML Kit), audio fallback tier (T — text-only is the thesis), LLM assistant, speaker cloning, Nearby Connections.

## 5. The repos that can beat us on the day

| Repo | Why it's dangerous | What beats it |
|---|---|---|
| **Cmcyooo/iTantra** (maturity 5) | Released APK, 10-language downloadable packs, Silero VAD, auto language-ID, zero-config emergency flow with ACK watchdog, **per-language on-device FLEURS reports on a Samsung S24**. This is the "it just works on a phone" team. | Their CER is 2–5× worse (Vakyansh wav2vec2), JSON payload, 884 MB PSS, no encryption/mesh/radio. Tier A #1 + #2 neutralises them. |
| **lector-sys/itantra ≡ rishikafrfr/iTantraaa** (5 / 4; same codebase, almost certainly one team) | Coherent engineering story: 12-byte CRC-16 frames, ACK/retransmit, clock sync, clause-boundary ALERT preemption, HF packs with SHA-256, ESP32 SPP receiver, FLEURS eval scripts + JSON, 24–34 MB APK, UI in 10 languages. | Hindi CER 13% vs our 2.9%; no text compression at all; MMS-TTS is CC-BY-NC (say so if asked); emulator-only numbers. Tier A #3/#4 copies their two best ideas. |
| **Niranjan266/iTantra** (4) | Best write-up in the field; two-phone RFCOMM log (62 B sentence); frozen 11-byte header + phoneme table; 3-byte prosody; **16 B phrase codebook**; flood relay + BLE-advert + Wi-Fi multicast bearers; live 300 bps throttle; WER/latency CSV; 226 tests. | Only en+ta; raw UTF-8 (no entropy coding — our 45 B on *Indic* text vs their 62 B on *English*); no encryption; no radio hardware; no corpus CER. Tier A #2 and #5 are their ideas, done on top of a real codec. |
| NihalMishra3009/ITANTRA (3+) | Deepest systems design: per-peer ECDH, Room store-and-forward, DTN routing, atomic pack installer, 168 tests. | Whisper-base, ~100 B overhead per packet, zero device-to-device evidence (their docs admit it). Design to borrow (I, D), not a demo threat. |
| Precise-Goals/iTantra-Communication-Ecosystem (4) | Same IndicConformer family, protobuf, SHA-256 resumable downloader, Wi-Fi Direct + BT two-device. | No measured accuracy/latency anywhere; Phi-3 assistant is scope creep. |

## 6. One-line positioning for the deck

> The only SIH26173 entry with entropy-coded text (4.45–5.41 bits/char, 45 B/sentence), an analog-radio path (AFSK, 0.3 s per sentence), LoRa firmware parity-tested against the reference, and a CAP/SACHET alert bridge — with 2–5× lower CER than the best rival that measured on a phone.

(Valid only after Tier A #1 lands; until then the last clause is desktop-only and a sharp jury will ask.)
