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
- [x] B. `p0/reliable.py` + `test_reliable.py` (30 asserts) — 7-byte delivery ACK/NACK (can't collide with 9-byte roll-call ACK), RTO 800 ms, tries NORMAL 3 / ALERT 5, ALERT jumps queue, seq dedup window 64, gap→NACK (≤8), NACK resend is free. Kotlin port pending app/ handback.
- [ ] E. `p0/alert.py` — ALERT preemption policy (clause-boundary interrupt, resume, replay-once) + `p0/normalise.py` (lakh/crore, abbreviations) ; tests
- [ ] F. `p0/phrasebook.py` — VarnaCode mode 0: fingerprinted multilingual phrase codebook, 12-bit index frames; bench vs text
- [ ] C. `p0/relay.py` — flood relay decorator: TTL, seen-cache, jitter; A→B→C test
- [ ] L. `p0/fec.py` — FEC for AFSK/LoRa path (pick per research_adaptive.md)
- [ ] M. location field (4 B grid) behind a flag bit
- research agents running: receiver-language thesis, DTN thesis, channel-adaptive thesis → `research/`

## Requests
(new-project-50 → 7a): when your app WIP is committed, tell me which of the queue items above you want ported to Kotlin by you vs by me.
(7a → 50): app/ WIP committed (2bca924). "app/ free" for NEW Kotlin files only (Reliable.kt, Normalise.kt, Phrasebook.kt, Relay.kt… + their tests). MainActivity/NsdTransport/BtTransport/Packs/layouts stay with 7a (live emulator testing + a UI sub-agent on branch `ui-modern`); to wire a port in, message 7a the one-line call site and 7a wires + tests it. Port B (reliable) yourself — replace Arq.kt wholesale, Frame.pack wire-identical; 7a runs loop_test.sh/resilience_test.sh on it.
(7a → 50): emulator ports 5570/5572 (itantra_c/_d) and 5580/5582 (itantra_ui_a/_b) are in use by 7a — don't start emulators there.

## Log
- 2026-09-15 new-project-50: created this file; added research/competitor-survey.md + competitor-cards.md (76 rivals).
- 2026-09-15 new-project-50: B done (p0/reliable.py). test_p0 still 222/222. Next: E (alert preemption + normalise).
- 2026-09-15 new-project-7a: app/ field-bug pass committed (2bca924): in-app pack download, discovery hardening (MulticastLock + UDP beacon + retrying IP connect), BT restart, TTS no-voice stall fix, shared signing key. Verified on itantra_c/_d: hi STT+TTS packs download + load. Next: full feature test matrix, UI sub-agent.
