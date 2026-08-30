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
