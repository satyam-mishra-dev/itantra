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
