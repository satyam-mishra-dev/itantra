# Wow-Factor Wave 2 — divergent search, scored, built (2026-08-31)

Goal: find the feature no other team will have. Each candidate was novelty-checked against
the live web, then scored **wow × feasibility-tonight × uniqueness** (1–5 each).

## Scored table

| # | Candidate | Wow | Feas. | Uniq. | Score | Verdict |
|---|---|---|---|---|---|---|
| a | **Prosody-over-text** — 1-byte urgency code survives the 45-byte bottleneck; receiver TTS adapts rate/volume | 5 | 5 | 5 | **125** | **BUILT** (`p0/prosody.py`) |
| g | **Voice-channel modem** — frames as audio tones through ANY analog radio/walkie-talkie | 5 | 4 | 4 | **80** | **BUILT** (`p0/afsk.py`) |
| b | **Digital roll-call** — offline evacuation headcount over 3-byte ACK frames | 4 | 5 | 4 | **80** | **BUILT** (`p0/rollcall.py`) |
| f | **CAP/SACHET bridge** — official alerts re-broadcast into the offline net | 4 | 4 | 3 | 48 | **BUILT** (`p0/cap_bridge.py`) |
| e | Speak-for-me accessibility mode | 3 | 5 | 2 | 30 | FREE — already exists (typed-text mode + far-end TTS); rename & pitch it |
| c | SOS GPS beacon | 3 | 4 | 1 | 12 | SPEC ONLY — Meshtastic/RescueMesh own this space; a 20-byte frame type, add if juries ask |
| d | Cross-language relay (offline MT) | 5 | 1 | 2 | 10 | ROADMAP — model size (100s of MB/pair) + RTranslator precedent; keep as the §6.6 teaser |

## Why the winners win

### a) Prosody-over-text (score 125) — the conceptual closer
- **The academic anchor is the attack**: STCTS (arXiv 2512.00451), the state-of-the-art
  semantic speech codec, explicitly says STT→TTS pipelines "sacrifice prosodic expressiveness
  (intonation, emphasis, emotion)" — and spends **312–592 bps** transmitting continuous prosody
  contours to fix it. iTantra's answer: a disaster channel doesn't need the *contour*, it needs
  the *urgency* — **8 bits per sentence** (level + pitch class + rate class), a ~40–70×
  cheaper point on the same curve, purpose-built for alerts.
- Receiver-side actuation uses knobs that already exist: sherpa-onnx `speed`
  (VITS length_scale) + playback gain + the existing ALERT volume path. No model changes.
- Demo line: *"When a scared voice says 'the water is rising', the far phone hears it fast
  and loud. Calm stays calm. Panic survives 45 bytes."*
- No other team will have this because it requires having already committed to text-as-codec
  and then reading its strongest critique.

### g) Voice-channel modem (score 80) — "any radio becomes a data link"
- ggwave (ggerganov, MIT, 8–16 B/s FSK data-over-sound) proves the physics; Gibberlink proved
  the demo appeal. **Nobody chains it to a speech pipeline**: iTantra frames are ≤73 B —
  at AFSK 1200 baud a full encrypted sentence crosses in **under a second of audio**.
- Strategic weight: the PS title says *"Radio Access for low bitrate links"*. India has millions
  of legacy analog VHF/ham handsets (₹500–2,000) with **no data port at all**. Hold the phone to
  the mic: every analog walkie-talkie, HF set, even a landline call becomes an iTantra bearer.
  Zero new hardware — softer than the LoRa bridge, wider than Bluetooth.
- Built as a ~200-line stdlib Bell-202-style AFSK modem (1200/2200 Hz, 1200 baud, Goertzel
  demod) with round-trip tests through a simulated 300–3400 Hz noisy voice channel.
  ggwave cited as production validation of the approach.

### b) Digital roll-call (score 80) — the humanitarian number
- Every existing mustering/roll-call product found (Stratus-io, EmergencyOS, headcount.io,
  SwipedOn) is **internet- or QR-kiosk-based**; Facebook Safety Check needs the internet that
  the disaster just removed. Offline, radio-borne roll-call appears to be unbuilt.
- Protocol cost: question = one ALERT frame; each answer = one **ACK frame with a 3-byte
  payload** (respondent id + status SAFE/NEED_HELP/SOS). A village ward's 40 households =
  120 payload bytes total. Aggregator shows "32 safe · 3 need help · 5 silent."
- Demo line: *"The sarpanch asks once, in Odia, by voice. Thirty seconds later they know who
  needs the boat."*

### f) CAP/SACHET bridge (score 48) — completes the national last mile
- SACHET (NDMA/C-DOT) publishes CAP alerts and an RSS/feed integration path
  (sachet.ndma.gov.in/CapFeed; agency integration guide PDF). The portal's own docs position
  RSS for re-dissemination by agencies — exactly what an iTantra gateway node does: parse the
  CAP XML, map severity→ALERT priority, VarnaCode the local-language `<info>` block, broadcast
  into the offline net. Official alert → spoken in the village's language on phones with no
  internet. ISRO/NDMA alignment in one demo.
- Built offline-testable: standard CAP 1.2 parser + bundled sample alert; feed URL is a
  parameter (live endpoint needs the agency guide / may need registration — flagged honestly).

## Sources
- STCTS prosody/bitrate: arxiv.org/html/2512.00451v2 · sherpa-onnx speed/length_scale: github.com/k2-fsa/sherpa-onnx/issues/2043, pypi.org/project/sherpa-onnx
- Mustering prior art (all online): headcount.io, cloud-in-hand.com, facilityos.com/emergencyos/roll-call-system, xenia.team
- Data-over-sound: github.com/ggerganov/ggwave (+ waver app), en.wikipedia.org/wiki/Gibberlink
- SACHET feeds: sachet.ndma.gov.in/CapFeed, sachet.ndma.gov.in/About, en.vikaspedia.in national-disaster-alert-portal
- LoRa SOS prior art: meshtastic.org, hackster.io RescueMesh
