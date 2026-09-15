# HANDOFF — two Claude sessions on this repo (started 2026-09-15)

Sessions: **new-project-50** (features, owns `p0/`, `firmware/`, `research/`, this file) · **new-project-7a** (testing, owns `app/` while its edits are uncommitted).
Message each other with SendMessage (to: "new-project-50" / "new-project-7a"). Human = Satyam, final say.

## Rules
1. Don't edit a path the other owns. Need something there? Write the request under "Requests" below and message.
2. Commit small and often on `main`; never rewrite history; never `git add -A` (the other session's WIP is in the tree). Stage by path.
3. New features are ADDITIVE: new module + new test file; existing tests must keep passing (`p0/test_p0.py` 222 assertions, `firmware/lora-bridge/test_frame_compat.py`, `app ./gradlew test`).
4. Frame format: any wire change goes in `p0/frame.py` FIRST with a test vector, then firmware parser, then Kotlin. Bump the version bit; never change the meaning of an existing bit.
5. Model/licence rule: offline, open-source, commercial-OK only (no MMS-TTS, no ML Kit, no Nearby Connections).

## Ownership now
| Path | Owner | Until |
|---|---|---|
| `app/**` | new-project-7a | its current WIP (BtTransport/NsdTransport/SpeechEngine/MainActivity/ConnectActivity/Packs.kt) is committed — then say so here |
| `p0/**`, `firmware/**`, `research/**` | new-project-50 | — |
| `docs/**`, `README.md` | shared, message before editing | — |

## Feature queue (new-project-50, p0 reference first, Kotlin port after handback)
- [x] B. `p0/reliable.py` + `test_reliable.py` (35 asserts) — 7-byte delivery ACK/NACK (can't collide with 9-byte roll-call ACK), RTO 800 ms, tries NORMAL 3 / ALERT 5, ALERT jumps queue, seq dedup window 64, gap→NACK (≤8), NACK resend is free; `tries=None` = store-and-forward never-give-up with x2 backoff capped 8× (= Arq.kt semantics), `flush()` on reconnect, `next_seq()` skips in-flight. Port = replace Arq.kt wholesale (its 9-byte empty-VarnaCode ACK has plen=3 like roll-call and only parses apart by luck).
- [x] E. `p0/speak.py` + `test_speak.py` (30 asserts) — `normalise()`: danda/punct → clauses (Piper otherwise says "पूर्णविराम"), Indian-grouped numbers → lakh/crore words in all 10 langs, unit abbreviations (en/hi/mr/bn lexicon), acronyms spelled out; `SpeakQueue`: ALERT preempts at clause boundary, interrupted msg resumes at its clause, alert plays twice, ALERT_GAIN flag for STREAM_ALARM. Kotlin port pending.
- [x] F. `p0/phrasebook.py` + `phrasebook.json` + `test_phrasebook.py` (38 asserts) — 32 phrases × 10 langs, `lang=15` marker (frame.py untouched; receivers must call `is_phrase_frame()` before `frame.unpack`), 9–10 B/frame = 2.3–2.9× smaller than text AND rendered in the receiver's language; fingerprint byte detects mismatched books; matcher (token+trigram Jaccard, spoken-number words 0–10/20/50/100 in 10 langs) returns ranked candidates — **sender confirms, never auto-sends**. ⚠️ translations are my draft: team must native-review `phrasebook.json` before the demo.
- [x] C. `p0/relay.py` + `test_relay.py` (31 asserts) → `app/…/RelayTransport.kt` + `RelayTest.kt` (5, byte-identical envelopes) — flood relay as a Transport decorator. Envelope = `lang=14` marker · prio copied · origin(2 B) · ttl:4|hops:4 · inner frame (+9 B). ttl=3 = 3 rebroadcasts (Meshtastic hop-limit semantics), dedup (origin, seq, inner CRC) restart-safe, 20–120 ms jitter (ALERT: none), legacy plain frames delivered but never relayed, ReliableSender/Receiver proven end-to-end across a hop with ACKs riding the flood back.
- [x] L. `p0/fec.py` + `test_fec.py` (29 asserts) — shortened Reed–Solomon (`reedsolo`, public domain, pinned in requirements.txt) on the AFSK path: `protect/recover`, `afsk_send/afsk_recv` with a raw demodulator that hands bytes to RS *before* the CRC gate (today afsk.demodulate discards any frame with one flipped bit). RS8 = +8 B, RS16 = +16 B; corrects nsym/2 byte errors incl. 8-byte bursts; frame CRC is the final gate so a wrong repair never surfaces. LoRa deliberately NOT app-FEC'd (PHY CR 4/5–4/8 already; failures are whole-packet loss). Kotlin/firmware port pending (libcorrect BSD for ESP32).
- [x] M. location — **additive change in `p0/frame.py` + `app/…/Frame.kt`** (rule 4 followed: p0 first, firmware parity 127/127 unchanged, Kotlin byte-identical via `location` vectors, LocationTest 2/2): prosody-byte bit 6 = LOC, 6-byte trailer (24-bit signed lat/lon, ~1.3 m) at the end of the plaintext payload → inside AES-GCM when encrypted; +7 B per frame incl. the prosody byte; old receivers ignore it (VarnaCode decoder stops at EOF). `frame.pack(..., location=(lat, lon))`, `unpack()['location']`; Kotlin `Frame.pack(..., location = Pair(lat, lon))`, `Msg.location`.
- research agents running: receiver-language thesis, DTN thesis, channel-adaptive thesis → `research/`

## Requests
(new-project-50 → 7a): when your app WIP is committed, tell me which of the queue items above you want ported to Kotlin by you vs by me.
(7a → 50): app/ WIP committed (2bca924). "app/ free" for NEW Kotlin files only (Reliable.kt, Normalise.kt, Phrasebook.kt, Relay.kt… + their tests). MainActivity/NsdTransport/BtTransport/Packs/layouts stay with 7a (live emulator testing + a UI sub-agent on branch `ui-modern`); to wire a port in, message 7a the one-line call site and 7a wires + tests it. Port B (reliable) yourself — replace Arq.kt wholesale, Frame.pack wire-identical; 7a runs loop_test.sh/resilience_test.sh on it.
(7a → 50): emulator ports 5570/5572 (itantra_c/_d) and 5580/5582 (itantra_ui_a/_b) are in use by 7a — don't start emulators there.

(50 → 7a) **Piper voices beyond hi_IN — commercial-OK (Piper MIT; check each voice's MODEL_CARD, most are MIT/CC-BY):** all under `https://huggingface.co/rhasspy/piper-voices/tree/main/<lang>/<locale>/<voice>/medium/` (files `<locale>-<voice>-medium.onnx` + `.onnx.json`; sherpa-onnx also needs `espeak-ng-data`, reuse hi pack's):
- ml: `ml/ml_IN/arjun/medium/`, `ml/ml_IN/meera/medium/` (~63 MB)
- mr: `mr/mr_IN/google/medium/` (9 speakers, ~77 MB; pick speaker id 0)
- te: `te/te_IN/maya/medium/`, `te/te_IN/padmavathi/medium/`, `te/te_IN/venkatesh/medium/`
- bn: `bn/bn_BD/google/medium/` (16 speakers, Bangladeshi accent — usable, say so)
- en: `en/en_US/lessac/medium/` (or any en_US medium)
Manifest to verify current names: `https://huggingface.co/rhasspy/piper-voices/raw/main/voices.json`.
**gu / kn / ta / or: NO Piper voice exists.** Deck says "AI4Bharat FastPitch+HiFi-GAN ×4" (MIT, https://github.com/AI4Bharat/Indic-TTS/releases v1-checkpoints-release) — but there is no PyTorch→ONNX export tool in this repo yet, so that claim is unbacked until someone writes `app/tools/convert_indictts.py` (FastPitch + HiFi-GAN → 2 ONNX graphs, sherpa-onnx can't load them natively — needs ORT direct or a VITS-style fused graph). Do NOT use MMS-TTS for these (CC-BY-NC). Until then the honest line is "6 languages with neural voice, 4 text-only".

(50 → 7a) **Relay wrap point** (MainActivity.onCreate), no other change:
```kotlin
val relay = RelayTransport(myId /* stable 16-bit per install, persist in prefs */, onFrame = ::onFrameBytes)
relay.attach(listOf(NsdTransport(..., onFrame = relay::onReceive), BtTransport(..., onFrame = relay::onReceive)))
transports = listOf(relay)   // send()/start()/stop() unchanged for callers
```
Everything already routed through `onFrameBytes` (ctrl → phrase → receiver.ingest) keeps working: it receives the *inner* frame. Demo: three emulators A–B–C with A↔C not connected → A's sentence and ALERT reach C via B, ✓ comes back to A.

## Log
- 2026-09-15 new-project-50: created this file; added research/competitor-survey.md + competitor-cards.md (76 rivals).
- 2026-09-15 new-project-50: B done (p0/reliable.py, now with Arq.kt's store-and-forward semantics). E done (p0/speak.py). F done (p0/phrasebook.py). **Kotlin ports landed**: app/…/Reliable.kt, Speak.kt (Normalise + SpeakQueue), Phrasebook.kt + ReliableTest (10) + SpeakPhrasebookTest (11), all asserting byte-identity against `app/src/test/resources/testvectors_v3.json` generated from p0; `./gradlew testDebugUnitTest` = 42/42. phrasebook.json copied to assets + test resources. MainActivity/Arq.kt NOT touched — 7a wires. Research verdicts filed in research/thesis-*.md: receiver-language (a) via Bergamot tiny en-pivot 17 MB int8 MPL-2.0; DTN (b) robustness chapter not headline, NavIC DAT-SG = ISRO precedent for ≤23 B priority S&F; channel-adaptive (a) with baud knob, controller on far-end CER is the contribution. test_p0 still 222/222. Next: Kotlin ports of B/E/F as new files, then C (relay).
- 2026-09-15 new-project-7a: app/ WIP = Packs.kt downloader, NSD MulticastLock + UDP beacon fallback, BT restart after permission, platform-TTS fallback fix, shared keystore. No wire change. Will write "app/ free" when committed. Emulators itantra_c/_d on 5570/5572 and itantra_ui_a/_b on 5580/5582 are theirs — don't start emulators on those ports.
- 2026-09-15 new-project-7a: app/ field-bug pass committed (2bca924): in-app pack download, discovery hardening (MulticastLock + UDP beacon + retrying IP connect), BT restart, TTS no-voice stall fix, shared signing key. Verified on itantra_c/_d: hi STT+TTS packs download + load. Next: full feature test matrix, UI sub-agent.
- 2026-09-15 new-project-50: fixed 7a's restart-dedupe bug (key = seq<<16|crc) in p0 + Kotlin, 39 py / 11 kt reliable tests.
- 2026-09-15 new-project-50: C done (relay), p0 31 asserts + Kotlin RelayTest 5/5; full Kotlin suite 42/42. Next: L (FEC on AFSK/LoRa path), M (location field).
- 2026-09-15 new-project-7a: Reliable/SpeakQueue/Phrasebook/RelayTransport all wired into MainActivity (Arq gone), Android-14 fresh-install FGS crash fixed, UI branch `ui-modern` merged (all ids/strings kept; resilience grep updated to the new chip text). Final suite on the merged build: loop full/gsm PASS, resilience 4/4 PASS, 42/42 unit. app/TESTING.md has the 18-row field-bug table. Pushed to origin/main.
- 2026-09-15 new-project-50: L (fec.py, RS on AFSK) and M (location trailer in frame.py + Frame.kt) done. Kotlin suite 44/44, p0 222 + 39 + 30 + 38 + 31 + 29. FEC SNR sweep running → RESULTS.md.
