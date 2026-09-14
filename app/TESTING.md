# iTantra app — automated functional + low-bitrate testing

Two headless Android 34 emulators (`itantra_c` / `itantra_d`, ports 5570/5572), driven end-to-end
with adb only — no human taps. Scripts: `app/tools/loop_test.sh`, `app/tools/resilience_test.sh`.
Logs: `app/testlogs/`. Screenshots: `app/screenshots/loop-*.png`, `resilience-b.png`.

## Two-phone loop under emulator network shaping (`loop_test.sh`)

Per speed preset: fresh app start on both → NSD connect → A sends 3 messages (3rd is ALERT) →
B must show exactly 3 bubbles, correct text, ALERT chip, no duplicates.

| speed:delay | connected | bubbles on B | dupes | ALERT chip | latency host (ms) | latency device tx→rx (ms) | result |
|---|---|---|---|---|---|---|---|
| full:none | ✓ | 3/3 | 0 | ✓ | 3915 3782 4182 | 12, 19, 16 | PASS |
| gsm:gsm (14.4 kbps) | ✓ | 3/3 | 0 | ✓ | 3895 3695 3177 | 100, 8, 13 | PASS |
| edge:edge (~200 kbps) | ✓ | 3/3 | 0 | ✓ | 3770 3081 2793 | 23, 8, 5 | PASS |
| 1:1000 (1 kbps, +1 s delay) | ✓ | 3/3 | 0 | ✓ | 2887 3055 3445 | 21, 10, 5 | PASS |

- **device tx→rx** = `iTantraLink` logcat epoch stamps: A's `tx seq=N` to B's `rx seq=N` (emulators share the host clock).
  Frame-level delivery is 5–100 ms on the emulator link.
- **host** = wall-clock from the PTT release command to the bubble appearing in B's `uiautomator dump`; ~3 s of it is
  the dump itself (≈1–2 s per poll) — a measurement floor, not app latency.
- **Honesty:** the emulator's `network speed/delay` shaping had almost no effect here (1 kbps + 1 s delay preset still
  delivered in 5–21 ms). Inter-emulator traffic rides netsim's virtual Wi-Fi, which the QEMU NIC shaping does not
  govern. So this run proves **functional correctness** of the loop at four settings; **bitrate physics** come from
  `p0/linksim.py` (P7 in `p0/RESULTS.md`), and the true throttled-link test is a real phone on a rate-limited hotspot
  or the LoRa/AFSK bearers.
- STT/TTS: no model packs are sideloaded on the emulators, so the typed-text path and platform TTS fallback were exercised
  (the frame/ARQ/transport path is identical for STT-produced text).

## Resilience (`resilience_test.sh`)

| check | result | detail |
|---|---|---|
| B backgrounded (HOME) mid-transfer, then foregrounded | PASS | delivered after foreground, no crash |
| rotation on both sides mid-conversation | PASS | frame received in landscape (logcat rx), no crash on either side |
| **peer killed → store-and-forward** | PASS | no ✓ while B was dead (2→2 ticks); both frames retransmitted + ACKed after B restarted (4 ✓) |
| sender app killed and restarted | PASS | ● connected again within 60 s |

## What the ARQ layer does (`Arq.kt`, 5 JVM tests + 2 transport tests, 19 total green)

- Every non-ACK frame is ACKed by the receiver — **including duplicates** (a retransmit whose first ACK was lost
  must still be acknowledged, or it loops forever). ACKs are 9-byte frames with `priority=ACK` and the original seq.
- Sender keeps every frame pending until ACKed: retransmit with exponential back-off 1.5 → 3 → 6 → 12 s (capped),
  **never dropped**. Peer disconnected ⇒ frames wait (store-and-forward); on any `connected`/`BT connected` event
  the queue is flushed immediately. The byte chip shows `queued` when no peer was writable, and gets a `✓` on ACK.
- JVM tests: lossless delivery of 20 frames at 30 % loss on data *and* ACKs; zero retransmits at 0 % loss; queue
  waits with no peer then drains on flush; duplicate ACK harmless; back-off bounds the retry rate at 100 % loss
  without giving up. `pumpFrames` splits back-to-back frames and never surfaces a truncated one.
- Bug found by the test, fixed: a synchronous ACK re-entered `onAck()` inside `tick()`'s iteration
  (`ConcurrentModificationException`) — iteration now runs on a snapshot.

## Bugs found while testing (all fixed)

1. `ServerSocket.accept()` / RFCOMM `accept()` never announced the peer — the receiving side stayed on
   "searching for peers…" while receiving frames. Both transports now announce from `attach()`.
2. MainActivity is no longer exported (ConnectActivity is the launcher) — test scripts enter via the launcher and tap
   "find peers".
3. Automation pitfall: after `input text` the soft keyboard covers the PTT button — the "long press" typed `g`.
   Scripts dismiss the IME (`keyevent 111`) before pressing.

## Known ceilings (deliberate, documented)

- **ARQ is first-ACK-wins.** With several peers on the link, a frame is considered delivered once *any* peer ACKs it;
  a peer that was down at that moment does not get it later. Discovered because a second emulator pair on the same
  virtual Wi-Fi ACKed for the dead peer. Two-phone spec is met; per-peer ARQ is the upgrade when group use matters
  (`ponytail:` note in `Arq.kt`). The resilience script isolates the pair before the store-and-forward check.
- A dead TCP peer's socket still accepts writes until the kernel notices, so the `queued` chip is not the first signal
  that the peer is gone — the missing `✓` is. `peer disconnected` arrives when the write fails or the read loop ends.

## Field-bug pass (2026-09-15) — real APK on two Android 14 emulators, no `-g` shortcuts where it mattered

Users reported: packs never install, phones don't connect, text/voice "not converted". Every row below is a
run on `itantra_c`/`itantra_d` (ports 5570/5572) with the Hindi STT (IndicConformer int8, 98 MB zip) and TTS
(Piper, 67 MB zip) packs served from a local throttled HTTP server (`-PpackBase=http://10.0.2.2:8000`).

| # | check | result | evidence |
|---|---|---|---|
| 1 | **fresh install, no pre-granted permissions** (the real user path) | **CRASH found → fixed** | `SecurityException: Starting FGS with type microphone … requires RECORD_AUDIO` the moment the talk screen opened on Android 14; PttService now starts only after the grant. All earlier tests used `adb install -g` and never saw it |
| 2 | in-app pack download, auto on unmetered Wi-Fi + one-tap pill | PASS | chip shows `downloading hi stt 17%`; STT engine loads (typed box hides); progress counter Int overflow at 21 MB found + fixed |
| 3 | app killed at 64 % of a download | PASS | only `stt.part/` on disk, `installed()` false, restart re-downloads from 0; no half pack ever loaded |
| 4 | Wi-Fi off mid-download | PASS | `SocketException` → toast + pill returns; no crash |
| 5 | on-device STT, real Hindi clip (`EvalActivity --es wav`) | PASS | `heard: बाढ़ का पानी बढ़ रहा है तुरंत निकले`, STT 994 ms for 2.9 s (RTF 0.34 on emulator) |
| 6 | on-device VAD sentence streaming (`--ez vad true`, 2 sentences, 0.9 s pause) | PASS | `VAD cut 2 sentence(s)`, seg 1 exact, seg 2 155/624 ms |
| 7 | silent PTT hold with STT installed | fixed | Conformer decoded silence as "आ" and sent it; RMS gate (0.004) → `nothing heard — hold longer` |
| 8 | VAD hears no sentence but the clip has energy | fixed | falls back to whole-clip decode (used to vanish behind "streamed as you spoke") |
| 9 | receiver with Piper pack | PASS | chip `first audio 315–1021 ms`; bubble now lands on receipt (host latency 6 s → 2.3 s) |
| 10 | receiver with NO voice for the language (Odia, platform TTS) | **stall found → fixed** | two messages used to take 30 s + 30 s (queue waited on a speak that never started); now both in 4 s, chip `no voice for or — text shown` |
| 11 | discovery with mDNS disabled (scratch build, beacon only) | PASS | both `● connected` in 12 s via the UDP 47475 beacon — the fallback for OEM hotspots that filter mDNS |
| 12 | connect-by-IP before the peer app is running | PASS | `dialing 10.0.2.16… (3/20)` → connected once B started |
| 13 | duplicate sockets | fixed | NSD-resolve + beacon dialed the same host 4× (4 `rx` per frame); dial-once guard → 1 |
| 14 | Wi-Fi off on B mid-conversation, message sent meanwhile, Wi-Fi on | PASS | B `searching…`, A frame queued, delivered after reconnect, ✓ |
| 15 | peer app restart reusing seq 0 (×3) | **drop found → fixed** (p0 + Kotlin) | ReliableReceiver deduped by seq alone: message ACKed (✓ on sender!) but never shown; key is now (seq, CRC) |
| 16 | phrase frame hi → or | PASS | "12 लोग घायल हैं" → 10 B → B renders "12 ଜଣ ଆହତ।", ACKed |
| 17 | loop_test full/gsm/edge, resilience ×4 | PASS | tables above re-run on the Reliable/SpeakQueue build; tx→rx 2–108 ms |
| 18 | CER on the phone vs the deck | fixed | Kotlin CER counted punctuation (26 % for a perfect transcript); now normalised like p0 `norm_dev` |

Also fixed without a row: APK built on another laptop would not update this one (different debug keys) → one
committed signing key for all build types; BT bearer never started on first launch (permission granted after
`start()`); mDNS TTL "service lost" flipped the chip to "searching" while the socket was alive.

Test hooks (debug-friendly, no logic change): `am start -n …/.EvalActivity --es wav <16 kHz PCM16 path> --es lang hi [--ez vad true]`
and `am start -n …/.MainActivity --es say '<text>'` (singleTop) — `adb shell input text` cannot type Devanagari
and the emulator has no injectable mic. Both test scripts now use `say`.

Still emulator-blind: real mic → VAD threshold on a phone mic, Bluetooth RFCOMM, OEM hotspot client isolation,
ALERT loudness under OEM audio policy. Those need the two phones on USB (`adb devices`), and the scripts run unchanged.

## Cannot be verified on emulators

Real mic → VAD sentence segmentation, Bluetooth RFCOMM (no BT hardware), NSD across OEM hotspots, actual ALERT
loudness under OEM audio policy, on-device STT RTF with the 140 MB pack, and true low-bitrate transport (see above).
