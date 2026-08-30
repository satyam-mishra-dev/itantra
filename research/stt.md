# On-device / lightweight Speech-to-Text (ASR) for Indian Languages — Research

Target: iTantra (SIH 2026) — offline STT+TTS Android app over low-bitrate radio links, 10 languages
(Hindi, Gujarati, Marathi, Kannada, Malayalam, Tamil, Telugu, Odia, Bengali, English), must run
fully offline on low/mid-range Android phones.

---

## 1. AI4Bharat models (IndicConformer, IndicWav2Vec, IndicWhisper, IndicVoices)

### IndicConformer (current flagship, actively maintained)
- **Architecture**: Conformer encoder + hybrid CTC/RNNT decoder. Two published sizes:
  - Per-language checkpoints: ~120M-param encoder (17 conformer blocks, dim 512).
  - `ai4bharat/indic-conformer-600m-multilingual`: 600M params, single multilingual model.
  - Source: https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual
- **Languages**: all 22 official Indian languages (covers all 10 iTantra languages except plain
  English, which is Whisper/other-model territory — though IndicConformer's Hindi/Indic-English
  code-mixed handling is decent).
- **WER**: Hindi WER 13.2 on the ARTPARK-IISc/Vaani-Benchmark-V1.0 (per HF model card). No full
  per-language WER table surfaced in the card itself; check AI4Bharat's Vistaar benchmark for
  broader numbers (below).
- **License**: MIT — usable commercially/for hackathon without restriction.
- **ONNX**: Yes — official card documents both fp32 and int8 ONNX export
  (`onnxruntime==1.20.1`). This is the most mobile-ready AI4Bharat ASR model.
  - Community conversions exist for sherpa-onnx (NeMo-CTC format): `trysem/indicconformer-120m-onnx`
    on Hugging Face — ~493 MB per language (fp32; this is the CTC-only export, no RNNT decoder,
    which is why it's larger relative to the 120M param count — likely un-quantized). A published
    Malayalam sherpa-onnx-ready build also exists from the community.
  - Source: https://github.com/k2-fsa/sherpa-onnx/discussions/3199
- Also listed on India's gov model registry (AI Kosh) per-language, e.g. Assamese/Konkani/Nepali
  cards at aikosh.indiaai.gov.in — confirms MeitY/AI Kosh distribution channel exists for offline
  deployment approval/credibility in a government hackathon context.

### IndicWav2Vec (older, wav2vec2-style, self-supervised)
- **Languages**: pretrained on 40 Indian languages; fine-tuned ASR released for 9
  (Bengali, Gujarati, Hindi, Marathi, Nepali, Odia, Tamil, Telugu, Sinhala) + community Kannada/Malayalam.
  Covers 8 of the 10 iTantra languages directly (missing native English handling by design).
- **WER** (MUCS/MSR/OpenSLR benchmarks, no LM):
  | Lang | MUCS | Notes |
  |---|---|---|
  | Hindi | 16.0 | 14.7 with LM |
  | Gujarati | 20.5 (MUCS) / 26.2 (MSR) | 11.7 with LM |
  | Marathi | 19.3 | |
  | Tamil | 27.3 | |
  | Telugu | 29.3 | |
  | Bengali | 16.6 | |
  | Nepali | 11.9 | |
  - Source: https://github.com/AI4Bharat/IndicWav2Vec
- **License**: MIT.
  ONNX/Torchscript/mobile export are explicitly listed as **"Coming soon"** in the repo — i.e.
  not production-ready for on-device export today. Treat as a research reference, not a deployment
  candidate, unless you do the ONNX conversion work yourselves (wav2vec2 CTC models convert fairly
  routinely via HF `optimum`, but AI4Bharat hasn't shipped official artifacts).

### IndicWhisper (Whisper fine-tuned on Indic data)
- Fine-tuned versions of Whisper (small/medium/large-v2) per language, e.g.
  `vasista22/whisper-hindi-large-v2`, `whisper-hindi-small`, `whisper-hindi-medium` on HF.
- On the **Vistaar benchmark** (13 public Indic ASR test sets, 12 languages, 10,700+ hrs of
  train data), IndicWhisper WER ranges from **13.6 (Hindi)** average up to **48 (Sanskrit)**,
  varying heavily by benchmark subset (Kathbath, Kathbath-Hard, FLEURS, CommonVoice, IndicTTS,
  MUCS, Gramvaani). Source: https://arxiv.org/pdf/2305.15386 (Vistaar paper).
- Since these are full Whisper-architecture fine-tunes (encoder-decoder, small = 244M params
  minimum), they inherit whisper.cpp's mobile export path (GGML/GGUF, see §2) but are heavier
  than IndicConformer for the same accuracy tier — decoder autoregression is slower than
  CTC/streaming-transducer decoding on CPU.

### IndicVoices (dataset, not a model — but the reason the above models exist)
- 7,348 hours of natural/spontaneous speech (9% read, 74% extempore, 17% conversational),
  16,237 speakers, 145 districts, 22 languages. 1,639 hrs already transcribed at release
  (median 73 hrs/language). Paper: https://arxiv.org/abs/2403.01926
- Companion **IndicVoices-R** (TTS-oriented derivative): 1,704 hrs, 10,496 speakers, 22 languages,
  paper: https://arxiv.org/pdf/2409.05356 — relevant if iTantra's TTS side also wants
  AI4Bharat-lineage voice data.
- Practical takeaway: this is why IndicConformer's real-world/noisy-mic WER should be trusted
  more than lab-benchmark-only models — the training data itself includes extempore/spontaneous
  speech, which is closer to a radio-link push-to-talk use case than read-speech corpora like
  FLEURS/CommonVoice.

---

## 2. Whisper family on mobile

### whisper.cpp (GGML C/C++ port — the standard mobile Whisper path)
- Android integration exists as a prebuilt AAR (no NDK needed):
  https://github.com/ffmpegkit-maintained/whisper — arm64-v8a, API 24+, published to Maven Central.
- ARM NEON SIMD is on by default for arm64 builds.
- **Model sizes**: tiny = 39M params (~75 MB fp16 / ~39 MB q5), base = 74M params (~142 MB fp16 /
  ~74 MB q5) — base literally doubles tiny's params while both stay small enough for phones.
- **RTF on ARM (Raspberry Pi 5, Cortex-A76, comparable to a mid-range phone SoC)**:
  tiny and base run **faster than real-time** (RTF < 1) on CPU-only NEON; small drops to
  **~0.4–0.6× real-time** (i.e. RTF ~1.7–2.5, a 10-min clip takes 17–25 min) — so small is
  **not viable** for a push-to-talk phone app, tiny/base are.
  Source: search-aggregated benchmarks (turingpi.com RK3588 writeup; Medium ARM benchmarking post).
- **Multilingual WER on Indic**: stock (non-fine-tuned) multilingual Whisper is weak on Indic
  scripts without normalization — search results show wildly different numbers depending on
  text normalization: un-normalized Whisper-small WER on FLEURS was reported as high as
  **86.9% (Hindi) / 93.3% (Tamil)**, dropping by **21.9 pts (Hindi) / 41.5 pts (Tamil)** after
  applying Whisper's own text normalizer — i.e. raw WER numbers for Indic scripts are close to
  meaningless without knowing the normalization pipeline. Source:
  https://arxiv.org/pdf/2409.02449 ("What is lost in Normalization?").
  **Conclusion: do not trust stock multilingual whisper-tiny/base WER claims on Indic languages
  at face value** — use IndicWhisper (AI4Bharat fine-tunes) instead if going the Whisper route.

### distil-whisper
- **English only** as of current release; community distillation efforts for other languages
  exist but nothing shipped for Indic languages. Not directly usable for this project's 9
  non-English languages. Source: https://github.com/huggingface/distil-whisper
- There is academic work on "Multilingual DistilWhisper" (language-specific expert distillation,
  arXiv 2311.01070) but no ready-to-download Indic checkpoints found.

### faster-whisper (CTranslate2 backend)
- Multilingual, supports quantized (int8) inference, big speedups on CPU vs vanilla PyTorch
  Whisper. Primarily a desktop/server-CPU tool via CTranslate2 — CTranslate2 does have ARM/Android
  support but it's far less battle-tested for Android than whisper.cpp's GGML path. For an Android
  APK, whisper.cpp (or its ONNX-Runtime equivalents) is the safer integration bet.

**Whisper-family verdict for iTantra**: viable as a *fallback/general* engine (English + code-mixed),
but for the 9 Indic languages, IndicWhisper fine-tunes are mandatory over stock Whisper, and even
then whisper.cpp's encoder-decoder autoregressive decoding is inherently slower/heavier per-token
than a CTC/transducer model at equivalent accuracy — better suited as a secondary/quality-fallback
engine than the primary low-latency engine.

---

## 3. sherpa-onnx / k2 / icefall ecosystem

- **sherpa-onnx** (k2-fsa/sherpa-onnx): unified ASR+TTS+VAD+diarization ONNX Runtime framework
  with **first-class Android support** (Kotlin/Java bindings, no internet needed), plus iOS,
  HarmonyOS, Raspberry Pi, RISC-V, NPU targets. This is the most Android-native of everything
  surveyed here. https://github.com/k2-fsa/sherpa-onnx
- **Streaming architecture**: zipformer-transducer models, typically configured as
  **"chunk-16-left-128"** (16-frame processing chunks, 128 frames of left context) — this is the
  standard low-latency streaming config, giving sub-second incremental latency suitable for
  live/push-to-talk transcription. Source:
  https://k2-fsa.github.io/sherpa/onnx/pretrained_models/online-transducer/zipformer-transducer-models.html
- **Model sizes observed** (encoder-only, various languages): English ~68–338 MB depending on
  variant, Chinese+English bilingual ~174–315 MB, Korean ~121–279 MB, **Bengali
  (`sherpa-onnx-streaming-zipformer-bn-vosk-2026-02-09`) ~87 MB encoder** — Bengali is the only
  directly-relevant iTantra language with an off-the-shelf *streaming* zipformer model found.
- **Indic language coverage gap**: sherpa-onnx's official pretrained-model pages show almost no
  ready-made streaming Indic models beyond Bengali. The community-discussion thread
  (https://github.com/k2-fsa/sherpa-onnx/discussions/3199) surfaces two real paths for the rest:
  1. **Dolphin multi-language CTC models** (converted from DataoceanAI's Dolphin) — cover Hindi,
     Tamil, Telugu, Gujarati, Punjabi, Marathi, Odia, Bengali, Kashmiri, in base/small variants,
     int8-quantized or fp32. **Gap: no Malayalam or Kannada** — a real problem since both are
     iTantra-required languages.
  2. **IndicConformer → sherpa-onnx NeMo-CTC conversion** — community-published, covers all 12
     Indic languages including Malayalam and Kannada, ~493 MB/language (this figure is likely
     unquantized fp32; expect ~120–150 MB after int8, see §6).
  - Neither path is officially blessed/maintained by k2-fsa — both are community conversions,
    so budget QA time and expect to do your own conversion/debugging for the 2 missing languages.
- **k2/icefall** is the training-side toolkit (Kaldi's Python-native successor) used to produce
  these zipformer/conformer models — relevant only if you need to train/fine-tune your own
  streaming model on IndicVoices/Vistaar data; not itself a deployment artifact.

---

## 4. Vosk / Kaldi small models

- Kaldi-based, GMM-free DNN-HMM small models, purpose-built for offline/embedded use.
  Android/iOS/RPi bindings via `vosk-api`. https://github.com/alphacep/vosk-api
- **Confirmed sizes from alphacephei.com/vosk/models** (fetched directly):
  | Language | Small model | Size | Full model | Size |
  |---|---|---|---|---|
  | Hindi | vosk-model-small-hi-0.22 | **42 MB** | vosk-model-hi-0.22 | 1,500 MB |
  | Gujarati | vosk-model-small-gu-0.42 | **100 MB** | vosk-model-gu-0.42 | 700 MB |
  | Telugu | vosk-model-small-te-0.42 | **58 MB** | — | — |
  | Indian English | vosk-model-small-en-in-0.4 | **36 MB** | vosk-model-en-in-0.5 | 1,000 MB |
  - **No Vosk models exist for Marathi, Kannada, Malayalam, Tamil, Odia, or Bengali** — this is a
    hard coverage gap; Vosk only covers 3 of iTantra's 9 non-English target languages
    (Hindi, Gujarati, Telugu) plus Indian-accented English.
- **WER**: not published in official docs for these small models; general community consensus
  (search-aggregated) is that Vosk small models **trail Whisper/Conformer-family models** in
  accuracy, trading accuracy for their very small footprint and low RAM/CPU use — historically
  positioned as "good enough for keyword/command-style recognition," less so for open dictation.
- **Verdict**: Vosk's small footprint (36–100 MB) and proven low-resource Android deployment
  track record make it attractive, but the missing 6/9 language coverage disqualifies it as a
  primary engine for iTantra unless you're willing to train/release your own Vosk-format models
  for Marathi/Kannada/Malayalam/Tamil/Odia/Bengali (nontrivial — Kaldi model-building is a
  heavier lift than fine-tuning an existing conformer).

---

## 5. Bhashini / MeitY / C-DAC government models

- **Bhashini**: Government of India's Digital Public Infrastructure for Indian languages (under
  MeitY), aggregating APIs + a model hub for ASR/TTS/NMT across all 22 scheduled languages, with
  contributions from AI4Bharat, C-DAC, IIIT-H and others.
- MeitY + C-DAC (Pune) provided GPU compute (Param Siddhi supercomputer nodes) that funded much of
  AI4Bharat's open-source ASR training — i.e. **IndicConformer/IndicWav2Vec effectively *are* the
  open-source output of the Bhashini ecosystem**, released under MIT on Hugging Face and mirrored
  on India's AI Kosh registry (aikosh.indiaai.gov.in) per-language. There isn't a *separate*
  meaningfully-different "Bhashini model" to evaluate — Bhashini is primarily an API/orchestration
  layer over these same AI4Bharat models, most of which are only exposed as cloud APIs
  (not bundled for offline redistribution) via the Bhashini API itself.
- **On-device feasibility**: cloud-hosted Bhashini API is **not usable for iTantra's offline
  requirement at all** — it requires internet connectivity to their servers. The only realistic
  path to an "MeitY/Bhashini-lineage" offline model is downloading the underlying open-source
  AI4Bharat checkpoints (IndicConformer, MIT-licensed, ONNX-exportable — see §1) directly from
  Hugging Face/AI Kosh and bundling them in the APK, not calling Bhashini's live API.
- One community example worth noting as a feasibility proof: **VEXYL-STT**, a self-hosted server
  wrapping IndicConformer, runs on **2 vCPU / 4 GiB RAM, CPU-only, no GPU** in production
  (Google Cloud Run) — confirms IndicConformer inference is CPU-viable at that scale, though this
  is a server deployment (2.4 GB unquantized model), not a phone-class deployment; still a useful
  sanity check that the model family isn't inherently GPU-bound.
  Source: https://medium.com/@anilmathewm/vexyl-stt-free-self-hosted-indian-language-speech-to-text-server-f2909003aaf6
- **Pitch angle for judges**: bundling AI4Bharat/IndicConformer (a MeitY/C-DAC-funded, Bhashini-
  ecosystem, government-endorsed open model) fully offline is a stronger SIH story than a foreign
  Whisper checkpoint — same underlying research lineage, but you can legitimately claim "built on
  India's national language AI infrastructure" while still meeting the fully-offline constraint,
  since the model weights (not the Bhashini API) are what you'd actually ship.

---

## 6. Quantization (int8) for ASR models

- **Whisper-small, dynamic int8 (Quanto)**: **~57% size reduction**, and WER *improved* slightly
  over the fp32 baseline in one study's config — i.e. dynamic quantization is close to free here.
  Source: https://arxiv.org/abs/2511.08093 ("Quantizing Whisper-small: How design choices affect
  ASR performance").
- **Whisper, PyTorch dynamic int8 on CPU**: RTF **0.077 vs 0.121 fp32 baseline (36.4% faster)**,
  "only a small accuracy drop." Same source family.
- **int8 k-quant Whisper variant**: **8.01% WER vs 8.03% fp32 ONNX baseline** (essentially
  identical) with **48% model-size reduction** — this is the strongest single data point for
  "quantize aggressively, pay almost nothing."
- **Conformer AED models** (speaker-adapted quantization study): **7× size reduction** with only
  **+1% extra speaker-specific params**, achieving **15.1% relative WER reduction on Whisper /
  23.3% relative WER reduction on Conformer** in their quantized+adapted configuration (i.e.
  quantization combined with light adaptation can even outperform full precision, not just match
  it). Source: https://arxiv.org/html/2408.03979 ("Speaker Adaptation for Quantised End-to-End
  ASR Models").
- **Memory impact example** (whisperx-tiny): fp32 4,273 MB peak RAM → fp16 4,028 MB → int8
  3,944 MB — note this is mostly *runtime/activation* memory in that specific pipeline, not just
  weight storage, so don't assume quantization alone solves phone RAM pressure; combine with a
  smaller model (tiny/base, not small/medium) regardless.
- **Bottom line for iTantra**: int8 dynamic/static quantization is a "do it, basically free"
  optimization for both IndicConformer and any Whisper-family model — expect **45–57% size cut**
  and **WER changes in the ±1 point range** (sometimes even improving), consistent across every
  paper found. Apply it to whichever model you pick; it is not an accuracy-vs-size tradeoff
  worth agonizing over at this level, it's close to strictly free.

---

## 7. VAD (Voice Activity Detection)

### Silero VAD
- **Size**: ~1.8 MB (JIT) / **~5.7 MB on disk** (per one source citing 1.49M params); a widely
  cited newer figure for v6 is **1.2 MB, 309K params** with CoreML/MLX/ONNX builds.
  Source: https://github.com/snakers4/silero-vad ; https://soniqo.audio/guides/vad
- **Speed**: processes a 30ms audio chunk in **<1ms on CPU**, faster still via ONNX Runtime —
  utterly negligible compute cost for a phone, even mid/low-range.
- **Accuracy**: deep-learning based (trained on speech from 6,000+ languages per the repo claims),
  more accurate than WebRTC VAD at low false-positive-rate operating points (5%/1% FPR); WebRTC
  only pulls ahead at very permissive thresholds (25% FPR, i.e. WebRTC lets more false positives
  through to get the same true-positive rate). Source (comparison):
  https://picovoice.ai/blog/best-voice-activity-detection-vad/ and
  https://github.com/wiseman/py-webrtcvad/issues/68 (quality benchmark issue thread).
- **ONNX/mobile**: ONNX Runtime has ARM/Android/edge builds; one source notes Silero is "heavy
  for power-constrained mobile" **only relative to WebRTC**, and specifically because of the
  PyTorch/ORT runtime dependency, not the model itself — at ~1–6 MB and sub-ms per-chunk cost,
  this is a non-issue in absolute terms for any phone iTantra targets.

### WebRTC VAD
- Classical GMM/signal-processing based (energy, spectral shape, zero-crossing rate, pitch) —
  **no neural network, essentially zero footprint**, the most lightweight option that exists.
- Lower accuracy than Silero at conservative (low-false-positive) thresholds, but "the de facto
  standard [WebRTC VAD] has mostly been *replaced* by Silero VAD in new projects due to superior
  accuracy at similar speed" per aggregated sources.

**Verdict for iTantra**: use **Silero VAD** for pause-based sentence segmentation / endpointing —
at ~1–6 MB and sub-millisecond-per-chunk cost it is effectively free on any Android target, and
meaningfully more accurate than WebRTC VAD, which matters directly for push-to-talk endpoint
detection (cutting off speech early vs. waiting too long are both bad UX over a radio link where
every extra second matters for bandwidth/latency).

---

## 8. Streaming vs non-streaming ASR — tradeoffs for push-to-talk

- **Non-streaming (offline/batch) models** (e.g. Whisper encoder-decoder, IndicConformer's
  full-context CTC/RNNT mode) see the *entire* utterance before decoding — highest accuracy,
  because bidirectional context resolves ambiguity that a causal/streaming model can't. But
  latency = full utterance duration + decode time; for a push-to-talk radio app this means the
  user waits after releasing the talk button.
- **Streaming models** (zipformer-transducer, streaming Conformer with limited right-context)
  emit partial hypotheses as audio arrives, at the cost of accuracy — restricting right-context
  is exactly what degrades WER relative to the same architecture run non-streaming. Typical
  sherpa-onnx streaming configs use small chunks with limited lookahead (the "chunk-16-left-128"
  pattern noted in §3) to bound latency to roughly one chunk-worth of audio, i.e. low
  hundreds-of-ms, not seconds.
- **Endpointing is the real design problem for push-to-talk**, not raw streaming vs non-streaming:
  you need to detect "user has stopped talking" to know when to finalize a transcript/segment a
  sentence. Aggressive endpointing = lower latency but risks cutting off trailing speech;
  conservative endpointing = safer but adds dead time. Source:
  https://arxiv.org/html/2505.17070 ("Improving endpoint detection in end-to-end streaming ASR").
- **Practical recommendation for a push-to-talk (not continuously-open-mic) UX**: iTantra's use
  case is fundamentally different from a live-dictation app — the user explicitly presses
  talk/release, so you already have an explicit utterance boundary from the UI, not from VAD.
  This changes the calculus:
  - You do **not strictly need a streaming ASR model** for correctness — you know exactly when
    the utterance starts/ends from the button, so you can run **non-streaming inference on
    button-release** and simply show a "transcribing..." spinner for the (short, since utterances
    over a radio link should be short by nature) duration.
  - However, running the ASR *incrementally while the button is still held* (streaming) lets you
    start decoding before release, so total perceived latency after release is much smaller —
    valuable given the "low-bitrate radio link" framing where every bit of decode-then-transmit
    latency compounds.
  - **VAD still matters inside a held-button recording** to auto-segment a long transmission into
    sentence-level chunks for incremental transmission over the low-bitrate link, rather than
    waiting for the entire recording to finish — this is the actual reason to run Silero VAD in
    this architecture, more than classic "hands-free" endpointing.
  - Given that, a **hybrid** approach — streaming zipformer/conformer for immediate partial
    feedback + VAD-based sentence chunking for transmission segmentation, with the option to
    re-run non-streaming decode on the full utterance for a final "cleaned up" transcript if
    latency budget allows — is the standard production pattern (used by Amazon/Google server ASR
    stacks per the endpointing literature) and is straightforwardly implementable with
    sherpa-onnx, which supports both streaming and non-streaming decode from compatible model
    families.

---

## Recommended stack

**Primary ASR: AI4Bharat IndicConformer (600M multilingual, or per-language ~120M checkpoints),
int8-quantized ONNX, run via sherpa-onnx's Android bindings.**

Why, weighed against the alternatives surveyed:

1. **Language coverage is the deciding factor.** IndicConformer is the *only* option here that
   natively covers all 9 non-English iTantra languages (Hindi, Gujarati, Marathi, Kannada,
   Malayalam, Tamil, Telugu, Odia, Bengali) from one model family with one license (MIT). Vosk
   covers only 3/9. sherpa-onnx's off-the-shelf Dolphin models cover 7/9 but explicitly miss
   Malayalam and Kannada. Stock Whisper covers all languages nominally but with unreliable
   accuracy on Indic scripts unless you swap in IndicWhisper fine-tunes per-language (9 separate
   checkpoints to manage instead of 1).
2. **It's already ONNX-native with an official int8 export**, unlike IndicWav2Vec (ONNX marked
   "coming soon" in the repo — not shippable today) — so no bespoke conversion risk for the core
   model, only for the sherpa-onnx runtime wrapper (community-maintained, budget QA time here).
3. **Architecture fits the latency need.** CTC/RNNT hybrid decoding is cheaper per-token on CPU
   than Whisper's autoregressive encoder-decoder, and sherpa-onnx exposes both streaming and
   non-streaming decode paths from compatible checkpoints — matching the hybrid
   streaming-partial + non-streaming-final pattern recommended in §8 for push-to-talk.
4. **Quantization is close to free here** (§6: 45–57% size cut, ~±1pt WER) — apply int8 to bring
   the ~493 MB community fp32 sherpa-onnx conversion down to a realistic **~120–150 MB per
   language** for on-device bundling. Ship only the languages the user selects/downloads, not all
   9 at once, to keep APK/first-run size sane on low-end phones.
5. **English**: use IndicConformer's own English support if adequate (it's in the 22-language
   suite), or fall back to whisper.cpp tiny/base (both run faster-than-real-time on ARM per §2)
   for English specifically if IndicConformer's English WER underperforms — English is the one
   language where a dedicated, heavily-benchmarked model (Whisper) has a real edge and the
   accuracy-normalization concerns from §2 don't apply (no script-normalization ambiguity for
   English).
6. **VAD: Silero VAD** (§7) for both endpoint segmentation of long push-to-talk holds and
   pause-based sentence chunking — negligible size/compute cost, materially better accuracy than
   WebRTC VAD, ONNX Runtime already in the dependency tree via sherpa-onnx so no extra runtime.
7. **Fallback/quality-check engine**: keep IndicWhisper (AI4Bharat's Whisper fine-tunes) in your
   back pocket as a per-language accuracy comparison during development/testing (§1), even if not
   shipped in the final APK — useful to sanity-check IndicConformer's transcripts are competitive
   before committing.
8. **Narrative bonus**: IndicConformer is literally the MeitY/C-DAC/Bhashini-funded open-source
   output (§5) — "built on India's own national language AI infrastructure, running fully offline
   on-device" is a stronger SIH pitch than "we bundled OpenAI's Whisper."

**What to explicitly punt on**: don't build custom Vosk/Kaldi models for the missing 6 languages
(too heavy a lift for a hackathon timeline) and don't chase distil-whisper (no Indic checkpoints
exist yet). If sherpa-onnx integration proves too unstable given its community (not official)
IndicConformer conversion, the fallback plan is direct ONNX Runtime Mobile integration of
AI4Bharat's officially-exported int8 ONNX checkpoints, bypassing sherpa-onnx's wrapper entirely —
more integration work, but removes the community-conversion risk.
