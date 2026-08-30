# Wave 3: Robustness + Jury Research — iTantra (SIH 2026, PS ISRO26173)

Research date: 2026-08-31. Third research wave, focused on hardening the weakest parts of the
pitch: ASR under real noise, alert-TTS intelligibility, 2025-26 semantic-comms landscape, SIH
jury mechanics, and hard evidence that two-way comms beats broadcast in disasters.

---

## 1. Noise-robust ASR: how badly does conformer/CTC degrade, and cheap fixes

### WER vs SNR — published curves
No single canonical "the" curve exists (every paper tests different models/noise sets), but the
pattern across recent papers is consistent and gives usable talking points:

- **Conformer-Transducer / Fast-Conformer**: WER stays roughly **flat and low down to ~10 dB
  SNR** (under 25% WER), degrades to **~40% WER around 0 dB**, and only "falls off a cliff"
  **below −10 dB SNR** (WER surges past 60%). Whisper-Base is worse at the low end, surpassing
  80% WER below −10 dB. [Journal on Audio, Speech, and Music Processing (Springer,
  2026)](https://link.springer.com/article/10.1186/s13636-026-00458-1)
- Confidence bands on these WER numbers stay tight (~2 percentage points) from 40 dB down to
  0 dB, and only widen (3-4 pp) below −10 dB — i.e. degradation is systematic/predictable, not
  driven by a few outlier clips. Same source as above.
- "Bring the Noise: Introducing Noise Robustness to Pretrained ASR" (Interspeech workshop /
  Springer LNCS 2023) — confirms the general finding that off-the-shelf pretrained ASR
  (wav2vec2/Whisper-class) degrades sharply under unseen noise types unless fine-tuned or paired
  with a front-end denoiser; noise-aware fine-tuning recovers most of the loss.
  [arXiv:2309.02145](https://arxiv.org/pdf/2309.02145)

**Practical takeaway for the pitch**: disaster-zone SNR is realistically in the **5-15 dB range**
(sirens, rain, crowd shouting, generator noise) — i.e. right in the "still workable but degrading"
band for a Conformer, not yet in freefall. This is defensible: iTantra doesn't need to claim
perfect ASR in a hurricane, it needs to claim "usable at typical disaster SNR, and here's the
mitigation for the worse cases."

### Cheap, deployable pre-ASR denoising options (all run before AI4Bharat IndicConformer)

| Option | Size | License | Mobile/ONNX | Notes |
|---|---|---|---|---|
| **RNNoise** | ~85,000 weights, tiny (<100KB model), faster than real-time on one CPU core | **BSD 3-Clause** | Android ports exist (e.g. `TGX-Android/rnnoise` on GitHub); used in WebRTC, Mumble, OBS | 2017-era RNN-GRU on 22 Bark-scale bands. Good for stationary noise (fans, hum), **degrades noticeably on non-stationary noise (crowds, babble)** — a real caveat for disaster acoustics. [jmvalin.ca demo](https://jmvalin.ca/demo/rnnoise/) |
| **SpeexDSP preprocessor** | Very small, pure C, no NN | BSD-style | Trivial to port; used for decades in embedded VoIP | Classic spectral-subtraction denoiser + AGC + VAD in one preprocessor block, "used on audio before running the encoder." Lighter than RNNoise but weaker on non-stationary noise. [SpeexDSP docs](https://github.com/TeaPoly/speexdsp-ns-python) |
| **sherpa-onnx DPDFNet** | 2.3M–3.6M params depending on variant (8/16/48kHz builds) | Same as sherpa-onnx (Apache-2.0-family) | **Native ONNX, ships in sherpa-onnx directly** — same runtime iTantra already needs for ASR/TTS, zero extra integration surface | Extends DeepFilterNet2 with dual-path RNN; causal + streaming-capable. Docs explicitly recommend `dpdfnet_baseline`/`dpdfnet2` (16kHz, fastest) as the pre-ASR enhancement stage. [k2-fsa docs](https://k2-fsa.github.io/sherpa/onnx/speech-enhancement/dpdfnet.html), [release](https://github.com/k2-fsa/sherpa-onnx/releases/tag/speech-enhancement-models) |
| **GTCRN** | **48.2K params, 33.0 MMACs/s** — extraordinarily small | Open (MIT-style, academic release) | Also available as a sherpa-onnx speech-enhancement model alongside DPDFNet | Peer-reviewed (ICASSP 2024) to **beat RNNoise** at similar or lower compute cost via grouped convs + sub-band + temporal-recurrent-attention. [GitHub](https://github.com/Xiaobin-Rong/gtcrn), [IEEE](https://ieeexplore.ieee.org/document/10448310/) |
| **Picovoice Koala** | commercial, on-device | Commercial license (not free) | iOS/Android/desktop | Cited only for comparison: reduces STOI distance to 0.0415 vs RNNoise's 0.0748 (lower = better) — i.e. meaningfully better than RNNoise, but paid. Not usable for a free/open hackathon build. [Picovoice guide 2026](https://picovoice.ai/blog/complete-guide-to-noise-suppression/) |
| WebRTC NS | small, C | BSD | Widely ported | Baseline reference; explicitly "known weaknesses with non-stationary noise and babble" — same weak spot as RNNoise, older/weaker overall. |

**Recommendation**: iTantra should pitch **sherpa-onnx DPDFNet or GTCRN** as the noise front-end,
not RNNoise — because (a) it's literally in the same runtime/toolchain as the ASR model already
chosen (no new dependency), (b) GTCRN is smaller than RNNoise and benchmarked to beat it, and
(c) it directly targets the SIH judges' likely question "what happens to your ASR in real noise."

### Disaster-specific acoustics literature
Direct "ASR-in-disaster-acoustics" papers are thin — this is a genuine research gap, which is
itself worth stating in the pitch ("no one has published WER-vs-siren/crowd numbers, we had to
reason from adjacent literature"). What does exist:
- Emergency siren *detection* (not ASR degradation) is well studied and performs well
  (>99% detection accuracy, <400ms response) — but that's a different task (classifying siren
  presence, not recognizing speech in the presence of a siren).
  [ResearchGate: Acoustic Features for Emergency Siren Detection](https://www.researchgate.net/publication/355112750_Acoustic_Features_for_Deep_Learning-Based_Models_for_Emergency_Siren_Detection_An_Evaluation_Study)
- General adverse-condition ASR papers test white noise, reverberation, time-stretch, pitch-shift
  — all show "significant decline... across all models," with resilience varying by language.
  [Springer, ASR Systems Under Acoustic Challenges: Multilingual Study](https://link.springer.com/chapter/10.1007/978-3-031-80607-0_16)

**Honest framing for judges**: "Published disaster-specific ASR-degradation studies don't exist
yet; we're applying the closest available evidence (general noise-robustness curves + a
sherpa-onnx-native denoiser) and this is itself a contribution — nobody has benchmarked Indic ASR
under simulated cyclone/siren/crowd audio before."

---

## 2. Alert TTS prosody & intelligibility

### The actual research behind "slower TTS = more intelligible" — and its limits
This is the most important correction from this wave: **the naive claim "just slow the TTS
down" is not well supported.** The literature says something more specific.

- **Lombard-effect TTS synthesis** (speaking as if in noise — raised pitch/loudness, spectral
  tilt change, not just slower rate) gives real, measured gains:
  - Relative intelligibility improvement of **8-12% in speech-shaped noise (SSN)** and
    **15-36% in competing-speaker noise (CSN)**, across SNR levels tested.
  - Subjective/keyword-correct-rate gains even larger: **+455% (SSN)** and **+104% (CSN)** median
    keyword correction rate vs plain TTS in the same noise.
    [Synthesizing the Lombard Effect: Multi-Level Control of Speech Clarity and Vocal Effort in
    TTS, arXiv](https://arxiv.org/pdf/2606.23176)
- **Speaking rate alone is NOT the mechanism**: "linearly slowing down speech alone is
  suboptimal for intelligibility enhancement... no beneficial effects of durational increases
  were observed... Lombard sentences spoken at substantially slower rates than their plain
  counterparts also failed to reveal a durational benefit." **Spectral changes** (formant/energy
  redistribution, not duration) are what carries most of the Lombard intelligibility benefit.
  [PubMed: contribution of durational and spectral changes to Lombard intelligibility
  benefit](https://pubmed.ncbi.nlm.nih.gov/25234895/)
- Style-conversion TTS (converting a plain-speech TTS voice toward a "clear speech" style, not
  just slowing it) — Interspeech 2020 paper directly targeted at this exact iTantra use case
  (making synthesized alerts more intelligible), confirms style/spectral conversion outperforms
  naive rate reduction. [ISCA
  archive](https://www.isca-archive.org/interspeech_2020/paul20b_interspeech.html), [arXiv
  2008.05809](https://arxiv.org/pdf/2008.05809)

**Correction to make in the pitch**: don't claim "we slow down the TTS for clarity" as the
headline mechanism — that's the weakly-supported version. The better, still-cheap claim is
**"we insert pauses/repetition and use a naturally slower, clearly-articulated TTS voice
preset"** (rate reduction + pause insertion is still mildly useful and free to implement; just
don't oversell it as *the* intelligibility mechanism — full Lombard-style resynthesis is the
"real" fix and is a stretch goal, not MVP).

### FEMA / WMO message-construction guidance (hazard-location-action)
- FEMA IPAWS best practice: alerts should include **Source, Hazard, Location, Protective Action,
  Expiration Time** — i.e. the "hazard-location-action" structure iTantra should assume/enforce
  as the canonical alert template. [FEMA Best
  Practices](https://www.fema.gov/emergency-managers/practitioners/integrated-public-alert-warning-system/public-safety-officials/alerting-authorities/best-practices),
  [FEMA IPAWS best practices
  PDF](https://www.fema.gov/sites/default/files/documents/fema_ipaws-best-practices-guide.pdf)
- WEA message length: **90-character legacy limit, 360-character extended limit** on 4G+
  devices. [NWS WEA360](https://www.weather.gov/wrn/wea360)
- **Important nuance/correction**: a 2024 peer-reviewed test (N=481) found **longer (360-char)
  messages did NOT produce higher compliance than 90-char messages** — in fact shorter messages
  slightly outperformed longer ones for people with lower risk personalization. Risk
  personalization and prior hazard experience were the stronger predictors of compliance, not
  message length. [PMC: Do 360-Character WEA Messages Work Better than 90-Character Messages? —
  Testing the Risk Communication Consensus (2024)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11424238/),
  [Wiley](https://onlinelibrary.wiley.com/doi/10.1111/1468-5973.12587)
  - **This directly supports iTantra's constraint, don't apologize for it**: iTantra's 45-byte
    text-message design isn't a compromise forced by bandwidth — it's *consistent with* published
    evidence that short, structured alerts perform at least as well as long ones. Use this as a
    citation to preempt the judge question "isn't 45 bytes too short to be useful?"
- WMO: Common Alerting Protocol (CAP) is the standard "all-hazard, all-media" message format;
  WMO's Impact-Based Forecasting/Warning (IBFWS) approach emphasizes framing messages around
  exposure/vulnerability of the specific audience, not generic hazard description; multi-channel
  redundancy is explicitly recommended (never rely on one channel). [WMO Multi-hazard
  guidelines](https://www.anticipation-hub.org/Documents/Manuals_and_Guidelines/WMO_Guidelines_on_Multi-hazard__part2.pdf),
  [WMO CAP](https://community.wmo.int/site/knowledge-hub/programmes-and-initiatives/public-weather-services-programme-pws/common-alerting-protocol)

---

## 3. 2025-26 semantic-comms updates beyond STCTS/DeepSC-ST

- **"Large Model Empowered Streaming Speech Semantic Communications" (LSSC-ST)**, Jan 2025 —
  the most relevant fresh citation found. Key differentiator vs older DeepSC-ST-style systems:
  it's **streaming** (processes short speech segments sequentially with a dynamic
  segmentation algorithm for low latency) rather than whole-utterance, and uses an
  **edge-device collaborative architecture** — semantic extraction/channel coding offloaded to
  an edge server, pretrained large speech models give multilingual support via unified semantic
  features across languages. Authors claim more accurate transmission + lower latency vs
  non-streaming semantic-comm baselines. No public bitrate figure surfaced in the abstract-level
  read. [arXiv:2501.05859](https://arxiv.org/abs/2501.05859) — **note**: iTantra's fully offline,
  no-edge-server, on-device-only story is actually a stronger fit for disaster scenarios than
  this paper's edge-collaborative design (edge server = infrastructure dependency = exactly what
  fails in a disaster). Worth naming as "we go further than 2025 semantic-comm research by
  removing the infrastructure dependency entirely."
- **Standardization movement**: 3GPP, IEEE, and ITU are all "actively exploring pathways" for
  semantic communication; ITU-T SG13 has identified semantic communication as a key enabler for
  networks beyond IMT-2020 (6G-era). This confirms semantic/token-based comms is a live
  standardization target, not a fringe research idea — useful as "this is where the industry is
  headed" framing. [arXiv:2509.12758, Towards Native AI in 6G Standardization: The Roadmap of
  Semantic Communication](https://arxiv.org/html/2509.12758v1)
- **Token-based speech transmission**: speech tokenization (discretizing audio into token
  sequences compatible with LLM-style prediction) is now a standard building block across recent
  semantic-comm papers — e.g. "Joint Semantic-Channel Coding and Modulation for Token
  Communications" (Nov 2025, arXiv:2511.15699) and RepCodec-style speech-representation codecs.
  This is the same conceptual family as iTantra's STT→text approach, just one level more
  abstract (sub-word tokens vs full text) — worth one sentence acknowledging the adjacent
  research trend without overclaiming iTantra invented it.
- **Ships-on-phones STT→text→TTS systems**: still no found production system doing exactly
  iTantra's loop (recognize speech → transmit ultra-low-bitrate text → resynthesize speech on
  the other phone) as a shipped consumer/field product. Meshtastic (LoRa mesh messenger) has
  active 2025-26 community discussion of **adding TTS-read-aloud of received text messages** and
  **voice-to-text for composing messages via the phone keyboard**, but this is "voice as
  input/output convenience layer," not "voice IS the compressed transport" — i.e. Meshtastic
  doesn't yet turn spoken audio into transmitted text as the *primary* channel. This remains
  the whitespace iTantra occupies. [Meshtastic voice discussion,
  GitHub](https://github.com/meshtastic/firmware/discussions/6026), [Meshtastic
  ATAK-plugin TTS language request](https://github.com/meshtastic/ATAK-Plugin/issues/26)
  - No hits at all for "ASR relay radio" or "textual voice channel" as an existing named
    product/term — confirms the terminology and the product category are still open.

---

## 4. SIH jury meta: what judges actually probe, and rejection patterns

Best single source found: a **2022 SIH winner's retrospective** (team lead), plus several
2025-26 "how to win SIH" guides that converge on the same points.
[anishprashun.me](https://www.anishprashun.me/blog/sih-2025-tips-and-common-mistakes)

### Reported evaluation weighting (from the 2022 winner's retrospective)
- Criticality/Impact: **25%**
- Commercial Viability: **25%**
- Innovation: **20%**
- Technology: **15%**
- MVP/Prototype: **15%**
(Treat this as one team's recollection, not an official published SIH rubric — but it's
directionally useful: impact + viability together are **50%**, tech stack is only 15%.)

### What judges actually probe
- **Word-by-word alignment with the official problem statement.** Repeated across every source:
  drifting from the literal PS wording is a fast disqualifier even for a genuinely better idea.
- **Working prototype > polished slides.** "Even a basic prototype beats slides only." Missing
  demo video/screenshots is called out explicitly as a critical, avoidable failure.
  [SIH 2026 project ideas guide](https://blogs.reskilll.com/smart-india-hackathon-2026-20-project-ideas-that-actually-win/)
- **Feasibility over ambition.** "A well-scoped, deeply understood problem consistently beats an
  ambitious one your team can't fully execute." Avoid problems needing long data-collection
  windows the team can't demonstrate live.
- **Tech-stack minimalism.** Judges explicitly penalize buzzword-stacking; they evaluate whether
  the tech *solves the stated problem*, not how modern the stack is. (Directly relevant: iTantra
  should not oversell "AI/ML/semantic comms" jargon at the expense of showing the actual
  demo working end to end.)
- **AI-generated-content detection.** Multiple sources flag that judges can tell when
  PPT/report content is generic LLM output; reward originality/specificity (concrete numbers,
  named benchmarks, named prior art) over generic claims.
- **Integration, not components.** A recurring finalist failure mode: teams that built working
  frontend and backend separately but never integration-tested end-to-end before finals lose to
  teams with a rougher but fully working pipeline. Advice: start integration testing from day
  one, not last-minute.
- **Track/category correctness.** Submitting under the wrong track/category for your solution's
  actual fit is called out as an avoidable rejection cause.

### Ideal ~3-minute finale pitch structure (converged across multiple hackathon-pitch guides)
1. **Intro + problem** (~20-30s) — who is affected, why it matters, made concrete/personal
   (not abstract statistics).
2. **Solution** (~30-45s) — what it does, one clear differentiator vs status quo/prior art.
3. **Technical approach** (~45-60s) — enough to show competence, not a tech tour; judges want
   "system logic without excessive detail."
4. **Live demo** (~45-60s) — the single highest-leverage segment; a working demo beats
   description every time.
5. **Impact + feasibility/scalability + what's next** (~20-30s) — quantify impact if at all
   possible, name a concrete deployment/scaling path.
[Best3Minutes MIT COVID19 hackathon pitch
guide](https://best3minutes.com/wp-content/uploads/2020/05/Make-a-Winning-Hackathon-Pitch_MIT-COVID19.pdf),
[TAIKAI hackathon pitch guide](https://taikai.network/en/blog/how-to-create-a-hackathon-pitch)

---

## 5. Two-way disaster comms: evidence it beats broadcast-only

### Nepal 2015 earthquake — ham radio
- Nepal had only **~99 licensed ham operators** (~8 with HF long-range gear, ~30 VHF/UHF local),
  yet amateur radio provided **reliable communication for responders in remote regions, helped
  locate missing people, and relayed casualty information** — precisely because it's two-way
  (operators coordinating in shifts with international hams in Turkey, Australia, NZ) not
  broadcast.
- Key infrastructure point: cell towers were **functional** but phone **batteries died** —
  amateur radio kept working because it can run on solar/hand-crank/low-voltage power, i.e. the
  bottleneck wasn't tower coverage but device power — a distinct and important nuance from the
  usual "towers went down" narrative. [ARRL](http://www.arrl.org/news/amateur-radio-continues-to-provide-reliable-post-quake-communication-in-nepal),
  [Network World](https://www.networkworld.com/article/938418/ham-radio-attempts-to-fill-communication-gaps-in-nepal-rescue-effort.html)

### Kerala 2018 floods — WhatsApp + ham radio, both two-way
- **40+ ham operators helped an estimated 2,000+ people** during the floods, working search-and-
  rescue coordination directly with Kerala Fire Force. [The
  Federal](https://thefederal.com/states/south/kerala/network-down-ham-radios-help-coordinate-rescue-in-rain-hit-kerala)
- WhatsApp groups (hundreds of members) were used for real-time two-way coordination of rescue/
  relief; a volunteer-built site (keralarescue.in) let stranded people submit needs directly to
  authorities — again explicitly two-way, not broadcast. [NPR](https://www.npr.org/sections/goatsandsoda/2018/08/22/640879582/how-social-media-came-to-the-rescue-after-keralas-flood)
- Documented closed-loop protocol in Kerala flood control rooms: **field teams acknowledge
  directives, repeat back critical details, then report execution status** — a textbook
  closed-loop/two-way pattern credited with reducing miscoordination in rescue operations.
  [AlertMedia](https://www.alertmedia.com/blog/two-way-communications/)

### General evidence for two-way > broadcast
- Two-way comms is credited in the crisis-comms literature with **error reduction via
  confirmation of understanding**, and **continuous feedback enabling real-time plan
  adaptation** as situations evolve — both structurally impossible with one-way alert broadcast.
  [AlertMedia: Importance of Two-Way Communication During a
  Crisis](https://www.alertmedia.com/blog/two-way-communications/), [Crisis Response Journal:
  Facilitating two-way public communication in crisis and disaster
  management](https://www.crisis-response.com/Articles/593418/Facilitating_two_way.aspx)
- This is a genuinely under-quantified area academically (no RCT-style "outcomes with two-way
  vs without" study surfaced) — the evidence is case-study/consensus, not a controlled trial.
  State this honestly if a judge pushes for a number: "the two-way-beats-broadcast case is
  strong on case-study and mechanism grounds (Kerala closed-loop protocol, Nepal SAR
  coordination), not on a controlled quantitative study — that gap itself is part of why a
  live two-way pilot has research value beyond the hackathon."

**Framing win for iTantra**: existing disaster comms tech (WEA, cell broadcast, siren systems)
is broadcast-only/one-way. Ham radio is two-way but requires licensing, training, and dedicated
hardware most citizens don't have. iTantra's pitch is literally "two-way ham-radio-grade
coordination, but usable by anyone with a phone and no training" — Nepal/Kerala give concrete,
real, high-profile Indian-context evidence for why the two-way property matters, not just the
low-bitrate property.

---

## Cheap wins to implement (ranked by effort)

1. **[~1 hour] Cite the FEMA hazard-location-action structure + the 90-vs-360-char study
   explicitly in the pitch deck.** Turns "our messages are short" from a limitation into a
   design decision backed by 2024 peer-reviewed evidence. Zero code.
2. **[~1 hour] Add DPDFNet or GTCRN as the stated pre-ASR noise front-end in the architecture
   diagram**, even if not fully wired into the demo build. Since it's a sherpa-onnx-native model
   (same runtime as ASR/TTS), this is a config/model-file addition, not a new dependency —
   pre-empts the "what about noise?" judge question with a specific, small, already-integrated
   answer.
3. **[~2-4 hours] Actually wire DPDFNet (16kHz baseline variant, ~2.3M params) into the STT
   pipeline as a literal pre-processing step before IndicConformer inference.** Turns #2 from a
   slide claim into a working demo feature; small enough to realistically fit in hackathon time.
4. **[~1 hour] Rewrite the "slower TTS = clearer" claim in the pitch to "clear-speech style +
   pause insertion" language**, and cite the Lombard-TTS papers instead of a vague speaking-rate
   claim — avoids a judge who knows the literature catching the oversimplification.
5. **[~2 hours] Add a one-slide honest gap admission**: no published disaster-acoustic
   ASR-degradation benchmark exists; iTantra's SNR framing is extrapolated from general noise
   literature. Counter-intuitively this raises credibility with technically sharp judges more
   than pretending the number is solid.
6. **[Stretch, days] Full Lombard-style TTS resynthesis** (spectral-tilt/formant adjustment, not
   just rate/pause) — real intelligibility gains (8-36% relative) but requires a different TTS
   model/training data than a stock Indic TTS voice; not hackathon-timeline feasible, name it as
   roadmap only.

## Pitch/jury playbook

1. Lead with the Nepal/Kerala two-way evidence, not abstract bandwidth math — judges respond to
   named, Indian, recent, human-stakes examples over kbps tables.
2. State the 90-vs-360-character WEA study number when a judge questions whether 45 bytes is
   "too short" — you have a citation, they probably don't.
3. Never let the tech-stack description run longer than the demo — evaluation weighting
   evidence suggests impact/viability (50%) dominates tech elegance (15%).
4. Rehearse hitting every literal word of the PS ISRO26173 text before finals — repeated across
   every source as the single most common avoidable rejection cause.
5. Build one honest "here's what we haven't solved yet" slide (disaster-acoustic ASR gap,
   two-way-vs-broadcast lacking an RCT). Judges reward calibrated confidence over oversell.
6. Keep the live demo to ~45-60 seconds of the ~3-minute slot and rehearse it more than any other
   segment — it's the highest-leverage single segment per every pitch-structure source found.
7. Have the DPDFNet/GTCRN noise-front-end answer ready verbatim — "what happens in a noisy
   disaster zone" is a near-certain question given the PS's disaster framing.
8. Frame semantic-comms/LLM-codec research (LSSC-ST, 3GPP/ITU SG13 moves) as "the industry is
   headed toward token/semantic transport; iTantra removes the edge-server dependency those 2025
   papers still assume" — turns recent academic work into supporting evidence, not competition.
9. Don't claim iTantra invented STT→text→TTS-as-transport; name Meshtastic's 2025-26 voice
   discussions and the 2025 "Voice over Low Data Rate Networks" paper explicitly, then state the
   precise gap iTantra fills (voice as *primary compressed transport*, not a UI convenience
   layer).
10. Close on feasibility, not ambition — one clear, already-working demo path beats five
    described future features, per every SIH rejection-pattern source found.

---

## Sources index (all URLs cited above, deduplicated)

- https://link.springer.com/article/10.1186/s13636-026-00458-1
- https://arxiv.org/pdf/2309.02145
- https://link.springer.com/chapter/10.1007/978-3-031-80607-0_16
- https://www.researchgate.net/publication/355112750_Acoustic_Features_for_Deep_Learning-Based_Models_for_Emergency_Siren_Detection_An_Evaluation_Study
- https://jmvalin.ca/demo/rnnoise/
- https://github.com/TGX-Android/rnnoise
- https://github.com/TeaPoly/speexdsp-ns-python
- https://k2-fsa.github.io/sherpa/onnx/speech-enhancement/dpdfnet.html
- https://github.com/k2-fsa/sherpa-onnx/releases/tag/speech-enhancement-models
- https://github.com/Xiaobin-Rong/gtcrn
- https://ieeexplore.ieee.org/document/10448310/
- https://picovoice.ai/blog/complete-guide-to-noise-suppression/
- https://arxiv.org/pdf/2606.23176
- https://pubmed.ncbi.nlm.nih.gov/25234895/
- https://www.isca-archive.org/interspeech_2020/paul20b_interspeech.html
- https://arxiv.org/pdf/2008.05809
- https://www.fema.gov/emergency-managers/practitioners/integrated-public-alert-warning-system/public-safety-officials/alerting-authorities/best-practices
- https://www.fema.gov/sites/default/files/documents/fema_ipaws-best-practices-guide.pdf
- https://www.weather.gov/wrn/wea360
- https://pmc.ncbi.nlm.nih.gov/articles/PMC11424238/
- https://onlinelibrary.wiley.com/doi/10.1111/1468-5973.12587
- https://www.anticipation-hub.org/Documents/Manuals_and_Guidelines/WMO_Guidelines_on_Multi-hazard__part2.pdf
- https://community.wmo.int/site/knowledge-hub/programmes-and-initiatives/public-weather-services-programme-pws/common-alerting-protocol
- https://arxiv.org/abs/2501.05859
- https://arxiv.org/html/2509.12758v1
- https://arxiv.org/pdf/2511.15699
- https://github.com/meshtastic/firmware/discussions/6026
- https://github.com/meshtastic/ATAK-Plugin/issues/26
- https://www.anishprashun.me/blog/sih-2025-tips-and-common-mistakes
- https://blogs.reskilll.com/smart-india-hackathon-2026-20-project-ideas-that-actually-win/
- https://best3minutes.com/wp-content/uploads/2020/05/Make-a-Winning-Hackathon-Pitch_MIT-COVID19.pdf
- https://taikai.network/en/blog/how-to-create-a-hackathon-pitch
- http://www.arrl.org/news/amateur-radio-continues-to-provide-reliable-post-quake-communication-in-nepal
- https://www.networkworld.com/article/938418/ham-radio-attempts-to-fill-communication-gaps-in-nepal-rescue-effort.html
- https://thefederal.com/states/south/kerala/network-down-ham-radios-help-coordinate-rescue-in-rain-hit-kerala
- https://www.npr.org/sections/goatsandsoda/2018/08/22/640879582/how-social-media-came-to-the-rescue-after-keralas-flood
- https://www.alertmedia.com/blog/two-way-communications/
- https://www.crisis-response.com/Articles/593418/Facilitating_two_way.aspx
