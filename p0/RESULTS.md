# P0 measured results

## VarnaCode v1 — corpus-trained codebooks (held-out sentences, measured)

Codebooks: char + top-192 bigram Huffman symbols per language, trained on ~80–560 KB
Wikipedia prose per language blended with the embedded disaster-domain corpus
(`build_codebooks.py`; raw corpus gitignored, `codebooks.json` committed for offline builds).

| Lang | Chars | UTF-8 B | VarnaCode B | bits/char | × vs UTF-8 | gzip B | × vs AMR-NB | × vs Codec2-450 | chars/LoRa-51B UTF-8 | chars/LoRa-51B VarnaCode |
|---|---|---|---|---|---|---|---|---|---|---|
| en | 169 | 169 | 97 | 4.59 | 1.7× | 140 | 200× | 7.4× | 51 | 88 |
| hi | 141 | 367 | 94 | 5.33 | 3.9× | 198 | 229× | 8.4× | 19 | 76 |
| bn | 145 | 391 | 91 | 5.02 | 4.3× | 203 | 243× | 9.0× | 18 | 81 |
| ta | 196 | 534 | 109 | 4.45 | 4.9× | 228 | 274× | 10.1× | 18 | 91 |
| te | 172 | 466 | 108 | 5.02 | 4.3× | 229 | 243× | 9.0× | 18 | 81 |
| gu | 102 | 270 | 68 | 5.33 | 4.0× | 166 | 229× | 8.4× | 19 | 76 |
| mr | 103 | 277 | 67 | 5.20 | 4.1× | 167 | 234× | 8.6× | 18 | 78 |
| kn | 115 | 313 | 77 | 5.36 | 4.1× | 182 | 228× | 8.4× | 18 | 76 |
| ml | 132 | 364 | 79 | 4.79 | 4.6× | 183 | 255× | 9.4× | 18 | 85 |
| or | 106 | 290 | 68 | 5.13 | 4.3× | 165 | 238× | 8.8× | 18 | 79 |

*AMR/Codec2 columns: bytes those codecs would spend on the same sentence spoken aloud
(13.3 chars/s en, 10 chars/s Indic) ÷ VarnaCode bytes. gzip shown for honesty: on short
single sentences its header overhead loses to VarnaCode. LoRa columns: characters fitting
one 51-byte SF12 payload — UTF-8 fits 18–19 Indic chars, VarnaCode fits 76–91: a full
spoken sentence per frame.*

### v0 → v1 (bits/char)

| | en | hi | bn | ta | te | gu | mr | kn | ml | or |
|---|---|---|---|---|---|---|---|---|---|---|
| v0 (embedded corpus / uniform blocks) | 4.59 | 5.16 | 5.30 | 4.86 | 5.16 | 7.37 | 7.38 | 7.44 | 7.39 | 7.40 |
| **v1 (corpus + bigrams)** | **4.59** | **5.33** | **5.02** | **4.45** | **5.02** | **5.33** | **5.20** | **5.36** | **4.79** | **5.13** |

### vs published baselines (Indic short text, bits/char)

| Coder | bits/char | Source |
|---|---|---|
| UTF-8 | 24.0 | 3-byte Indic plane |
| SCSU / BOCU-1 | 8.0–8.8 | JOSS Unishox2 paper, measured (research/text-compression.md) |
| Unishox2 (Meshtastic's coder) | 7.3–7.8 | JOSS paper, measured Indic sentences |
| GSM 7-bit national tables (3GPP TS 23.038) | 7.0 | deployed SMS floor |
| **VarnaCode v1** | **4.45–5.36** | this repo, held-out sentences |
| Hindi char entropy (order-n bound) | 4.98 | arXiv:2004.13945 |

Claim discipline: VarnaCode wins because the language is known from the frame header and
the domain is conversational/alert text — Unishox2/SCSU pay for generic any-script
generality. Do not claim a general-purpose win. Hindi at 5.33 sits near the 4.98
entropy bound; the residual gap is order-0 Huffman vs context modeling.

### Measured rivals + the v2 arithmetic experiment (same held-out sentences)

| Lang | Chars | UTF-8 b/c | SCSU b/c | Unishox2 b/c | VarnaCode v1 b/c | v2 arith b/c |
|---|---|---|---|---|---|---|
| en | 167 | 8.00 | 8.00 | 4.98 | **4.65** | 4.65 |
| hi | 139 | 21.01 | 8.17 | 8.23 | **5.41** | 5.29 |
| bn | 143 | 21.76 | 8.50 | 8.50 | **5.09** | 5.09 |
| ta | 194 | 21.94 | 8.25 | 8.45 | **4.49** | 4.49 |
| te | 170 | 21.84 | 8.33 | 8.61 | **5.08** | 5.04 |
| gu | 101 | 21.31 | 8.32 | 8.55 | **5.39** | 5.39 |
| mr | 102 | 21.65 | 8.16 | 8.24 | **5.25** | 5.33 |
| kn | 114 | 21.89 | 8.28 | 8.42 | **5.40** | 5.33 |
| ml | 131 | 22.17 | 8.24 | 8.67 | **4.82** | 4.70 |
| or | 105 | 22.02 | 8.46 | 8.46 | **5.18** | 5.18 |

- SCSU and Unishox2 are now **measured in-repo** (`bench_compression.py` `rivals()`, pips
  `scsu` 1.1.1 + `unishox2-py3`), not cited: on our short alert sentences they cost
  **8.2–8.7 bits/char** — slightly worse than the JOSS paper's 7.3–7.8 on longer prose
  (per-string setup amortizes worse on ~50-char sentences). VarnaCode v1 wins every
  language, including English (4.65 vs Unishox2's 4.98).
- **v2 arithmetic-coding experiment (`varnacode2.py`): rejected.** A static range coder
  over the identical char+bigram frequencies averages **5.05 vs v1's 5.08 bits/char** —
  a 0.03 win, far under the 0.25 keep-bar. The bigram symbols already absorb most
  order-0 Huffman inefficiency; arithmetic would add decoder complexity on three
  platforms (Python/Kotlin/C) for ~0.5%. v1 Huffman stays the wire format; the
  experiment stays in-repo with its own lossless self-check (70 cases).

### AES-GCM envelope (version-2 frames)

Optional pre-shared-key encryption around the VarnaCode payload:
`payload = nonce(12) + AES-128-GCM ciphertext (+16 B tag)`, with the frame header bytes
(ver|lang|prio, seq) as AAD — header tampering fails authentication even if CRC is
recomputed. Overhead **+28 B**: an encrypted Hindi sentence ≈ **73 B**, still ~104×
under AMR-NB's 7,625 B. Implemented in `p0/frame.py` and Android `Frame.kt`;
cross-language vectors (fixed PSK/nonce) prove Python-encrypted frames decrypt on
Android and re-pack byte-identical.

## Pipeline smoke test (measured on this machine, CPU)

Loop: Hindi text -> Piper VITS (hi_IN-pratham-medium) -> wav -> STT -> text, 4 sentences.
Round-trip CER compounds BOTH engines' errors (TTS pronunciation + STT recognition) —
per-engine CER on natural speech is lower. Whisper-tiny emits romanized Hindi, so its raw
same-script CER is meaningless; we report a transliteration-normalized approximation.
IndicConformer int8 (native Devanagari, research/stt.md) replaces both in P1.

| Metric | Piper TTS | Whisper-tiny STT | Vosk small-hi STT |
|---|---|---|---|
| RTF (mean) | 0.049 | 0.055 | 0.119 |
| Round-trip CER | — | ~50% (translit-normalized, approx) | 1.6% (same-script, honest) |
| Round-trip WER | — | — | 7.1% |
| Model on disk | 77 MB | 245 MB (fp32+int8) | 78 MB |

Tests: `python3 test_p0.py` — 154 assertions green.

## P4: STT quantization (int8 dynamic, measured)

`quantize_stt.py` — onnxruntime `quantize_dynamic` (weights→QInt8) on the converted
IndicConformer NeMo-CTC model, sherpa-onnx metadata re-injected post-quantization
(quantizer strips custom metadata_props). Same 4 Piper wavs + references as the
pipeline demo; sherpa-onnx `OfflineRecognizer.from_nemo_ctc`, 2 threads, desktop CPU.

| Hindi model | Size MB | Load s | RTF | CER vs ref | CER vs fp32 hyps |
|---|---|---|---|---|---|
| fp32 | 493 | 0.7 | 0.047 | 0.8% | — |
| int8 | **140** | 0.5 | **0.059** | **1.6%** | 0.8% |

- 72% size cut; RTF stays ~17× faster than real time; accuracy loss is anusvara/
  candrabindu-level (जाएँ→जाए, पहुँचेगी→पहुंचेगी) — within the ±1 pt the literature predicts.
- Generalization: Bengali (5,633-token vocab) converts + quantizes to the same
  **140 MB** and loads in 0.8 s (no bn reference audio locally, so size/load only).
- Per-language phone budget confirmed: ~140 MB STT (int8) + ~63 MB Piper TTS ≈ **203 MB**,
  vs the idea doc's ≤230 MB/language budget. ✓

## P6: real-speech evaluation (FLEURS test, human speakers, measured)

Data: google/fleurs test split, first 20 utterances/language (streamed, cached in
`fleurs/`, not committed). Normalization applied to ref AND hyp before scoring:
NFC -> strip danda/punct -> collapse whitespace -> casefold. Model: IndicConformer
int8 (140 MB), sherpa-onnx `from_nemo_ctc`, 2 threads, desktop CPU.

| Lang | Utts | Audio | CER | WER | RTF |
|---|---|---|---|---|---|
| hi | 20 | 235 s | 2.9% | 8.9% | 0.062 |
| bn | 20 | 279 s | 4.0% | 16.4% | 0.063 |
| ta | 20 | 277 s | 13.9% | 31.3% | 0.059 |
| te | 20 | 227 s | 7.8% | 26.3% | 0.057 |
| ml | 20 | 284 s | 9.2% | 37.6% | 0.059 |

Honest read: synthetic Piper speech round-trip CER was 0.8-1.6% (P0/P4); real spontaneous-adjacent read speech is harder, and
the numbers above are the ones to defend. Published IndicWhisper/IndicConformer
baselines run ~13 WER on Hindi benchmarks — same territory. CER stays the headline
metric for agglutinative scripts (arXiv 2203.16601).

### Noise robustness (babble 85% + white 15%, additive at target SNR)

We also tested a GTCRN speech-enhancement front-end (0.5 MB, RTF 0.031) before STT.

| Lang | Clean | 20 dB | 10 dB | 5 dB |
|---|---|---|---|---|
| hi (noisy) | 2.9% | 8.0% | 11.8% | 17.9% |
| hi + GTCRN | 2.9% | 12.1% | 26.7% | 29.9% |
| ta (noisy) | 13.9% | 13.8% | 17.1% | 22.8% |
| ta + GTCRN | 13.9% | 15.0% | 18.5% | 24.1% |

**Denoiser verdict (evidence-driven): ship WITHOUT a denoiser.** GTCRN made CER
*worse* at every SNR tested (hi @ 10 dB: 11.8% → 26.7%; ta @ 10 dB: 17.1% → 18.5%) —
off-the-shelf speech-enhancement artifacts hurt Conformer ASR more than the noise they
remove. IndicConformer's own noise robustness (trained on spontaneous, real-world
IndicVoices audio) is the better defense; enhancement, if ever added, belongs on the
*playback* side for human ears, not in front of the recognizer. We measured the obvious
trick, it backfired, and the pipeline stays simpler for it.

Chart: `chart-noise.png` (both curves — noisy vs denoised — so the verdict is visible).


## P7: low-bitrate link simulation (`linksim.py`, `test_linksim.py`, `chart-linksim.png`)

A 60-second conversation (10 held-out sentences, alternating speakers, 1 s pauses; a sentence
becomes sendable when the speaker stops) is serialized over modelled bearers as VarnaCode frames,
UTF-8 text frames, Codec2-450 audio and AMR-NB audio (audio chunked to the bearer MTU, 6-byte
frame header per packet). Stop-and-wait ARQ: 9-byte ACK, timeout = RTT + ACK airtime, retransmit
until acknowledged. LoRa airtime uses the Semtech formula (125 kHz, CR 4/5, explicit header);
**IN865's 1% duty cycle is modelled as a 99× rest after every transmission** — the regulatory
reality the firmware also enforces. Deterministic seeds; `python linksim.py` regenerates everything.

**Keeps real time** = last sentence delivered within 5 s of the conversation ending.

| Bearer | Encoding | mean latency | p95 | last byte at | keeps real time? |
|---|---|---|---|---|---|
| LoRa SF12 | VarnaCode | 857.4 s | 1520.7 s | 1767 s | ✗ backlog 1707 s |
| LoRa SF12 | UTF-8 | 2874.7 s | 5203.8 s | 6436 s | ✗ backlog 6376 s |
| LoRa SF12 | Codec2-450 | 7674.7 s | 12699.4 s | 14902 s | ✗ backlog 14842 s |
| LoRa SF12 | AMR-NB | 207058.4 s | 340698.7 s | 399351 s | ✗ backlog 399291 s |
| LoRa SF9 | VarnaCode | 97.8 s | 171.8 s | 247 s | ✗ backlog 187 s |
| LoRa SF9 | UTF-8 | 280.8 s | 541.0 s | 670 s | ✗ backlog 610 s |
| LoRa SF9 | Codec2-450 | 780.1 s | 1298.0 s | 1560 s | ✗ backlog 1500 s |
| LoRa SF9 | AMR-NB | 21299.8 s | 35037.8 s | 41116 s | ✗ backlog 41056 s |
| LoRa SF7 | VarnaCode | 11.7 s | 20.0 s | 77 s | ✗ backlog 17 s |
| LoRa SF7 | UTF-8 | 49.1 s | 100.5 s | 171 s | ✗ backlog 111 s |
| LoRa SF7 | Codec2-450 | 205.2 s | 343.3 s | 436 s | ✗ backlog 376 s |
| LoRa SF7 | AMR-NB | 6061.3 s | 9970.0 s | 11754 s | ✗ backlog 11694 s |
| LoRa SF7 no duty cap | VarnaCode | 0.2 s | 0.2 s | 57 s | ✓ |
| LoRa SF7 no duty cap | UTF-8 | 0.3 s | 0.3 s | 57 s | ✓ |
| LoRa SF7 no duty cap | Codec2-450 | 0.8 s | 0.8 s | 58 s | ✓ |
| LoRa SF7 no duty cap | AMR-NB | 78.9 s | 126.3 s | 204 s | ✗ backlog 144 s |
| dying link 300 bps | VarnaCode | 1.3 s | 1.4 s | 58 s | ✓ |
| dying link 300 bps | UTF-8 | 5.7 s | 8.5 s | 66 s | ✗ backlog 6 s |
| dying link 300 bps | Codec2-450 | 38.7 s | 60.3 s | 127 s | ✗ backlog 67 s |
| dying link 300 bps | AMR-NB | 1636.8 s | 2689.6 s | 3208 s | ✗ backlog 3148 s |
| AFSK 1200 baud | VarnaCode | 0.3 s | 0.3 s | 57 s | ✓ |
| AFSK 1200 baud | UTF-8 | 0.9 s | 1.2 s | 58 s | ✓ |
| AFSK 1200 baud | Codec2-450 | 2.2 s | 2.4 s | 60 s | ✓ |
| AFSK 1200 baud | AMR-NB | 289.3 s | 472.5 s | 610 s | ✗ backlog 550 s |
| GSM CSD 9.6 kbps | VarnaCode | 0.3 s | 0.3 s | 57 s | ✓ |
| GSM CSD 9.6 kbps | UTF-8 | 0.3 s | 0.4 s | 57 s | ✓ |
| GSM CSD 9.6 kbps | Codec2-450 | 0.8 s | 1.0 s | 58 s | ✓ |
| GSM CSD 9.6 kbps | AMR-NB | 85.4 s | 137.3 s | 217 s | ✗ backlog 157 s |
| Bluetooth SPP 100 kbps | VarnaCode | 0.0 s | 0.0 s | 57 s | ✓ |
| Bluetooth SPP 100 kbps | UTF-8 | 0.0 s | 0.0 s | 57 s | ✓ |
| Bluetooth SPP 100 kbps | Codec2-450 | 0.1 s | 0.1 s | 57 s | ✓ |
| Bluetooth SPP 100 kbps | AMR-NB | 1.0 s | 1.1 s | 58 s | ✓ |

### What this means (honestly)
- On the **300 bps "dying link"** only VarnaCode keeps the conversation real-time (1.3 s mean latency);
  UTF-8 already backlogs, Codec2 audio lands 39 s late on average, AMR is unusable (27 min behind).
- **AFSK through a voice radio** (1200 baud): text is real-time at 0.3 s; AMR audio backlogs 9 minutes.
- **LoRa under the 1% duty cycle is a burst channel, not a talk channel — for any encoding.** Ten
  sentences in one minute exceeds the regulatory airtime budget: VarnaCode drains the burst in
  ~4 min at SF9 (sustained ≈ 2 sentences/min, matching the firmware README), UTF-8 in 11 min,
  Codec2 in 26 min, AMR in **11 hours**. The claim to make on stage: *VarnaCode makes LoRa usable
  for messages, and is the only encoding within an order of magnitude of usable.* Without the duty
  cap (licensed / ISRO-class link, row "no duty cap") SF7 carries text in 0.2 s and still cannot carry AMR.
- Bluetooth/GSM-CSD are not the bottleneck for any text encoding — the interesting engineering is
  entirely below 10 kbps, which is where iTantra lives.

### ARQ under loss (VarnaCode frames, stop-and-wait, seed 1)

| Bearer | loss | delivered | packets sent (retx) | mean latency | goodput |
|---|---|---|---|---|---|
| LoRa SF9 | 0% | 10/10 | 10 (+0) | 97.8 s | 15 bps |
| LoRa SF9 | 5% | 10/10 | 15 (+5) | 144.9 s | 9 bps |
| LoRa SF9 | 10% | 10/10 | 16 (+6) | 159.7 s | 9 bps |
| LoRa SF9 | 20% | 10/10 | 17 (+7) | 208.4 s | 8 bps |
| dying link 300 bps | 0% | 10/10 | 10 (+0) | 1.3 s | 62 bps |
| dying link 300 bps | 5% | 10/10 | 15 (+5) | 2.3 s | 60 bps |
| dying link 300 bps | 10% | 10/10 | 16 (+6) | 2.5 s | 60 bps |
| dying link 300 bps | 20% | 10/10 | 17 (+7) | 2.7 s | 62 bps |
| AFSK 1200 baud | 0% | 10/10 | 10 (+0) | 0.3 s | 63 bps |
| AFSK 1200 baud | 5% | 10/10 | 15 (+5) | 0.6 s | 62 bps |
| AFSK 1200 baud | 10% | 10/10 | 16 (+6) | 0.6 s | 62 bps |
| AFSK 1200 baud | 20% | 10/10 | 17 (+7) | 0.7 s | 63 bps |

Every sentence is delivered at every loss rate (lossless by construction: retransmit until ACK).
On LoRa each retransmit costs another 99× rest, so loss hurts latency ~10× more there than on a
duty-free bearer — one more reason to keep frames tiny: fewer bits on air = fewer chances to lose them.
`test_linksim.py`: 24 assertions (airtime formula vs firmware README, latency monotonic in payload size
on every bearer, latency falls with bitrate, real-time verdicts, lossless ARQ with retransmit counts,
BER-induced retransmits, duty-cycle rest math).

## Phrasebook mode (added 2026-09-15, `phrasebook.py`, `python test_phrasebook.py`)

32-phrase emergency register in all 10 languages, 12-bit index + optional 8-bit slot, `lang=15` marker in the unchanged header. Same 32 sentences, text frame vs phrase frame, mean bytes on the wire:

| lang | VarnaCode text frame | phrase frame | ratio |
|---|---|---|---|
| en | 21.8 | 9.1 | 2.4× |
| hi | 21.3 | 9.1 | 2.3× |
| bn | 21.9 | 9.1 | 2.4× |
| ta | 26.6 | 9.1 | 2.9× |
| te | 25.8 | 9.1 | 2.8× |
| gu | 23.7 | 9.1 | 2.6× |
| mr | 22.9 | 9.1 | 2.5× |
| kn | 24.6 | 9.1 | 2.7× |
| ml | 26.4 | 9.1 | 2.9× |
| or | 23.2 | 9.1 | 2.5× |

Note the honest baseline: these register sentences are short, so text frames are 21–27 B here, not the 45 B of the held-out long sentences. The bigger win is not bytes — a phrase frame is language-neutral, so a Hindi speaker's "5 लोग घायल हैं" is spoken as "5 জন আহত" on a Bengali phone with no MT model. Matcher never auto-sends: it returns ranked candidates (exact 1.0, paraphrase 0.6–0.8, off-topic none) and the sender confirms. Translations are draft — native-speaker review pending.
