# Short Indic-text compression: prior art for VarnaCode

Research pass for VarnaCode — compressing single-sentence Indic-script messages (~40–80 chars,
Devanagari/Tamil/Telugu/Odia/Bengali) for LoRa/low-bitrate transport. Baseline: UTF-8 costs
3 bytes/char (24 bits/char) for every Indic script in the BMP (Devanagari U+0900, Bengali
U+0980, Tamil U+0B80, Telugu U+0C00, Odia U+0B00 are all above U+07FF, so UTF-8 always
spends 3 bytes). Goal: verify whether ~5–6 bits/char is realistic and against what.

---

## 1. Unishox / Unishox2 (siara-cc)

**Exactly the target use case.** Unishox2 is a hybrid encoder (entropy coding + dictionary
coding + delta coding) purpose-built for short Unicode strings on memory-constrained devices
(Arduino, ESP8266/32), described in a peer-reviewed JOSS paper: Ramanathan, A. (2022),
*"Unishox: A hybrid encoder for Short Unicode Strings"*, JOSS 7(69), 3919,
https://doi.org/10.21105/joss.03919 (full text: https://www.theoj.org/joss-papers/joss.03919/10.21105.joss.03919.pdf).

**Algorithm.** ASCII/Latin text uses a fixed Huffman-style prefix-free code (built from published
English letter-frequency tables, not adaptive/trained) split into 5 selectable code "sets"
(Alpha, Symbols, Numbers, Dictionary, Delta) addressed by short horizontal/vertical code pairs.
Runs and repeated substrings get dictionary/RLE-style codes. **Non-Latin Unicode characters —
this covers all Indic scripts — are handled with plain delta coding**: the first codepoint in a
Unicode run is emitted with a range-coded absolute value (6–21 bits depending on magnitude),
every subsequent codepoint in that run is emitted as a *signed delta from the previous codepoint*
(1 sign bit + 6/12/14/16/21 magnitude bits chosen by range code, ~8 bits typical for the small
deltas found inside one Devanagari/Tamil/etc. block). This is deliberately similar to BOCU-1's
idea but simpler — the paper explicitly notes SCSU's windowing is "slightly better" in principle
but that plain delta coding was chosen because short strings are usually single-language.

**License.** Apache License 2.0 (source: JOSS paper "Implementation" section; repo
https://github.com/siara-cc/Unishox2). Note: the project's own GitHub Pages site
(https://siara-cc.github.io/Unishox2/) currently carries an added "not licensed for AI/bot use"
clause — a documentation-page restriction on top of the underlying Apache-2.0 code license, not
a change to the repo's actual LICENSE file. Worth a line of caution if VarnaCode vendors the
code, but it does not affect a from-scratch reimplementation of the published algorithm.

**Measured ratios (from the JOSS paper, Table "Comparison with Unicode compression
techniques" — translations of Kahlil Gibran's "Beauty is not in the face...", all sizes in
bytes):**

| Language | UTF-8 bytes | Unishox | SCSU | BOCU-1 |
|---|---|---|---|---|
| English | 58 | 30 | 58 | 58 |
| Hindi | 144 | 53 | 55 | 55 |
| Bengali | 117 | 41 | 48 | 47 |
| Punjabi | 141 | 51 | 57 | 59 |
| Marathi | 142 | 52 | 55 | 58 |
| Telugu | 104 | 39 | 42 | 44 |
| Tamil | 128 | 49 | 50 | 52 |

**This is the single most important number for VarnaCode's honesty check.** Estimating codepoint
counts from the UTF-8 byte totals (Devanagari-family scripts = 3 bytes/codepoint, ASCII
spaces/punctuation = 1 byte, ~45–55 total codepoints per row): Unishox2 lands around
**7.3–7.8 bits/char** on Indic scripts, SCSU/BOCU-1 land around **8.0–8.8 bits/char**. Compare
to English, where Unishox2's *real* entropy coding (built on actual English letter frequencies)
gets **4.1 bits/char** (30 bytes / 58 chars). The gap is the tell: for Latin text Unishox2 wins
big because it has a genuine frequency-tuned code; for Indic scripts it falls back to generic
delta coding and is only marginally better than SCSU/BOCU-1's windowing trick — none of the
three get anywhere near 5–6 bits/char on Indic text.

**Non-Unicode comparison (same paper) vs smaz/shoco** confirms Unishox2 is also the strongest
short-ASCII-string compressor of the three (e.g. "Beauty is not in the face..." 58→30 bytes vs
smaz 31, shoco 46; an ISO timestamp 24→9 bytes vs smaz 32/shoco 24; a phone number 14→7 bytes
vs smaz 20/shoco 14).

**Used by Meshtastic — confirmed, not just MeshCore.** Meshtastic's official firmware
(https://github.com/meshtastic/firmware) uses Unishox2 for its `TEXT_MESSAGE_COMPRESSED_APP`
port: it auto-compresses outgoing text and picks whichever of raw/compressed is smaller, and
auto-decompresses on receive — app developers don't need to do anything. Confirmed via
`meshtastic/firmware` PRs #3189 (TAK packet compression), #2819 ("Fix compression"), #3606
("Drop unishox2 functions from Router"), and issue #3841 (a real stack-buffer-overflow CVE in
`unishox2_decompress_simple` from not bounding the output buffer — a concrete implementation
gotcha worth remembering if VarnaCode embeds this code or writes its own decompressor).
A second, independent adoption exists in **MeshCore** (a different LoRa mesh firmware),
documented in detail at https://github.com/meshcore-dev/MeshCore/discussions/1959, which gives
concrete field numbers: 43→30 bytes (30% saving), 85→52 bytes (39%), 95-byte message with
emoji →69 bytes (27%); messages under ~40 characters are sent uncompressed because Unishox2's
per-message overhead isn't worth it below that length; combined with a stream cipher instead of
AES, the discussion projects 25–40% airtime savings on messages over 40 chars. No Indic-specific
numbers are given in either Meshtastic or MeshCore threads — their compression heuristics are
English/ASCII-message-tuned.

Sources: [Unishox2 GitHub](https://github.com/siara-cc/Unishox2), [Unishox2 README](https://github.com/siara-cc/Unishox2/blob/master/README.md), [JOSS paper PDF](https://www.theoj.org/joss-papers/joss.03919/10.21105.joss.03919.pdf), [Unishox project site](https://siara-cc.github.io/Unishox2/), [MeshCore Unishox2 discussion](https://github.com/meshcore-dev/MeshCore/discussions/1959), [meshtastic/firmware PR #3189](https://github.com/meshtastic/firmware/pull/3189), [meshtastic/firmware PR #2819](https://github.com/meshtastic/firmware/pull/2819), [meshtastic/firmware issue #3841](https://github.com/meshtastic/firmware/issues/3841)

---

## 2. SCSU and BOCU-1

**SCSU** (Standard Compression Scheme for Unicode, Unicode Technical Standard #6,
https://en.wikipedia.org/wiki/Standard_Compression_Scheme_for_Unicode) works by keeping up to
8 dynamically-positioned "windows" (plus static windows) into 128-codepoint slices of Unicode
space; once a window is active over a script block (e.g. Devanagari), each character in that
block costs **1 byte** (an index into the active window), with punctuation/ASCII costing 1–2
bytes via non-locking shifts, and a ~1-byte one-time window-select cost per script switch. This
is the classic "SCSU gets Indic to ~1 byte/char" claim, confirmed generically by Unicode's own
FAQ-linked material and by the measured JOSS-paper numbers above (SCSU ≈ 8.0–8.8 bits/char on
Indic sentences, i.e. essentially 1 byte/char plus overhead). SQL Server 2008 R2's SCSU
implementation reports 15–50% space savings vs UTF-8 depending on language, well short of
UTF-8's 50%+ ceiling on pure-ASCII data. Reference implementation: ICU
(https://unicode-org.github.io/icu/userguide/conversion/compression.html); no patent/licensing
encumbrance — SCSU is an open Unicode Technical Standard.

**BOCU-1** (Binary Ordered Compression for Unicode, Unicode Technical Note #6,
https://en.wikipedia.org/wiki/Binary_Ordered_Compression_for_Unicode) is conceptually
Unishox2's Unicode-delta mode's ancestor: it encodes each character as a signed delta from the
previous character (MIME- and binary-order-safe), giving roughly uniform ~1 byte/char
compression across *any* small alphabetic script regardless of which Unicode block it lives in
— no per-script window setup needed, at the cost of being slightly worse than SCSU on some
scripts (matches the JOSS table: BOCU-1 ≥ SCSU on every Indic row).

**Patent — yes, this is real and now moot.** IBM held US Patent 6,737,994 ("Binary-Ordered
Compression For Unicode") covering the core BOCU technique. IBM offered a royalty-free license
on request, but at least one documented case (a self-employed developer) had a license request
refused — this is why BOCU-1 was historically avoided in some open-source stacks even though it
was technically "free to use." **The patent expired 16 November 2022**, so BOCU-1 is now
unencumbered; SCSU was never patent-encumbered (Ewell 2004's Unicode compression survey, UTN#14,
notes BOCU-1 was the *only* Unicode Web-site-listed scheme with IP restrictions).

Sources: [SCSU — Wikipedia](https://en.wikipedia.org/wiki/Standard_Compression_Scheme_for_Unicode), [BOCU-1 — Wikipedia](https://en.wikipedia.org/wiki/Binary_Ordered_Compression_for_Unicode), [ICU compression docs](https://unicode-org.github.io/icu/userguide/conversion/compression.html), [UTS#40 BOCU-1](https://unicode.org/reports/tr40/tr40-1.html), [Just Solve the File Format Problem: BOCU-1](http://justsolve.archiveteam.org/wiki/BOCU-1)

---

## 3. smaz / shoco (short-string precedent, why gzip fails on <100 bytes)

**Why general compressors lose on short strings.** gzip/zlib/bzip2/LZMA carry fixed header +
dictionary/model overhead; the JOSS paper and multiple smaz/shoco sources converge on the same
rule of thumb: **zlib/gzip essentially never compresses (and often expands) text shorter than
~100 bytes**, because the Huffman table / LZ77 window setup and framing overhead exceeds any
savings on such small inputs. VarnaCode's ~40–80 char messages are squarely inside this dead
zone for generic compressors — this is the core justification for using a static, pre-shared
codebook approach (Unishox2/smaz/shoco/SCSU-style) instead of anything gzip-family.

**smaz** (Salvatore Sanfilippo, BSD license, https://github.com/antirez/smaz): a small built-in
dictionary coder for short English/URL strings. It can compress a 2–3 byte string (e.g. "the"
→ 1 byte). README examples: "This is a small string" → 50% saved, "the end" → 58%, a
36-character sentence → 39%, various URLs → 46–59%. No Unicode/Indic awareness at all — it's a
Latin-only static dictionary.

**shoco** (Christian Schramm, MIT license, https://github.com/Ed-von-Schleck/shoco): an entropy
coder for short strings with a default English frequency model, and the option to retrain the
model on custom text (unlike smaz's fixed dictionary). Also ASCII-only. Its own docs say not to
use it above ~100 bytes since gzip's overhead-to-benefit ratio flips around there.

Both lose head-to-head to Unishox2 on every string type tested in the JOSS paper (see table in
§1), which is unsurprising since Unishox2 essentially generalizes their approach (fixed
frequency-tuned entropy code + dictionary of common substrings) and adds Unicode delta coding on
top.

Sources: [smaz README](https://github.com/antirez/smaz), [shoco site](https://ed-von-schleck.github.io/shoco/), [shoco GitHub](https://github.com/Ed-von-Schleck/shoco), [Unishox JOSS paper](https://www.theoj.org/joss-papers/joss.03919/10.21105.joss.03919.pdf)

---

## 4. Academic work on Indic character entropy / Devanagari compression

**Character-level entropy of Hindi (and sibling languages) — a real, citable number.**
Ojha, Zeman et al., *"Linguistic Resources for Bhojpuri, Magahi and Maithili: Statistics about
them, their Similarity Estimates, and Baselines for Three Applications"* (arXiv:2004.13945,
ACM TALLIP; https://arxiv.org/abs/2004.13945) compute character-level entropy via SRILM n-gram
language models (Table 10 of the paper):

| Language | Complete-corpus entropy (bits/char) | Restricted-corpus entropy |
|---|---|---|
| Hindi | 4.98 | 4.97 |
| Magahi | 4.96 | 4.95 |
| Maithili | 5.01 | 5.01 |
| Bhojpuri | 4.86 | 4.85 |

Corpus: Hindi from Europarl v7 (~2.9M tokens); Bhojpuri/Magahi/Maithili from purpose-built
corpora (267K–704K tokens). **This is an n-gram (context-aware) entropy estimate, not naive
order-0 single-character entropy** — it already captures some inter-character correlation via
SRILM's backoff model, so it's a lower bound that a real adaptive/context-aware coder
(order-1+ arithmetic coding) could approach, while a simple *static order-0* Huffman/arithmetic
code (VarnaCode's realistic hackathon scope) will land somewhat above it — this is exactly where
the "~5–6 bits/char" target sits, and it lines up: order-0 Huffman on Devanagari's genuinely
Zipfian codepoint distribution (a few dozen consonants/matras/virama do almost all the work vs.
~130 possible codepoints in the block) plausibly costs ~5.5–6.5 bits/char, comfortably below
Unishox2/SCSU/BOCU-1's measured 7.3–8.8 bits/char on real Indic sentences.

**Telugu entropy.** Ganapathiraju & Balakrishnan (?), *"Entropy of Telugu"* (arXiv:1106.5973,
https://arxiv.org/abs/1106.5973) explicitly studies Telugu's *syllabic* (not alphabetic)
character inventory and the resulting complication in computing entropy — full numeric results
weren't extractable from the available abstract/PDF text in this pass, but the framing confirms
the field treats Indic-script entropy estimation as syllable-aware, i.e. **akshara-level (not
raw-codepoint-level) modeling is the academically preferred unit** for Indic compression, echoing
VarnaCode's own akshara-based framing.

**Devanagari compression benchmark study (2025).** *"Performance Evaluation of Efficient Hybrid
Compression Methods for Devanagari-Encoded Hindi Text Using Lossless Algorithms"*
(arXiv:2504.20747, https://arxiv.org/html/2504.20747v1) benchmarks LZMA/Zstd/Brotli/Bzip2/LZ4HC
and 60 hybrid pipelines on 145 KB / 1.6 MB / 13 MB UTF-8 Devanagari corpora — LZMA and
Brotli-based hybrids top out around 90–140:1 compression ratio on large files, but the paper
**does not test anything under 100 bytes**, so it says nothing directly useful for a single
40–80-char SMS/LoRa message — it's file-scale evidence, not message-scale, and reinforces that
this exact gap (short-Indic-message compression) is thin in the literature, which is Unishox2's
whole reason for existing.

**Older Huffman-on-Indian-language work.** A search turned up *"In Search of a Suitable Indian
Language for Huffman Data Compression Algorithm"* (academia.edu) — a comparative Huffman-coding
study across Indian languages, confirming static Huffman-on-Devanagari is an established,
unremarkable technique academically; no concrete bits/char figure was extractable from the
available excerpt.

Sources: [Bhojpuri/Magahi/Maithili linguistic resources paper](https://arxiv.org/abs/2004.13945), [ar5iv HTML render](https://ar5iv.labs.arxiv.org/html/2004.13945), [Entropy of Telugu](https://arxiv.org/abs/1106.5973), [Devanagari hybrid compression 2025](https://arxiv.org/html/2504.20747v1), [Huffman for Indian languages](https://www.academia.edu/4177567/In_Search_of_a_Suitable_Indian_Language_for_Huffman_Data_Compression_Algorithm)

---

## 5. SMS prior art: GSM 7-bit vs UCS-2 vs national language shift tables (3GPP TS 23.038)

This is a real, already-deployed precedent and a useful "beat this" floor for VarnaCode.

- **Default GSM 7-bit alphabet:** 160 characters packed into 140 octets per SMS segment — but
  this is a Latin-only alphabet table, unusable for Devanagari etc.
- **UCS-2 (what Indic SMS actually falls back to today):** every Indic character costs a full
  16-bit code unit → only **70 characters per 140-octet SMS segment**. This is the real-world
  status quo VarnaCode is implicitly competing with for the SMS use case.
- **National Language Shift Tables (3GPP TS 23.038, since Release 8 / March 2008):** the GSM
  standard defines locking and single-shift 7-bit alphabet tables for **10 non-Latin
  languages/scripts, 9 of them Indic**: Hindi, Bengali, Gujarati, Kannada, Malayalam, Oriya,
  Punjabi, Tamil, Telugu (plus Urdu, Arabic script). A locking shift table replaces the whole
  7-bit alphabet for the message; using it costs a small UDH (User Data Header) selector but then
  packs **each Indic character in 7 bits**, giving up to **155 characters per segment** (slightly
  less than the 160-char Latin case because of the UDH overhead) — a **2.2x** improvement over
  UCS-2's 70-char cap, using nothing but a fixed per-language lookup table, no compression at
  all.

**Why this matters for VarnaCode's positioning:** telecom already ships a *zero-compression*,
pure fixed-alphabet 7-bit encoding for Indic SMS achieving 7 bits/char. That is the floor any
compression scheme must clear to be worth the complexity. Unishox2/SCSU/BOCU-1 (7.3–8.8
bits/char measured, §1–2) are actually **worse than plain GSM national-language 7-bit packing**
for pure single-script Indic text — general Unicode compressors lose to a dumb fixed 7-bit
alphabet table because they're paying for generality (multi-script/emoji/URL support) VarnaCode
doesn't need. A static per-language Huffman/arithmetic code targeting ~5.5–6.5 bits/char would
be the first approach in this whole survey to clearly beat the already-deployed telecom baseline.

Sources: [GSM 03.38 — HandWiki](https://handwiki.org/wiki/GSM_03.38), [3GPP TS 23.038 spec (ARIB mirror)](https://www.arib.or.jp/english/html/overview/doc/STD-T63v11_00/5_Appendix/Rel12/23/23038-c00.pdf), [tech-invite TS 23.038 index](https://www.tech-invite.com/3m23/toc/tinv-3gpp-23-038_e.html)

---

## 6. LoRa payload limits and Meshtastic

**LoRaWAN regional payload caps scale inversely with spreading factor** (EU863-870 band,
125 kHz, from the LoRaWAN 1.0.3 Regional Parameters spec,
https://lora-alliance.org/wp-content/uploads/2020/11/lorawan_regional_parameters_v1.0.3reva_0.pdf):

| Spreading Factor | Max application payload |
|---|---|
| SF12 | 51 bytes |
| SF11 | 51 bytes |
| SF10 | 51 bytes |
| SF9 | 115 bytes |
| SF8 | 222 bytes |
| SF7 | 222 bytes |

This confirms the task's "51–222 bytes by SF" framing exactly. At the long-range/low-bitrate
extreme (SF12, 51-byte cap) this is the tightest and most important regime for VarnaCode's
pitch: at 3 bytes/char (UTF-8) that's only **17 Devanagari characters** per packet — barely
half a sentence. At a genuine 5.5–6.5 bits/char that becomes **~63–74 characters** per packet —
a full short sentence in one SF12 transmission, a **~4x** headroom gain, which is the concrete,
defensible number for the pitch deck (cite payload cap + measured/target bits-per-char, don't
just assert "4x smaller").

Non-LoRaWAN raw LoRa radio (Meshtastic's stack, using Semtech SX127x/SX126x chips directly, not
LoRaWAN's MAC layer) uses similar physical-layer payload limits (max packet ~256 bytes,
~237-byte payload cited in community discussion) but Meshtastic's *own* packet budget is much
tighter in practice — 160-byte text messages was cited as the reason plain LZW/DEFLATE were
ruled out for Meshtastic (too much per-message overhead) in favor of Unishox2 (§1). **Meshtastic
does not do anything Indic/script-specific** — its compression heuristic (skip compression under
~40 chars, use Unishox2 above that) is tuned for English chat traffic, confirming there's no
existing prior art specifically solving Indic-on-LoRa; VarnaCode's angle is open.

Sources: [LoRaWAN 1.0.3 Regional Parameters](https://lora-alliance.org/wp-content/uploads/2020/11/lorawan_regional_parameters_v1.0.3reva_0.pdf), [Meshtastic LoRa packet size discussion](https://meshtastic.discourse.group/t/lora-packet-size-in-meshtastic/3288), [Meshtastic LoRa Configuration docs](https://meshtastic.org/docs/configuration/radio/lora/), [MeshCore Unishox2 discussion](https://github.com/meshcore-dev/MeshCore/discussions/1959)

---

## 7. Practical verdict: static per-language Huffman/arithmetic vs. adopting Unishox2

**The numbers settle this reasonably cleanly.** Measured on real Indic sentences, general
Unicode short-string compressors cluster at **7.3–8.8 bits/char** (Unishox2 best of the three,
SCSU/BOCU-1 behind it) — worse than the zero-compression GSM national-language 7-bit table
already deployed in production telecom (§5), and nowhere near VarnaCode's 5–6 bit/char target.
The reason is structural, not incidental: all three treat every Unicode character as
"some codepoint, could be any script" and fall back to windowing (SCSU) or delta-coding
(BOCU-1/Unishox2) — a *generic* mechanism, not a *frequency-tuned* one. VarnaCode's framing —
**language is already known from the frame header, and the domain is narrow
(conversational/alert text)** — removes exactly the generality these algorithms are paying for.

A static per-language Huffman or arithmetic coder built directly on the actual character
frequency distribution of each target script (informed by the ~4.9–5.0 bits/char n-gram entropy
figures in §4 as a lower-bound sanity check) has a real, defensible shot at **5.5–6.5 bits/char
order-0**, and could push toward the ~5-bit true-entropy floor with order-1
(previous-character-conditioned) modeling if time allows — a **~25–35% improvement over
Unishox2/SCSU/BOCU-1's measured Indic numbers**, and a genuine, citable beat of the GSM 7-bit
baseline.

**But don't discard Unishox2's engineering — reuse its architecture, replace only its weak
part.** Unishox2 already solved several things a from-scratch coder would have to re-solve:
small footprint (~300 bytes RAM total, proven on Arduino), mixed-content handling (numbers,
punctuation, dates/phone templates, repeated substrings), and a battle-tested bitstream
format/decoder — but its Unicode/Indic path (plain delta coding) is exactly its weakest measured
mode (§1). The highest-leverage, lowest-risk hackathon move is **not** "reimplement everything
from scratch" nor "ship Unishox2 unmodified and call it done" — it's:

- Keep Unishox2-style structure for the English/ASCII/numeric/punctuation/template portions of a
  message (ponytail: this part is already solved, don't re-solve it).
- Replace its Unicode delta-coding mode with a **static, per-script Huffman table** (one
  precomputed table per supported script, selected by the frame's language byte — no runtime
  training, no adaptive model, just a lookup table baked at build time from real corpus
  frequencies) for the actual Indic character run.
- Validate the frequency tables against a real corpus per language before the demo — the
  Bhojpuri/Magahi/Maithili paper's methodology (SRILM n-gram char stats) is a reasonable
  template, or simpler: build order-0 tables directly from any available Hindi/Tamil/etc. news
  or SMS-style corpus.

This is a small, bounded diff (one Huffman table + a switch-on-language codepath) rather than a
new compression algorithm, fits a hackathon timeline, and produces an honestly *better*,
narrower-but-true claim than "we beat Unishox2" in general.

---

## VarnaCode design recommendation

**Algorithm:** Frame = 1 header byte (language ID + content-type flag) + payload. Payload uses
a Unishox2-style multi-set bitstream (reuse its ASCII/number/punctuation/template/dictionary
machinery — don't reinvent this part) but with the Unicode/delta mode swapped out for a static,
per-language order-0 Huffman (or simple range/arithmetic) code built from real character-frequency
tables for that language's script, selected by the header byte instead of being auto-detected at
runtime.

**Expected bits/char:** target **5.5–6.5 bits/char** order-0 static Huffman on the Indic
character stream (grounded against the 4.9–5.0 bits/char n-gram entropy floor measured for
Hindi/Bhojpuri/Magahi/Maithili in arXiv:2004.13945 — order-0 will sit a bit above that true-entropy
floor, which is exactly the honest range to claim). This is **2.5–3x smaller than raw UTF-8**
(24 bits/char) and a **~25–35% improvement over measured Unishox2/SCSU/BOCU-1 on real Indic
sentences** (7.3–8.8 bits/char, JOSS paper table, §1). Validate the exact number against your own
corpus before quoting it in the final pitch — the 5–6 figure is a well-grounded target range, not
yet a measured VarnaCode result.

**How to position this honestly in the pitch:**
- **Don't** claim to have beaten Unishox2 "in general" — Unishox2 remains the stronger choice
  for mixed-script/emoji/URL/English content, and it's already production-proven inside
  Meshtastic's official firmware. Overclaiming here is checkable (the JOSS paper table is public)
  and would visibly damage credibility with any judge who looks it up.
- **Do** claim the narrower, true thing: for the specific problem VarnaCode targets — single
  known-language Indic sentences, language declared out-of-band in the frame header — a
  frequency-tuned static code beats general-purpose Unicode short-string compressors (Unishox2,
  SCSU, BOCU-1) by construction, because those generic schemes pay a real, measured 15–20%+ tax
  for handling scripts/content they don't need to handle in this use case, and lands VarnaCode's
  Indic path below the GSM 7-bit national-language SMS baseline that carriers already ship —
  something none of Unishox2/SCSU/BOCU-1 do on the measured Indic numbers.
- **Do** cite the LoRa SF12 arithmetic (51-byte cap → 17 chars at UTF-8 vs ~63–74 chars at
  5.5–6.5 bits/char) as the headline demo number — it's concrete, verifiable, and makes the
  bandwidth case vivid without needing to relitigate every competing algorithm.
- **Do** credit Unishox2 explicitly as the closest prior art and explain the one specific thing
  VarnaCode changes (frequency-tuned per-language Indic coding vs. generic Unicode delta coding)
  — judges familiar with the space (there's a real chance someone knows Unishox2/Meshtastic) will
  trust a scoped, cited improvement far more than an unscoped "we invented Indic compression"
  claim.
