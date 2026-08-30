# On-device TTS for iTantra (10 Indian languages, offline, low/mid Android)

Target languages: Hindi, Gujarati, Marathi, Kannada, Malayalam, Tamil, Telugu, Odia, Bengali, English.
Constraint: fully offline, low/mid-range Android phones, open-source only (PS requirement — NC licenses are disqualifying for shipped models, fine only for prototyping/eval).

---

## 1. Piper TTS

- **Architecture**: single-speaker/multi-speaker VITS (end-to-end, non-autoregressive: text → mel → waveform in one flow, no separate vocoder step). Runs as a single ONNX graph.
- **Model sizes** (from `voices.json` on `rhasspy/piper-voices`, actual bytes measured):
  - `low` quality: ~63.1 MB (16kHz)
  - `medium` quality: ~63.2–63.5 MB typical single-speaker, ~76–78 MB for multi-speaker sets (22kHz)
  - `high` quality: ~114–137 MB (22kHz, best quality, slowest)
  - So a **medium** voice (the practical sweet spot) is consistently **~60–65 MB** per language/speaker.
- **RTF on ARM**: ~0.19–0.2 on Raspberry Pi 5 CPU (≈5x faster than real-time); Pi 4 works but lags on medium/high voices. No direct low/mid-range-phone-SoC benchmark found, but phone CPUs (even budget) generally outperform a Pi 4, so sub-0.3 RTF on a mid-range Android CPU is a reasonable expectation — needs on-device verification, not just extrapolation.
- **License**: MIT (Piper itself). Individual voices vary — most are MIT, some CC0/CC-BY depending on the training dataset; check each voice's `MODEL_CARD` before shipping.
- **Indic language coverage — the important finding**: Piper's actual voice catalog (queried directly from `voices.json`, 57 language variants total) has **real, working medium-quality voices for only 5 of our 9 Indic languages**:
  | Language | Piper voices | Quality |
  |---|---|---|
  | Hindi (hi_IN) | pratham, priyamvada, rohan | medium, ~63 MB each |
  | Malayalam (ml_IN) | arjun, meera | medium, ~63 MB each |
  | Marathi (mr_IN) | google (9 speakers) | medium, ~77 MB |
  | Telugu (te_IN) | maya, padmavathi, venkatesh | medium, ~63 MB each |
  | Bengali (bn_BD) | google (16 speakers) | medium, ~77 MB (Bangladeshi Bengali, not bn_IN — usable but accent mismatch for India) |
  | Urdu (ur_PK) | 2 voices | medium, ~63 MB each (not one of our 10, bonus) |
  | English (en_US/en_GB) | 30+ voices | low/medium/high, 63–137 MB |
  - **No Piper voices exist for Gujarati, Kannada, Tamil, or Odia.** This is a hard gap — Piper alone cannot cover all 10 target languages. Confirmed by pulling the full language-code list from the voices manifest, not just browsing docs (which are frequently stale/incomplete).
- **Mobile deployment**: Piper's ONNX models run directly via ONNX Runtime Mobile or through `sherpa-onnx`'s Android bindings (Kotlin/Java + JNI, prebuilt AARs). A voice (~60 MB) + sherpa-onnx native runtime (~25 MB) ≈ ~85 MB per language installed. For 5 languages that's ~300–400 MB just for Piper voices — need to budget storage or make voice packs downloadable/optional rather than bundled.

Sources: [Piper voices manifest](https://huggingface.co/rhasspy/piper-voices) (queried directly), [piper1-gpl VOICES.md](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/VOICES.md), [sherpa-onnx Piper docs](https://k2-fsa.github.io/sherpa/onnx/tts/piper.html), [Piper on RK3588/ARM64](https://turingpi.com/whisper-cpp-piper-tts-arm64-turing-pi-rk3588/), [LocalAIMaster Piper setup guide](https://localaimaster.com/blog/piper-tts-setup-guide)

---

## 2. AI4Bharat Indic-TTS / Indic Parler-TTS

### Indic-TTS (the classic FastPitch+HiFi-GAN project) — **this is the one that matters for on-device**

- **Languages**: 13 — Assamese, Bengali, Bodo, Gujarati, Hindi, Kannada, Malayalam, Manipuri, Marathi, Odia, Rajasthani, Tamil, Telugu. **Covers all 9 of our Indic languages** (need English separately — trivial, use Piper en_US or LJSpeech).
- **Architecture**: FastPitch (non-autoregressive acoustic model, parallel mel generation, duration-predictor based) + HiFi-GAN V1 vocoder. Both components are small, non-autoregressive, and standard ONNX-export targets (FastPitch and HiFi-GAN are two of the most commonly ONNX/TensorRT-exported TTS architectures in the NVIDIA Riva ecosystem — same recipe AI4Bharat used, per NVIDIA Riva's own FastPitch/HiFi-GAN TAO training tutorial).
- **License: MIT** (confirmed directly via GitHub API on `AI4Bharat/Indic-TTS` — `license.spdx_id: MIT`). This is a materially better license position than Meta MMS (CC-BY-NC, see below).
- **Quality**: paper ("Towards Building Text-to-Speech Systems for the Next Billion Users", arXiv:2211.09536) reports FastPitch+HiFi-GAN beating existing baselines (DON Lab's Tacotron2+WaveGlow, Vakyansh's GlowTTS+HiFiGAN) on MCD, F0, CER, and subjective MOS for both Hindi (Indo-Aryan) and Tamil (Dravidian) — exact MOS decimal values are in a table image not machine-extractable from search, but the qualitative result (best-in-class among open Indic TTS at the time) is stated directly in the abstract/results. Live audio samples for direct listening evaluation are at [models.ai4bharat.org/#/tts](https://models.ai4bharat.org/#/tts) — worth listening before committing.
- **Downloads**: pretrained checkpoints at [github.com/AI4Bharat/Indic-TTS releases (v1-checkpoints-release)](https://github.com/AI4Bharat/Indic-TTS/releases), also served through the Bhashini/ULCA platform.
- **On-device feasibility**: no official ONNX export ships in the repo, but the architecture is ONNX-friendly (same class as Piper's VITS — non-autoregressive, single forward pass). Independent proof-of-concept: [vani-tts](https://github.com/vivek-541/vani-tts) is explicitly "fine-tuned on AI4Bharat IndicVoices, ONNX export, runs offline on CPU in real-time" for Hindi — though as of the last check (Apr 2026) it's early-stage (still training a VITS variant, no shipped ONNX file yet, targets `<200MB` post-INT8-quantization and `RTF < 0.3x` on CPU but marked "pending", Apache 2.0 licensed). Treat as a signal that the conversion is tractable, not as a ready dependency.
- **Practical read**: Indic-TTS is the strongest license+coverage fit (MIT, 9/9 Indic languages, good quality) but requires **you to do the PyTorch→ONNX export yourselves** (FastPitch export + HiFi-GAN export, then chain them, or fuse into one ONNX graph). Budget real engineering time for this — it's not a drop-in like Piper's official ONNX releases.

### Indic Parler-TTS — **not viable for this project's on-device constraint**

- **Languages**: 20 Indic + English (broader than Indic-TTS, adds Assamese, Bodo, Dogri, Konkani, Maithili, Manipuri, Nepali, Sanskrit, Santali, Sindhi, Urdu on top).
- **Architecture**: extension of Parler-TTS Mini — an **880M-parameter** autoregressive LLM-style decoder-only TTS (text+description prompt → audio codec tokens), not a compact VITS/FastPitch style model.
- **License**: Apache 2.0 (good).
- **On-device feasibility**: poor fit for low/mid-range phones. 880M params is roughly 15–50x larger than a Piper/FastPitch voice; autoregressive token-by-token generation means no free real-time-factor win from parallelism the way VITS/FastPitch get. This is a server-class model. Skip for this PS unless doing heavy quantization + acceptance of much slower/heavier inference — not recommended.
- Related: **IndicF5** (AI4Bharat, F5-TTS based, 11 languages, MIT license, 0.4B params, flow-matching) — same story: good quality, zero-shot voice cloning capability, but flow-matching + 400M params makes it a server/high-end-device model, not a fit for low-end offline Android.

Sources: [AI4Bharat/Indic-TTS GitHub](https://github.com/AI4Bharat/Indic-TTS), [Indic-TTS README](https://github.com/AI4Bharat/Indic-TTS/blob/master/README.md), [arXiv:2211.09536](https://arxiv.org/pdf/2211.09536), [ai4bharat/indic-parler-tts on HF](https://huggingface.co/ai4bharat/indic-parler-tts), [ai4bharat/indic-parler-tts-pretrained on HF](https://huggingface.co/ai4bharat/indic-parler-tts-pretrained), [ai4bharat/IndicF5 on HF](https://huggingface.co/ai4bharat/IndicF5), [vani-tts](https://github.com/vivek-541/vani-tts)

---

## 3. Meta MMS-TTS

- **Architecture**: one VITS model per language (1,107 languages total in the full MMS-TTS release).
- **Coverage of our 10 languages**: MMS-TTS has per-language checkpoints for Hindi (`mms-tts-hin`), Bengali (`mms-tts-ben`), Tamil (`mms-tts-tam`), Telugu (`mms-tts-tel`), and by the same pattern very likely all of Gujarati, Marathi, Kannada, Malayalam, Odia, English too (MMS covers >1000 languages so the long tail of Indian languages is essentially guaranteed to be present — confirm exact HF repo IDs like `facebook/mms-tts-guj`, `-mar`, `-kan`, `-mal`, `-ori`/`-ory` before committing, but MMS's breadth strongly suggests all 9 Indic languages + English are covered, which would make it the **only single source with full 10/10 language coverage** among everything reviewed here).
- **Size per model**: VITS-class, so expect the same ballpark as Piper — tens of MB per language (VITS models in this class are consistently 60–110M params / tens of MB).
- **License: CC-BY-NC 4.0 — hard blocker.** Confirmed: "MMS code and model weights are released under the CC-BY-NC 4.0 license," explicitly restricting commercial use unless separately authorized. **This disqualifies MMS-TTS for a shipped/demoed SIH solution under an "open-source only" PS requirement** — NC terms are not open-source by OSI definition and typically bar hackathon/production deployment even when free. Use MMS only for internal benchmarking/reference audio, never as the shipped model.
- **ONNX export**: well-trodden path — `Xenova/mms-tts-*` and similar repos on HuggingFace already ship ONNX-converted MMS-TTS models (built for transformers.js/browser use, e.g. `Xenova/mms-tts-eng`, `Xenova/mms-tts-ara`, `elloza/mms-tts-mlg-onnx`), proving the conversion works cleanly (some early TracerWarning issues during conversion were reported and resolved). sherpa-onnx also documents importing MMS VITS models directly (`vits-mms-*` naming in its releases). So technically the easiest full-coverage on-device option — just not license-clean.

Sources: [facebook/mms-tts-hin](https://huggingface.co/facebook/mms-tts-hin), [facebook/mms-tts-ben](https://huggingface.co/facebook/mms-tts-ben), [facebook/mms-tts-tam](https://huggingface.co/facebook/mms-tts-tam), [facebook/mms-tts-tel](https://huggingface.co/facebook/mms-tts-tel), [fairseq MMS README](https://github.com/facebookresearch/fairseq/blob/main/examples/mms/README.md), [sherpa-onnx MMS docs](https://k2-fsa.github.io/sherpa/onnx/tts/mms.html), [Xenova/mms-tts-eng ONNX](https://huggingface.co/Xenova/mms-tts-eng)

---

## 4. sherpa-onnx TTS on Android

- **What it is**: k2-fsa's cross-platform (C++/ONNX Runtime core, Kotlin/Java Android bindings, prebuilt AARs) runtime that can load Piper VITS models, MMS VITS models, Coqui VITS models, Matcha-TTS, and Kokoro — i.e. it's the **common runtime layer**, not a model source itself.
- **Which models run**: any VITS-family ONNX export (Piper's official releases, MMS conversions, Coqui-trained VITS) plus non-VITS additions like Matcha-TTS and Kokoro (added more recently). Full catalog: [github.com/k2-fsa/sherpa-onnx/releases/tag/tts-models](https://github.com/k2-fsa/sherpa-onnx/releases/tag/tts-models) and the interactive [HF Spaces demo](https://huggingface.co/spaces/k2-fsa/text-to-speech) (100+ voices across 40+ languages, catalog changes frequently — verify current Indic entries at build time rather than trusting this doc's snapshot).
- **Latency**: no network round-trip (fully offline/on-device) → sub-second time-to-first-audio is the norm for VITS-class models once loaded; a full RTF benchmark specific to a mid-range Android SoC wasn't found in this pass and should be measured directly on target hardware (e.g. a ₹10–15k class device) before committing to a specific voice quality tier.
- **Footprint**: native runtime (libsherpa-onnx + ONNX Runtime) adds roughly ~20–25 MB to the APK on top of whatever voice models are bundled/downloaded.
- **Practical implication for iTantra**: sherpa-onnx is almost certainly the right integration layer regardless of which model source you pick (Piper voices, or your own AI4Bharat FastPitch+HiFiGAN ONNX export, or a licensed-carefully MMS subset) — it already has Android bindings so you're not writing ONNX Runtime Mobile glue from scratch.

Sources: [sherpa-onnx TTS on Android index](https://k2-fsa.github.io/sherpa/onnx/tts/index.html), [sherpa-onnx APK engine page](https://k2-fsa.github.io/sherpa/onnx/tts/apk-engine.html), [Piper + sherpa-onnx write-up](https://medium.com/@patare.vivek/running-neural-text-to-speech-on-device-with-piper-and-sherpa-onnx-58f4eed29247), [VoxSherpa community Android app discussion](https://github.com/k2-fsa/sherpa-onnx/discussions/3383)

---

## 5. Lightweight TTS architecture comparison

| Architecture | Type | Typical size | Speed characteristic | Quality signal |
|---|---|---|---|---|
| **VITS** (Piper, MMS) | End-to-end, non-autoregressive, single ONNX graph | ~15M core params → ~20–65 MB ONNX (low/medium tiers) | Fast, parallel decode, RTF ~0.2 on ARM (Pi 5) | Good, well-proven at scale (100+ languages shipped) |
| **FastPitch + HiFi-GAN** (AI4Bharat Indic-TTS) | Two-stage, both non-autoregressive | Comparable class to VITS, two smaller models chained | Fast — same parallel-decode advantage as VITS, this is the standard NVIDIA Riva production combo | Beat Tacotron2+WaveGlow and GlowTTS+HiFiGAN baselines on Indic languages per AI4Bharat's own paper |
| **Matcha-TTS** | Flow-matching acoustic model + vocoder (Vocos or HiFi-GAN) | Small (designed for LJSpeech/VCTK-scale training, lighter than diffusion TTS) | Fast enough for real-time on CPU; espeak-ng-based phonemizer front end | MOS 3.85±0.05 (HiFi-GAN vocoder) vs 3.91±0.05 (Vocos vocoder); UTMOS 3.22 vs 3.44 respectively — note UTMOS "can be too generous to small HiFi-GAN vocoders that sound clean but mechanical," i.e. take these numbers as directional, not gospel |
| **Kokoro-82M** | Compact, ranked #1 on HF TTS-Arena at release | 82M params | Fast, CPU-viable, described as "dramatically smaller than competitors" while matching their quality | Strong community reception; primarily English-centric voice set — **no confirmed Indic-language Kokoro voices**, would need training/fine-tuning from scratch for Indic support, not a shortcut here |
| **Indic Parler-TTS / IndicF5** | Autoregressive LLM-decoder / flow-matching, 880M / 400M params | Large | Not designed for edge — no parallel-decode speed advantage, much bigger footprint | High quality but wrong tradeoff for this PS |

**Takeaway**: for this project, VITS and FastPitch+HiFi-GAN are in the same practical performance class (both non-autoregressive, both proven at ~20–80MB, both real-time-capable on ARM). Matcha-TTS and Kokoro are interesting but don't currently have ready-made Indic-language voices — would mean training from scratch, not a fit for a hackathon timeline. Stick to VITS (Piper) + FastPitch/HiFi-GAN (AI4Bharat) as the two realistic families.

Sources: [Matcha-TTS paper (arXiv:2309.03199)](https://arxiv.org/pdf/2309.03199), [Kokoro-82M on HF](https://huggingface.co/hexgrad/Kokoro-82M), [Kokoro CPU benchmark write-up](https://heyneo.com/blog/kokoro-supertonic-inflect-nano-cpu-tts-benchmark), [NVIDIA Riva FastPitch/HiFiGAN training tutorial](https://docs.nvidia.com/deeplearning/riva/archives/2-5-0/user-guide/docs/tutorials/tts-python-advanced-pretrain-tts-tao-training.html)

---

## 6. eSpeak-NG as fallback

- **Coverage**: 100+ languages/accents via formant synthesis (rule-based, no neural model), including Hindi, Bengali, Tamil, Telugu, Marathi and more — broader raw language coverage than any neural option here, and near-zero storage footprint (whole engine + all voices is a few MB, no per-language download).
- **Quality reality check**: explicitly robotic — not attempting to sound human. Confirmed by multiple independent sources as "very robotic and sometimes gibberish," with reliability issues on some inputs. Not viable as the primary voice for a demo-quality product.
- **Where it's actually useful**: (a) an instant fallback when a language's neural voice pack hasn't been downloaded yet or fails to load, so the app never goes fully silent; (b) extreme-speed accessibility reading where naturalness matters less than throughput; (c) as the phonemizer backend some neural pipelines (e.g. Matcha-TTS) already depend on — so it may already be a transitive dependency regardless.
- **Recommendation**: bundle eSpeak-NG as a zero-footprint universal fallback/safety-net across all 10 languages, not as the primary voice for any of them.

Sources: [espeak-ng voices.md](https://github.com/espeak-ng/espeak-ng/blob/master/docs/voices.md), [eSpeak NG on iOS/Android — why robotic voices still matter](https://speechcentral.net/2026/04/07/espeak-ng-on-ios-and-android-why-robotic-voices-still-matter/), [OfflineTTS FAQ](https://offlinetts.com/faq/)

---

## 7. IIT Madras Indic TTS project (SYSPIN / IndicTTS database)

- **What it is**: primarily a **dataset/corpus** project (Speech Technology Consortium, IIT Madras, MeitY-funded, 23 institutions), not a pretrained-model release like Piper or AI4Bharat's checkpoints.
- **Coverage**: original database — 13 major Indian languages, 10,000+ utterances each; expanded version covers 22 languages. ~40 hours of studio audio per language (20h native-language + 20h Indian-English), male+female speakers, 48kHz/16-bit studio recordings.
- **License**: gated behind the project's own "License For Use of Indic TTS" agreement — must be read/accepted before use; not a blanket open license like MIT/Apache. Treat as **research-use, not confirmed redistribution-safe for a shipped app** until the license terms are actually read and verified against SIH's open-source requirement.
- **Relevance to iTantra**: this is the data AI4Bharat's own Indic-TTS models were trained on (AI4Bharat's FastPitch+HiFi-GAN paper evaluates directly against "the IndicTTS Database"). Practical value here is as a **training/fine-tuning corpus** if the team wants to fine-tune voices further, not as a source of ready-to-ship model weights — use AI4Bharat's already-trained checkpoints instead unless there's a specific need to retrain.
- Related project note: SPRING Lab (IIT Madras) also publishes derivative HF datasets like `SPRINGLab/IndicTTS_Kannada` — same underlying corpus, packaged per-language.

Sources: [IIT Madras Indic TTS database](https://www.iitm.ac.in/donlab/indictts/database), [IIT Madras Indic TTS voices](https://www.iitm.ac.in/donlab/indictts/voices), [Unified Framework paper, arXiv:2410.14197](https://arxiv.org/pdf/2410.14197), [SPRINGLab/IndicTTS_Kannada on HF](https://huggingface.co/datasets/SPRINGLab/IndicTTS_Kannada)

---

## 8. Streaming TTS (chunked synthesis for low first-audio latency)

- **Core technique**: split input text at sentence/clause punctuation boundaries, synthesize and start playback of the first chunk while later chunks are still generating, rather than waiting for the whole utterance. This is standard practice, not something specific to any one engine — applies directly to a Piper/sherpa-onnx pipeline: run VITS inference chunk-by-chunk on a background thread, feed a rolling audio buffer to the Android `AudioTrack`/`MediaPlayer`.
- **What NOT to do**: splitting mid-sentence causes audible discontinuity (pitch/expression doesn't carry across chunk boundaries) — chunk at clause/sentence boundaries, not arbitrarily.
- **Measured impact**: one cited real-world case reports an **85% reduction in time-to-first-audio** from switching to phrase-segmented streaming vs. whole-utterance synthesis.
- **Gotcha for latency measurement**: naive "time to first byte" on a streamed response can be misleading — early bytes are often container/header metadata (WAV header, Ogg pages) carrying no actual audio, so measure time-to-first-**playable**-sample, not time-to-first-byte.
- **iTantra-specific plan**: since VITS/FastPitch are already non-autoregressive and fast per-sentence, sentence-chunked synthesis + a small look-ahead buffer (synthesize sentence N+1 while playing sentence N) should get first-audio latency down to roughly one sentence's worth of RTF-scaled compute — likely low hundreds of ms on target hardware once RTF is confirmed on-device (see gap noted in section 4).

Sources: [Soniox — Streaming TTS: why time-to-first-audio decides UX](https://soniox.com/wiki/streaming-tts), [Gradium — Time to First Audio](https://gradium.ai/blog/time-to-first-audio), [Deepgram TTS latency docs](https://developers.deepgram.com/docs/text-to-speech-latency), [Microsoft Speech SDK — lowering synthesis latency](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-lower-speech-synthesis-latency)

---

## 9. Text normalization for Indic scripts (numbers, dates, etc.)

- **`indic-numtowords`** (AI4Bharat, [github.com/AI4Bharat/indic-numtowords](https://github.com/AI4Bharat/indic-numtowords), also on [PyPI](https://pypi.org/project/indic-numtowords/)): "simple lightweight library for text normalization for Indian Languages" — converts digits to spoken-word form per language. Comes directly from the same org as our recommended TTS models, so integration friction should be low.
- **`indic-num2words`** ([github.com/raj-sutariya/indic-num2words](https://github.com/raj-sutariya/indic-num2words)): number→words for all Indian languages, e.g. `num2words(150, lang='hi', variations=True)` → "एक सौ पचास" / "डेढ़ सौ" (multiple valid spoken variants per number, useful for more natural-sounding output).
- **Indic NLP Library** (Anoop Kunchukuttan, [anoopkunchukuttan.github.io/indic_nlp_library](https://anoopkunchukuttan.github.io/indic_nlp_library/)): broader normalization toolkit — handles Devanagari, Bengali, Oriya/Odia, Gujarati, Gurmukhi (Punjabi), Tamil, Telugu, Kannada, Malayalam scripts. Useful beyond just numbers (script-level normalization, transliteration).
- **Gap**: none of these explicitly confirmed as handling **dates** end-to-end (day/month/year → spoken form) in a single call — likely needs a thin wrapper: detect date patterns (regex on DD/MM/YYYY or Devanagari-digit dates), decompose into day/month/year, run each numeric part through `indic-numtowords`/`indic-num2words`, and hand-write the month-name lookup per language (12 names × 9 languages is a small, one-time static table — not worth pulling in a heavier dependency for).
- **Recommendation**: use `indic-numtowords` (AI4Bharat) as the primary number normalizer given the org-alignment with the TTS models, fall back to `indic-num2words` for languages/edge cases it doesn't cover, and hand-roll the date-decomposition wrapper — this is a small, bounded amount of glue code, not a research gap.

Sources: [AI4Bharat/indic-numtowords](https://github.com/AI4Bharat/indic-numtowords), [indic-numtowords on PyPI](https://pypi.org/project/indic-numtowords/), [raj-sutariya/indic-num2words](https://github.com/raj-sutariya/indic-num2words), [Indic NLP Library](https://anoopkunchukuttan.github.io/indic_nlp_library/)

---

## Recommended stack

**Primary: AI4Bharat Indic-TTS (FastPitch + HiFi-GAN) exported to ONNX, served through sherpa-onnx on Android, with eSpeak-NG as a universal silent-fallback, and Piper's official voices used opportunistically wherever they already exist.**

Why, concretely:

1. **License is the deciding factor.** The PS requires open-source. Meta MMS-TTS — despite being the *only* source with confirmed/near-certain per-language coverage of all 10 target languages out of the box — is **CC-BY-NC 4.0**, which disqualifies it as the shipped model. AI4Bharat Indic-TTS is **MIT**, confirmed directly via the GitHub API, and covers all 9 Indic languages (English is trivial to add separately).
2. **Coverage**: AI4Bharat Indic-TTS is the only genuinely open, redistribution-safe source with all 9 Indic languages in one project (confirmed: Bengali, Gujarati, Hindi, Kannada, Malayalam, Marathi, Odia, Tamil, Telugu). Piper alone only covers 5/9 (Hindi, Malayalam, Marathi, Telugu, Bengali-Bangladeshi) — real gaps in Gujarati, Kannada, Tamil, Odia, verified by pulling Piper's actual voice manifest rather than trusting docs.
3. **Architecture fit**: FastPitch+HiFi-GAN is in the same performance class as VITS — both non-autoregressive, both proven to run in real time on ARM CPUs, both export cleanly to ONNX (this is literally NVIDIA Riva's production recipe). No architectural reason to expect it to be harder to get running on-device than Piper.
4. **Runtime**: sherpa-onnx already has Android bindings (Kotlin/Java, prebuilt AARs) and already handles VITS-family ONNX graphs — so whether the model source is Piper or a self-exported AI4Bharat checkpoint, the on-device integration code is the same. Don't build custom ONNX Runtime Mobile glue.
5. **Practical hybrid, not purity**: use **Piper's official ONNX voices directly** for the 5 languages where they already exist (Hindi, Malayalam, Marathi, Telugu, Bengali) — zero export work, known-good, MIT — and only do the AI4Bharat FastPitch+HiFi-GAN → ONNX export work for the 4 languages Piper is missing (Gujarati, Kannada, Tamil, Odia) plus English (trivially, from Piper's en_US catalog). This cuts the actual export/conversion engineering surface from "9 languages" to "4 languages," which matters a lot on a hackathon timeline.
6. **Fallback**: bundle eSpeak-NG (near-zero footprint, all 10 languages covered even if robotic) so the app is never silent for a language whose neural voice pack failed to load or hasn't been downloaded yet — genuine safety net, not the primary voice.
7. **Streaming**: implement sentence-chunked synthesis (split on punctuation, synthesize+play chunk N while chunk N+1 generates) regardless of model source — this is a pure integration-layer win (reported up to 85% first-audio latency reduction elsewhere) and doesn't depend on which of the above models is used.
8. **Open risk to flag explicitly**: no on-device RTF/latency number specific to a real low/mid-range Android SoC was found for either Piper or AI4Bharat FastPitch+HiFiGAN — all RTF figures above are ARM-adjacent (Raspberry Pi) proxies, not phone measurements. **This must be benchmarked directly on a target device (e.g., a sub-₹15k Android phone) early in the build**, since it's the one number that could force a fallback to `low`-quality voices or a different architecture if it doesn't hold.

**What to explicitly avoid**: Meta MMS-TTS as a shipped model (NC license), Indic Parler-TTS / IndicF5 as the primary voice (880M/400M params, wrong architecture class for edge), Kokoro (no Indic voices exist, would mean training from scratch), and eSpeak-NG as anything other than a fallback (too robotic for a demo).
