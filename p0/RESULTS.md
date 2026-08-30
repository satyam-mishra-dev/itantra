## Compression benchmark (held-out sentences, measured)

| Lang | Chars | UTF-8 B | VarnaCode B | bits/char | × vs UTF-8 | gzip B | × vs AMR-NB | × vs Codec2-450 |
|---|---|---|---|---|---|---|---|---|
| en | 169 | 169 | 97 | 4.59 | 1.7× | 140 | 200× | 7.4× |
| hi | 141 | 367 | 91 | 5.16 | 4.0× | 198 | 236× | 8.7× |
| bn | 145 | 391 | 96 | 5.30 | 4.1× | 203 | 230× | 8.5× |
| ta | 196 | 534 | 119 | 4.86 | 4.5× | 228 | 251× | 9.3× |
| te | 172 | 466 | 111 | 5.16 | 4.2× | 229 | 236× | 8.7× |
| gu | 102 | 270 | 94 | 7.37 | 2.9× | 166 | 165× | 6.1× |
| mr | 103 | 277 | 95 | 7.38 | 2.9× | 167 | 165× | 6.1× |
| kn | 115 | 313 | 107 | 7.44 | 2.9× | 182 | 164× | 6.0× |
| ml | 132 | 364 | 122 | 7.39 | 3.0× | 183 | 165× | 6.1× |
| or | 106 | 290 | 98 | 7.40 | 3.0× | 165 | 165× | 6.1× |

*AMR/Codec2 columns: bytes those codecs would spend on the same sentence spoken aloud (13.3 chars/s en, 10 chars/s Indic) ÷ VarnaCode bytes. gzip shown for honesty: on short single sentences its header overhead loses to VarnaCode.*

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

