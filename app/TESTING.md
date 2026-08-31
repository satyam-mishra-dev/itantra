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

## Cannot be verified on emulators

Real mic → VAD sentence segmentation, Bluetooth RFCOMM (no BT hardware), NSD across OEM hotspots, actual ALERT
loudness under OEM audio policy, on-device STT RTF with the 140 MB pack, and true low-bitrate transport (see above).
