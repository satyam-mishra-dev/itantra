# Receiver-language rendering for iTantra — research (2026-09-15)

Thesis under test: "unit on the wire is language-neutral enough that the receiver renders it in its own
Indian language, fully offline, open-source-only, on a budget Android phone; the extra cost is
measurable and acceptable."

## TL;DR
- Verdict: (a) correct and defensible within ~1 week — but only if the MT model is Mozilla/Bergamot
  "tiny" (17 MB int8, English pivot), NOT IndicTrans2 direct Indic-Indic (~330 MB int8, no Android
  runtime today).
- Reframe the "unit on the wire": keep sender-language text on the wire (unchanged bytes, lossless for
  the same-language majority case) plus a 1-byte language tag; translation is a receiver-side decision.
  Do not put a "codebook" on the wire for free speech; use codes only where messages are already
  structured (CAP alerts, roll-call/ACK).
- Jury metric: FLEURS is n-way parallel (join on `id`) and CC-BY-4.0; IN22 is n-way parallel across 22
  languages and CC-BY-4.0. Report MT-only chrF++ and end-to-end CER deltas vs the same-language pipeline.

## 1. Offline open-source MT options (measured sizes from HF API, 2026-09-15)

### 1a. IndicTrans2 (AI4Bharat) — MIT, HF repos gated (`gated: auto`, click-through)
| Model | Params | fp32 on HF | int8 (ONNX/CT2) | Notes |
|---|---|---|---|---|
| indictrans2-indic-indic-dist-320M | ~320M (paper: "about 350M") | 1283.5 MB | ~330 MB est. (no public int8 conversion found) | direct Indic→Indic, 18L enc/18L dec, d=512, ffn=2048 |
| indictrans2-en-indic-dist-200M | 211M | 1098.4 MB | 209 MB ONNX int8 (enc 76 + dec-with-past 133) [naklitechie] | en→22 Indic |
| indictrans2-indic-en-dist-200M | 211M | 913.4 MB | ~210 MB est. (adalat-ai CT2 fp32 = 847 MB) | 22 Indic→en |
| indictrans2-indic-indic-1B | 1.2B | 4832.5 MB | ~1.2 GB | out of budget |
| indictrans2-indic-en-1B ONNX int8 [akki244] | 1B | — | 218 MB (enc 121.8 + dec 96.3) | ran on Pixel 7: enc 50-150 ms, 20-40 ms/token, 0.6-1 s per 20-token sentence, ~400 MB peak RAM |

Sources: https://huggingface.co/ai4bharat/indictrans2-indic-indic-dist-320M ,
https://huggingface.co/naklitechie/indictrans2-en-indic-dist-200M-ONNX-int8 ,
https://huggingface.co/akki244/indictrans2-onnx-int8 ,
https://huggingface.co/adalat-ai/ct2-rotary-indictrans2-en-indic-dist-200M ,
https://github.com/AI4Bharat/IndicTrans2 (licences: checkpoints MIT, IN22 CC-BY-4.0).

Paper (TMLR 12/2023, https://arxiv.org/abs/2305.16307) — chrF++, Indic-Indic, Dist-M2M (~350M) column:
| Target lang | FLORES-200 xx→lang | IN22-Gen xx→lang | IN22-Conv xx→lang | IN22-Gen lang→xx |
|---|---|---|---|---|
| ben | 43.7 | 43.2 | 40.5 | 41.2 |
| hin | 46.8 | 47.1 | 41.7 | 42.3 |
| tam | 46.1 | 42.6 | 34.9 | 39.3 |
| tel | 46.0 | 42.9 | 37.9 | 41.9 |
| mal | 45.1 | 42.0 | 38.0 | 40.6 |
(Table 19-21; "xx→lang" = average over all Indic sources into that language. Per-pair hi→bn etc. are not
printed in the paper; must be computed from the released IN22 outputs or re-run.) Direct M2M costs ~1
chrF++ vs pivot at half the inference; Dist-M2M costs ~1-2 more. Distilled En/Indic models lose only
0.17/0.87 chrF++ avg vs 1B (Table 22).

Blockers for IndicTrans2 on a phone within a week:
- No Android runtime for CTranslate2 (issue #1683 open since Apr-2024, no maintainer reply:
  https://github.com/OpenNMT/CTranslate2/issues/1683). sherpa-onnx is speech-only. You would use
  `com.microsoft.onnxruntime:onnxruntime-android` (Maven Central, v1.24.x:
  https://central.sonatype.com/artifact/com.microsoft.onnxruntime/onnxruntime-android) and write the
  greedy/beam decode loop with KV-cache yourself.
- Pre/post-processing is not just SentencePiece: IndicTransToolkit does Indic script unification to
  Devanagari (indic_nlp_library), placeholder entity replacement, and back-transliteration. Porting it
  is real work (a TypeScript port exists: https://github.com/Jaswanth-Reddy-2006/Yaad/pull/1).
- Size: 330 MB int8 for direct; or 2 x 210 MB via en pivot. Vocab pruning to 2 scripts could cut the
  embedding tables (est. ~190 M of the 320 M params are embeddings) but that is unproven engineering.

### 1b. Mozilla Firefox Translations / Bergamot "tiny" models — the practical option
Registry https://storage.googleapis.com/moz-fx-translations-data--303e-prod-translations-data/db/models.json
(generated 2026-09-14). Released Indic models (all X↔en; NO Indic↔Indic direct):
| Pair | arch | int8 file | params | FLORES200+ chrF++ | COMET22 |
|---|---|---|---|---|---|
| hi-en / en-hi | tiny | 17.1 MB | 16M | 60.5 / 58.1 | 0.872 / 0.790 |
| bn-en / en-bn | tiny | 17.1 MB | 16M | 55.3 / 49.9 | 0.855 / 0.847 |
| te-en / en-te | tiny | 17.1 MB | 16M | 58.2 / 56.7 | 0.851 / 0.851 |
| ml-en / en-ml | tiny | 17.1 MB | 16M | 55.7 / 53.6 | 0.849 / 0.868 |
| kn-en / en-kn | tiny | 17.1 MB | 16M | 54.8 / 53.2 | 0.843 / 0.843 |
| gu-en / en-gu | tiny | 17.1 MB | 16M | 58.6 / 52.5 | 0.870 / 0.861 |
| ta-en / en-ta | base-memory / tiny | 31.6 / 17.1 MB | 31M / 16M | 54.9 / 55.1 | 0.843 / 0.879 |
| mr-en / en-mr | base-memory | 31.6 MB | 31M | 58.8 / 51.1 | 0.864 / 0.760 |
| ur-en / en-ur | base-memory | 31.6 MB | 31M | 57.5 / 50.7 | 0.848 / 0.832 |
Architecture: 6-layer enc / 2-layer SSRU dec, emb 256, ffn 1536, 32k tied vocab, plain SentencePiece,
int8 via intgemm (x86) or ruy (aarch64) — https://github.com/jerinphilip/slimt . Licence: repo and
pipeline MPL-2.0 (https://github.com/mozilla/translations, https://github.com/mozilla/firefox-translations-models);
models are already redistributed by a GPL-3 F-Droid Android app (proof it runs on Android via slimt):
https://github.com/DavidVentura/offline-translator , https://f-droid.org/packages/dev.davidv.translator .
Any Indic→Indic pair = two hops through English: 34 MB per pair, ~1 chrF++ loss per pivot is the
IndicTrans2 paper's own finding for pivot vs direct (Section 7.5), so expect hi→bn end-to-end around
the low-to-mid 40s chrF++ on FLORES — same ballpark as IndicTrans2-Dist-M2M at 1/10 the size.
Caveats: en-hi COMET 0.79 and en-mr 0.76 are the weak links; Odia/Assamese/Punjabi are absent.

### 1c. Ruled out
- NLLB-200-distilled-600M: CC-BY-NC-4.0 (non-commercial — an ISRO/NDMA deployment fails the licence),
  622.6 MB CT2 int8 (https://huggingface.co/mijuanlo/nllb-200-distilled-600M-ct2-int8 ,
  https://huggingface.co/facebook/nllb-200-distilled-600M).
- OPUS-MT opus-mt-inc-inc (Apache-2.0, 247 MB fp32): Indo-Aryan only (asm/hin/mar/urd trained), no
  Dravidian, Tatoeba hin-mar BLEU 28.1, hin-asm 9.1 — https://huggingface.co/Helsinki-NLP/opus-mt-inc-inc .
- M2M100-418M: 1.9 GB fp32, MIT, weak on Indic; no reason to prefer over the above.
- "One shared encoder, 22 languages, <150 MB int8": exists only as IndicTrans2-Dist-M2M at ~330 MB.
  Nothing public meets 150 MB for direct Indic↔Indic.

## 2. Alternative: constrained "emergency register" codebook
Prior art (all are structured-message, not free-speech, systems):
- CAP (ITU-T X.1303 / OASIS) — language-neutral enumerated fields: category, urgency (5), severity (5),
  certainty (5), responseType (8), plus free text `<info>` per language. SACHET (C-DOT/NDMA) already
  renders CAP into 19-23 Indian languages: https://sachet.ndma.gov.in/About ,
  https://www.undrr.org/resource/case-study/mobile-technology-expanding-inclusive-early-warning-communication .
  iTantra already bridges CAP → speech; the enumerated fields are already the codebook.
- FCC WEA multilingual order (2025): fixed fillable alert templates in 13 languages, i.e. a template
  index + slot values is what a regulator adopted for cross-language alerts:
  https://www.fcc.gov/sites/default/files/FillableAlertTemplates-WEA-MultilingualOrder.pdf .
- British Red Cross / DH "Emergency Multilingual Phrasebook": 62 phrases x 36 languages
  (https://health.wyo.gov/wp-content/uploads/2016/04/43-5873_DH_4073282.pdf) — the classic curated codebook.
- NATO APP-11 / ADatP-3 MTFs (400+ message formats, values-only on the wire, designed for HF/VHF
  tactical radio): https://systematic.com/int/industries/defence/products/domains/interoperability/app11-and-adatp3/ ,
  https://www.isode.com/whitepaper/c2-systems-use-of-mtf-and-messaging/ ; brevity codes APP-7 /
  AFTTP 3-2.5: https://static.e-publishing.af.mil/production/1/lemay_center/publication/afttp3-2.5/afttp3-2.5.pdf .
- Semantic/token communication (TokCom, codebook-index-on-the-wire, 2025-26):
  https://arxiv.org/html/2502.12096 , https://arxiv.org/pdf/2510.07108 — vocabulary for the pitch, but
  these are image/LLM-token systems, no multilingual speech results to borrow.
- Crisis MT (Haiti 2010 cookbook; COVID-19 MT https://arxiv.org/pdf/2005.00283): lesson was that free-text
  MT + terminology lists beat phrasebooks once messages leave the template.

Coverage numbers: no public corpus gives "X% of disaster/field-ops utterances covered by N phrases" for
Indian languages. IN22-Conv (1503 sentences, 16 everyday domains) and IndicVoices (12k h, 22 langs,
role-play prompts) have no disaster/field-ops split. Any coverage figure you produce in a week will
come from your own utterance list and a jury will (rightly) call it circular. Recommendation:
- Codebook only for already-structured traffic: CAP fields, roll-call/ACK (9 B), a ~32-entry
  "tactical" set (SOS / need medic / water / all-clear / move to <grid>) with slot values. 1-2 B index.
- Everything else: sender text on the wire + receiver-side MT. Never "untranslated" silently: header bit
  `TRANSLATED` set by the receiver's UI, not the wire — the wire never changes.

## 3. Jury-grade metric protocol
Facts confirmed:
- FLEURS (google/fleurs, CC-BY-4.0): "utterances correspond to n-way parallel sentences", `id` field is
  shared across language configs (FLORES-101 sentence id); Indian configs: as_in, bn_in, gu_in, hi_in,
  kn_in, ml_in, mr_in, or_in, pa_in, ta_in, te_in, ur_pk. https://huggingface.co/datasets/google/fleurs
- IN22 (CC-BY-4.0): n-way parallel across English + 22 Indic; IN22-Gen 1024 sentences (13 domains),
  IN22-Conv 1503 sentences (16 conversational domains). https://github.com/AI4Bharat/IndicTrans2
Protocol (hi→bn shown; repeat for hi→ta, hi→te, hi→ml, bn→hi):
1. Text-only MT: IN22-Conv hin_Deva → MT → compare with ben_Beng reference, sacreBLEU chrF++
   (`--chrf-word-order 2`) + chrF; report against IndicTrans2 paper Table 21 (xx→ben Dist-M2M 40.5) as
   the published reference point. Also run on FLORES-200 devtest for a second number.
2. End-to-end speech: FLEURS test, inner-join hi_in and bn_in on `id` (expect a few hundred pairs;
   verify by eyeballing 10 pairs). hi audio → IndicConformer hi STT → VarnaCode → wire → decode →
   MT hi→bn → Bengali TTS → IndicConformer bn STT → CER vs FLEURS bn `transcription`. Report three
   CERs side by side: (a) same-language pipeline bn→bn (your existing 4.0%), (b) cross-language
   hi→bn, (c) MT-text CER without TTS/STT. (b)-(a) is the honest "cost of translation" the jury sees.
3. Also report bytes/sentence on the wire (unchanged), receiver added latency (ms, median/p95 on the
   budget phone), and pack size delta. Human sanity check: 30 sentences rated by one Bengali speaker
   (adequacy 1-5) — cheap, and juries trust it more than chrF.
Caveat: CER after TTS→STT conflates MT errors with TTS intelligibility; that is why (c) is included.

## 4. Cost model on a 4 GB phone (STT 140 MB + TTS 63 MB already resident)
| Option | Pack per pair | RAM added (est.) | Latency / sentence | Runtime |
|---|---|---|---|---|
| Bergamot tiny, hi→en→bn | 34 MB (17+17); all 9 Indic langs ↔ en = ~200 MB | ~60-120 MB | est. <300 ms on budget ARM (16M params, 2 hops) — measure | slimt C++ via JNI (ruy), proven on Android |
| IndicTrans2 en/indic dist pivot | ~420 MB | ~600-800 MB | ~2 x (0.6-1 s Pixel-7-class for 1B; dist ~3x faster) | onnxruntime-android + own decode loop |
| IndicTrans2 Dist-M2M direct | ~330 MB | ~500-600 MB (scaling akki244's 218 MB → 400 MB peak) | ~0.3-0.5 s Pixel-7-class, 2-3x on budget SoC | same |
On a 4 GB phone the app already holds roughly 300-400 MB PSS for STT+TTS; adding 500+ MB puts a
foreground app near the point where lmkd kills it under memory pressure
(https://source.android.com/docs/core/perf/lmkd). The 17 MB models are within noise.

## 5. Verdict
(a) Correct and defensible in ~1 week — with Bergamot tiny hi/bn/ta/te/ml/kn/gu ↔ en (MPL-2.0 repo,
17 MB int8 each) through slimt on Android; sender-language text stays on the wire, receiver pivots
through English. Numbers you can show: pack +34 MB/pair, RAM +~100 MB, latency +~0.2-0.5 s, chrF++ ~40s
vs published 40-47 for a model 10x larger, end-to-end CER delta vs same-language baseline.
Not (b): IndicTrans2 direct is the "too heavy" path, but the fallback is not a phrasebook — it is the
pivot model above. Not (c): the thesis is wrong only in its wording. "Language-neutral unit on the wire"
is unnecessary and harmful: sender text is already the neutral unit once tagged, and translating at the
sender would degrade the same-language majority case. Make the wire the same; make the receiver smart.

Strongest counter-argument: compounding errors. STT CER already 4-14% (ta 13.9%), then two MT hops on
noisy, unpunctuated, code-mixed field speech, then TTS. hi→ta or hi→ml end-to-end could land at 25-35%
CER, at which point a Tamil listener may prefer the untranslated Hindi audio over confident wrong
Tamil. Mitigation you must build and show: confidence gate (STT confidence and MT length-ratio/round-trip
check) that falls back to reading the source text aloud with a spoken "[untranslated]" tag, and the
human adequacy rating on 30 sentences. If the gate fires on >30% of ta/ml sentences, ship translation
for hi/bn/te/gu only and say so.

Second counter-argument: licence hygiene. IndicTrans2 is MIT but HF-gated; Bergamot models sit under an
MPL-2.0 repo trained on OPUS/HPLT data — record provenance per model in the README before the demo.
