# iTantra (SIH26173) — India Policy Context, Academic Grounding & Evaluation Science

Research pass for SIH 2026 PS **SIH26173 — "iTantra: Indian Multilingual TTS & STT Aided Neural Transceiver Radio Access for low-bitrate links"**, sponsored by **ISRO**, Software category. Compiled 2026-08-31.

---

## 1. Who posted this PS, and why

- **Sponsor: Indian Space Research Organisation (ISRO)**, not DRDO/DoT/C-DOT as originally guessed. Listed on the official SIH 2026 archive under the **Software** track (PS ID SIH26173), theme bucket variously indexed as "Smart Automation" / "Miscellaneous" depending on the mirror site. [sih2026.vuce.in](https://sih2026.vuce.in/en) / [SIH 2026 PS viewer](https://sih2026-ps-viewer.vercel.app/)
- Full canonical problem text was **not retrievable** — the vuce.in archive entry for this specific PS 404s, and no third-party mirror had the full brief cached at fetch time. Only title + sponsor + category confirmed across 3 independent sources. Recommend pulling the live brief from sih.gov.in directly before finalizing the deck (search box or PS ID SIH26173).
- **Why ISRO, not a telecom body**: ISRO runs India's operational **Disaster Management Support (DMS) Programme**, whose stated purpose is enabling India (and neighboring countries) to use space-based information across all disaster-management phases — prevention, preparedness, early warning, response, reconstruction. It pairs earth-observation, meteorological and **communication satellites** with aerial survey. [ISRO's Capabilities in Disaster Management (ResearchGate)](https://www.researchgate.net/publication/342657614_ISRO's_Capabilities_in_Disaster_Management), [Deccan Herald](https://www.deccanherald.com/india/isros-disaster-management-programme-2168319)
- Concretely, ISRO already fields **GSAT-6 based Satellite Mobile Radio, Broadcast Receiver, Reporting Terminal and Sat-Sleeve terminals** for emergency comms, and regional centres (e.g. NESAC in the North-East) run VSAT-based SATCOM links to NDMA/SDMA over GSAT bandwidth, plus systems like **SILAAS** (Satellite Integrated Landslide Assessment and Alert System) issuing village-level alerts. This is the direct institutional lineage of a "neural transceiver for low-bitrate links" PS — ISRO's own radio-access hardware for the last mile already exists; iTantra is the natural next layer (voice-native compression + Indic TTS/STT) on top of it. [NESAC SATCOM applications](https://nesac.gov.in/scientific-programmes/satellite-communication-applications/)
- ISRO has also been actively **expanding satellite-based disaster management into border/remote regions** (e.g. Jammu & Kashmir), reinforcing that the PS's low-bitrate/offline framing is aimed at exactly the terrain where cellular infrastructure is thin or first to fail — border districts, hill states, cyclone coasts. [Kashmir Life](https://kashmirlife.net/isro-expands-satellite-based-disaster-management-across-jammu-kashmir-446739/)
- **Amateur/ham radio** is the closest civilian analogue to what iTantra digitizes: it is explicitly used as the fallback "when wireline, cell phones and other conventional means of communications fail" during disasters — the same use case iTantra targets with a phone-to-phone loop. [Amateur radio emergency communications (Wikipedia)](https://en.wikipedia.org/wiki/Amateur_radio_emergency_communications)

**Pitch framing**: iTantra isn't a random hackathon toy problem — it sits directly on ISRO's existing DMS-programme radio-access stack (GSAT satellite mobile radio, VSAT links to SDMAs) and fills the one gap that stack doesn't solve: voice-native, multilingual, low-bitrate human communication when literacy or bandwidth collapses.

---

## 2. India disaster-communication studies (NDMA/SACHET, cyclones, network outages)

**SACHET (NDMA's Common Alerting Protocol platform)**
- SACHET is India's official CAP-based warning aggregator — "the first and only portal across India to publish official warnings for all disasters from authorized sources," operational across **all 36 states/UTs**. [sachet.ndma.gov.in/About](https://sachet.ndma.gov.in/About)
- Cumulative SMS alert volume reported inconsistently across sources: one figure cites **>134 billion SMS alerts** sent to date in **19+ Indian languages**; a separate PIB-adjacent figure cites **6,899 crore (~69 billion) SMS alerts**. Treat as order-of-magnitude "tens of billions" and cite the range rather than a single hard number — both are large enough to be a strong scale citation. [Deccan Chronicle](https://www.deccanchronicle.com/nation/what-is-ndmas-nationwide-cell-broadcast-alert-system-for-natural-disasters-1954155)
- Government is actively piloting a new **indigenous Cell Broadcast system** (DoT + NDMA), tested nationwide, precisely because SMS/app-based alerting has last-mile gaps — pop-up alerts with loud tones, and on supported handsets **the message text is read aloud** (i.e., the government's own current system already leans on TTS-style read-aloud as an accessibility patch, which iTantra formalizes and pushes offline/multilingual). [PIB press release](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2140843&reg=3&lang=2), [PIB — pan-India testing](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2256706&reg=3&lang=1)
- Government has also had to reinforce **Akashvani (All India Radio) and Doordarshan** as last-mile disaster-alert channels specifically for rural, remote and border regions — an explicit admission that mobile-only alerting doesn't reach everyone. [News on Air, Dec 2025](https://www.newsonair.gov.in/akashvani-doordarshan-boost-last-mile-delivery-of-disaster-alerts-and-welfare-schemes-says-govt)

**Cyclone Fani (2019, Odisha) — the "zero casualty" benchmark**
- ~**2.6 million text messages** sent in clear language before landfall; state upgraded early warning reach via **122 siren towers across 6 coastal districts**. [The Conversation](https://theconversation.com/indias-cyclone-fani-recovery-offers-the-world-lessons-in-disaster-preparedness-116870)
- Widely cited as a "textbook" near-zero-casualty response combining accurate IMD forecasting + evacuation protocol + clear communication.

**Cyclone Amphan (2020, WB/Bangladesh)**
- Evacuation of **>3 million people**, praised by WMO as a textbook multi-hazard early-warning success. [WMO](https://wmo.int/media/news/cyclone-amphan-highlights-value-of-multi-hazard-early-warnings)
- But the comms *infrastructure* buckled even as the *warning* succeeded: in West Bengal, **~7,000 of 14,167 cell tower sites went non-operational**; networks ran at **65–70% capacity** three days post-landfall (COAI), later recovering to ~85%. This is the strongest "why low-bitrate / degraded-link resilience matters" data point available — the warning worked, the network that was supposed to carry follow-on comms didn't. [Deccan Herald — 65-70% capacity](https://www.deccanherald.com/amp/story/india%2Fcyclone-amphan-telecom-networks-operating-at-65-70-capacity-in-affected-districts-says-coai-840844.html), [Deccan Herald — 85% capacity](https://www.deccanherald.com/amp/story/india%2Ftelecom-network-working-at-85-capacity-in-amphan-hit-areas-of-west-bengal-841824.html), [The Quint](https://www.thequint.com/tech-and-auto/tech-news/cellphone-services-hit-after-amphan-knocks-out-cell-towers-in-west-bengal)

**Other recent outage precedents (strengthens the "networks fail exactly when needed" argument)**
- J&K floods, Aug 2025: **all service providers** hit outages from optical-fiber damage in torrential rain; ~24-hour disruption before ~80% restoration. [Deccan Herald](https://www.deccanherald.com/india/telcos-say-80-of-their-network-restored-in-flood-hit-kashmir-415934.html)
- Tripura floods, Aug 2024: telecom sites damaged alongside roads and power across multiple districts.
- DoT + Coalition for Disaster Resilient Infrastructure now run a **Disaster Risk and Resilience Assessment Framework** explicitly mapping tower/fiber/power vulnerability in high-risk states — **Odisha, Uttarakhand, Assam, Tamil Nadu, Gujarat** named specifically. [PIB — DoT 2025 year-end review](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2206477&reg=3&lang=1)

---

## 3. Literacy, linguistic inclusion, and why voice beats text

- National literacy (age 7+): **~77.7%** overall — **73.5% rural vs 87.7% urban**. The rural/urban gap is itself an alert-access gap.
- State literacy in disaster-prone states (most recent estimates found):
  - **West Bengal**: 82.6% (male 85.8%, female 79.3%) — 2023-24 survey
  - **Assam**: 72.19% (male 77.85%, female 66.27%) — 2024
  - **Bihar**: 70.9% — lowest-literate major state (NSO)
  - **Odisha**: state-level current figure not directly surfaced; district-level 2024 data exists via Indiastat but wasn't pulled — flag as a follow-up if a single Odisha number is needed for the deck.
  [findeasy.in state literacy compilation](https://www.findeasy.in/indian-states-by-literacy-rate/), [21kschool literacy overview](https://www.21kschool.com/us/blog/literacy-rate-in-india/)
- **Female literacy lags male by 6–12 points in every disaster-prone state above** — meaning text-based alerts systematically under-reach women in exactly the states most exposed to cyclones/floods. Useful equity angle.
- **Language, not just literacy, is the barrier**: ~70% of India's population is rural, and an estimated **90% of rural residents communicate only in their mother tongue**, preferring native-language interaction even when digitally literate. India recognizes **22 scheduled languages**. [Kadence / Digital India context](https://kadence.com/en-us/knowledge/connecting-with-digital-india-engaging-tech-savvy-consumers/)
- **Digital divide, hard numbers**: urban broadband penetration ~93% vs **rural 29.3%**; rural household internet access **14.9%** vs urban **42%**; rural digital literacy estimated at only **~37%** (2023), with only **27% of rural users** independently digitally literate. [arXiv survey on rural internet connectivity](https://arxiv.org/pdf/2111.10219)
- Net effect for the pitch: a meaningful share of India's most disaster-exposed population is simultaneously **(a)** less likely to read a text alert, **(b)** less likely to read it in a language other than their own, and **(c)** on a degraded or absent data link when it matters most — which is exactly the three-way failure mode iTantra (offline, multilingual, low-bitrate, voice-native) is built to close.

---

## 4. Academic literature

**(a) Low-resource Indic ASR/TTS surveys**
- **ASRoIL** — comprehensive survey of ASR for Indian languages (Artificial Intelligence Review, Springer). [link](https://link.springer.com/article/10.1007/s10462-019-09775-8)
- **Survey on ASR Systems for Indic Languages** (Springer book chapter). [link](https://link.springer.com/chapter/10.1007/978-3-030-95711-7_8)
- **BhashaSutra** (2026) — task-centric unified survey of Indian NLP datasets/corpora across ASR, TTS, translation, LID, spanning IndicSUPERB, IndicVoices/IndicVoices-R, IndicSpeech, LDC-IL, IIITH-ILSC. [arXiv 2604.18423](https://arxiv.org/pdf/2604.18423)
- **IndicVoices-R** — large multilingual multi-speaker speech corpus purpose-built for scaling Indian TTS. [arXiv 2409.05356](https://arxiv.org/pdf/2409.05356)
- **A2TTS** — TTS specifically for low-resource Indian languages (2026). [arXiv 2507.15272](https://arxiv.org/pdf/2507.15272)
- **AI4Bharat Indic-TTS** — open-source, 13 Indic languages (Assamese, Bengali, Gujarati, Hindi, Kannada, Malayalam, Marathi, Odia, Punjabi, Sanskrit, Tamil, Telugu, Urdu) — the most directly reusable reference stack for a 10-language build.
- Recurring challenge flagged across surveys: **code-switching, diverse morphology (agglutination), phonetic variety** as the core Indic-ASR difficulty, distinct from English-centric ASR literature.

**(b) Speech interfaces for low-literacy users (ICTD)**
- **"Designing IVR interfaces: Localisation for low literacy users"** — foundational ICTD paper on IVR design for non-literate populations. [ResearchGate](https://www.researchgate.net/publication/40904086_Designing_interactive_voice_response_IVR_interfaces_Localisation_for_low_literacy_users)
- **"Speech Interfaces for Information Access by Low Literate Users"** — direct precedent for the iTantra thesis. [ResearchGate](https://www.researchgate.net/publication/277293009_Speech_Interfaces_for_Information_Access_by_Low_Literate_Users)
- **"Behavior analysis of low-literate users of a viral speech-based telephone service"** (ACM DEV/COMPASS). Key finding pattern across this literature: **non-text (voice/audio) interfaces significantly outperform textual counterparts** for task completion among low-literacy users; spoken dialog lets illiterate users operate phones independently. [ACM DL](https://dl.acm.org/doi/10.1145/2537052.2537062)
- **"Using Radio Archives for Low-Resource Speech Recognition: Towards an Intelligent Virtual Assistant for Illiterate Users"** — directly analogous to using broadcast/radio-style audio as training signal for underserved-language ASR. [arXiv 2104.13083](https://arxiv.org/pdf/2104.13083)
- ICTD framing note: literacy-based technology barriers are best modeled "ecologically" — users route around barriers via social/community networks, meaning a single illiterate user's access often depends on one literate proxy in the household/village. Voice removes that dependency.

**(c) On-device speech recognition — energy/latency**
- Quantized Whisper-class "base" encoder on **Raspberry Pi: 107.13 ms latency, 71.75 mJ energy** — a **19x / 44x** improvement over the unquantized model. Quantized "small" encoder on **Jetson Nano: 7.32 ms, 4.92 mJ** (4x/33x gains). Directly citable numbers for an on-device feasibility slide. [arXiv 2405.01004](https://arxiv.org/pdf/2405.01004)
- **Conformer-based ASR on extreme edge devices** (Apple ML Research / arXiv 2312.10359) — achieves **5.26x faster than real-time (RTF 0.19)** on small wearables while holding SOTA accuracy, i.e. proof that sub-1.0 RTF is achievable on genuinely constrained hardware, not just flagship phones. [Apple ML Research](https://machinelearning.apple.com/research/conformer-based-speech), [arXiv](https://arxiv.org/abs/2312.10359)
- General claim worth citing cautiously (single blog source, not peer-reviewed): on-device ASR can hit **sub-500ms total latency** vs **500–1200ms** typical for cloud round-trips — use as a directional claim, not a hard benchmark.

**(d) WER/CER for Indic scripts**
- **"Is Word Error Rate a good evaluation metric for Speech Recognition in Indic Languages?"** — the single most important methodology paper for this PS's evaluation design. Core finding: WER is **disproportionately punishing for agglutinative Indic languages** (Malayalam, Kannada, Telugu) because single tokens can be very long — one substitution inside a long word counts as a full word error under WER. **CER is the better metric for these languages.** [arXiv 2203.16601](https://arxiv.org/pdf/2203.16601)
- **SN-WER (Script-Normalized WER)** — proposes reporting a script-normalized WER alongside raw WER/CER for multi-script Indic evaluation, since normalization choices (diacritics, combining marks, whitespace) can shift CER numbers dramatically between labs reporting on the *same* model. [arXiv 2606.02548](https://arxiv.org/pdf/2606.02548)
- Sarvam AI's practitioner writeup echoes this: Indic ASR eval should go **"beyond WER to LLM & semantic metrics."** [Sarvam AI blog](https://www.sarvam.ai/blogs/evaluating-indian-language-asr)
- **Practical takeaway for the pitch/eval section**: report **both WER and CER**, be explicit about the text-normalization pipeline used (script, diacritics, whitespace), and prefer CER as the headline number for Malayalam/Kannada/Telugu/Tamil-family outputs specifically.

---

## 5. Evaluation metrics science

- **WER** = (Substitutions + Deletions + Insertions) / Total reference words. **CER** = same edit-distance formula at the character level — preferred for Indic per section 4(d) above, especially agglutinative languages.
- **RTF (Real-Time Factor)** = processing time / audio duration. **RTF ≤ 1.0 is the real-time bar**; RTF 0.5 = 2x faster than real time; RTF 1.2 = falling behind live audio. On-device/edge work should target **RTF well under 1.0** (edge Conformer work above hits 0.19). [Picovoice — STT latency](https://picovoice.ai/blog/speech-to-text-latency/), [Keen Research — ASR latency](https://keenresearch.com/blog/evaluation/evaluating-asr-systems-part-3-latency-responsiveness.html)
- **MOS (Mean Opinion Score)** — subjective 1–5 human-rated naturalness/quality score for synthesized speech; gold standard but expensive (needs a listening panel).
- **PESQ (ITU-T P.862)** — objective proxy for MOS, score range **-0.5 to 4.5**, originally telecom-focused, adaptable to TTS quality scoring.
- **STOI (Short-Time Objective Intelligibility)** — objective intelligibility metric, **0 to 1**, purpose-built for "can this be understood," which for a disaster-alert TTS use case may matter more than naturalness. [Picovoice — speech quality](https://picovoice.ai/blog/speech-quality/)
- **Mouth-to-ear latency — ITU-T G.114**: **<150ms** one-way delay = transparent/imperceptible interactivity; **150–400ms** = workable but noticeably present; **>400ms** = unacceptable for real-time voice, hard upper bound used in VoIP network planning. Below 100ms specifically matters for highly interactive exchanges. This is the standard to cite for any "our walkie-talkie loop feels real-time" latency claim. [ITU-T Rec. G.114](https://www.itu.int/rec/dologin_pub.asp?lang=e&id=T-REC-G.114-200305-I!!PDF-E&type=items)
- **Suggested "good number" targets for a 2-phone offline walkie-talkie loop**, synthesized from the above (not from the PS text, since the exact rubric text wasn't retrievable — verify against the live PS before quoting in the deck):
  - ASR: **CER < 15–20%** for a 10-language, low-resource, on-device build is a defensible "working" bar (state-of-the-art cloud Indic ASR is single digits; on-device/low-resource realistically lands higher).
  - RTF: **< 0.5** on target hardware (mid-range Android) to leave headroom for TTS + transmission pipeline stages.
  - TTS: **MOS > 3.5** (understandable, not necessarily broadcast-natural) or **STOI > 0.8** if only objective scoring is feasible in the judging window.
  - End-to-end mouth-to-ear (STT decode + compress + transmit over low-bitrate link + decompress + TTS): **target <400ms**, stretch **<150ms** per ITU-T G.114 — frame the demo around whichever bucket is actually hit, don't overclaim <150ms unless measured.

---

## 6. Government programs to cite

- **Bhashini (National Language Translation Mission / NLTM)** — MeitY-led "National Public Digital Platform for Indian languages," implemented via the **Digital India BHASHINI Division (DIBD)** under Digital India Corporation. **₹450 crore** proposal was taken to Cabinet as part of MeitY's 100-day action plan for Natural Language Translation. Directly citable as the government's own AI-for-Indian-languages mission — iTantra is a disaster/offline-comms application of exactly this mission's goals. [X/DARPG announcement](https://x.com/DARPG_GoI/status/1945085173227512237), [Business Standard explainer](https://www.business-standard.com/technology/tech-news/bhashini-everything-you-need-to-know-about-ai-language-translation-tool-123121800769_1.html), [IndiaAI mission page](https://indiaai.gov.in/missions/national-mission-on-natural-language-translation-bhashini)
- **BharatNet** — world's largest rural broadband program; **>500,000 km of optical fiber laid**, **~2.14–2.15 lakh (214,000+) Gram Panchayats connected** as of late 2024/2025, targeting **630,000+ inhabited villages** at completion. Recent Phase III includes **satellite broadband via Hughes India** for the most remote panchayats — relevant precedent for "last-mile connectivity is a live government priority, and iTantra is the resilience layer for when even that fails." [BharatNet Phase III](https://bharatnet.in/bharatnet-phase-iii-landmark-initiative-narrowing-the-digital-gap-between-urban-and-rural-india/), [Organiser](https://organiser.org/2026/03/11/343531/bharat/rural-india-goes-online-bharatnet-brings-high-speed-internet-to-over-2-15-lakh-panchayats/)
- **DoT's Disaster Risk and Resilience Assessment Framework** (with Coalition for Disaster Resilient Infrastructure) — active government initiative specifically mapping telecom tower/fiber/power vulnerability in Odisha, Uttarakhand, Assam, Tamil Nadu, Gujarat. [PIB — DoT 2025 year-end review](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2206477&reg=3&lang=1)
- **NDMA's Cell Broadcast pilot** (indigenous system, tested nationwide, DoT+NDMA jointly) — shows government is *already* investing in the alert-delivery layer iTantra would sit downstream of / complement. [PIB](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2256706&reg=3&lang=1)
- **Digital India** umbrella — broad citation for the digital-inclusion policy context Bhashini and BharatNet both sit under.

---

## 7. Global analogues

- **Japan — J-Alert** (launched Feb 2007 by Fire and Disaster Management Agency): distributes via loudspeakers, TV, radio, email, and **cell broadcast**. **Uses synthesized TTS voice announcements** for tsunami warnings in **English, Mandarin, Vietnamese, Portuguese, Korean** over audio subchannels — Japanese-language content is typically live-read rather than synthesized. **This is the single strongest existing-nation precedent for "TTS speaks disaster alerts,"** directly validating iTantra's core mechanism at national scale. [J-Alert (Wikipedia)](https://en.wikipedia.org/wiki/J-Alert), [Centre for Public Impact](https://centreforpublicimpact.org/public-impact-fundamentals/j-alert-disaster-warning-technology-in-japan/)
- **EU-Alert** (EU-wide, cell-broadcast-based, ETSI-standardized): required of all EU member states by **2022** under a 2018 EU law. Explicitly network-congestion-immune (cell broadcast doesn't compete with call/SMS/data traffic during a load spike) — a strong structural argument that mirrors why a low-bitrate, non-cellular-dependent transceiver matters. Country variants use a `XX-Alert` naming convention (e.g. NL-Alert). Cross-border language support is an explicit design requirement given EU internal mobility. [EU-Alert (Wikipedia)](https://en.wikipedia.org/wiki/EU-Alert), [ITU cell broadcast overview](https://www.itu.int/en/ITU-D/Emergency-Telecommunications/Pages/EW4ALL/cell-broadcast.aspx)
- **US — FEMA IPAWS**: integrates Wireless Emergency Alerts (mobile), Emergency Alert System (TV/radio), NOAA Weather Radio. **Offers TTS but officially recommends human-recorded audio instead**, because TTS can mispronounce words/number sequences — an important **counter-argument iTantra needs to preempt**: TTS quality/pronunciation accuracy is a real, government-documented failure mode, not a solved problem. Worth addressing directly in the pitch (e.g., domain-tuned pronunciation lexicons for place names/numbers in alerts). [FEMA IPAWS](https://www.fema.gov/emergency-managers/practitioners/integrated-public-alert-warning-system), [FEMA IPAWS TTS tips](https://www.fema.gov/sites/default/files/documents/fema_ipaws-tip-42-alerts-with-audio.pdf)

---

## Pitch ammunition (10 most jury-impressive citable facts)

1. **iTantra is sponsored by ISRO**, which already runs GSAT-based Satellite Mobile Radio, VSAT-linked SDMA nodes, and village-level alert systems (SILAAS) under its Disaster Management Support Programme — iTantra isn't inventing a new mandate, it's completing ISRO's own existing radio-access stack with voice-native, multilingual intelligence.
2. **Cyclone Amphan (2020, WB): ~7,000 of 14,167 cell towers went down**, with networks at 65–70% capacity three days after landfall — proof that even a "successful" evacuation (3M+ people moved) still runs on a comms network that partially collapses exactly when it's needed most.
3. **NDMA/SACHET has sent on the order of tens of billions of SMS alerts (cited figures range ~6,900 crore to >134 billion) across 19+ languages** — yet the government is *still* building a parallel cell-broadcast system and reinforcing All India Radio/Doordarshan, a tacit admission that SMS-only alerting doesn't close the last mile.
4. **India's own Bihar (70.9%), Assam (72.2%), West Bengal (82.6%) literacy rates** — with female literacy trailing male by 6–12 points in every one — mean text alerts systematically under-reach the most disaster-exposed, most vulnerable population segment.
5. **~90% of India's 70%-rural population communicates only in its mother tongue**, across **22 scheduled languages** — text-in-English-or-Hindi alerting is a structural exclusion, not an edge case.
6. **ITU-T G.114 sets the international bar: <150ms mouth-to-ear = transparent real-time voice**, up to 400ms is workable — a concrete, internationally standardized target for iTantra's walkie-talkie-loop demo to be measured against on stage.
7. **Academic consensus (arXiv 2203.16601): WER is the wrong headline metric for Indic ASR** — agglutinative languages like Malayalam/Kannada/Telugu get punished disproportionately at the word level; **CER is the scientifically correct metric to report**, which most rival teams will get wrong.
8. **Quantized on-device ASR already hits 107ms/71.75mJ on a Raspberry Pi and 7.32ms/4.92mJ on a Jetson Nano** (19–44x gains over unquantized) — on-device, offline, low-power Indic ASR is not speculative, it's demonstrated engineering.
9. **Japan's J-Alert already uses synthesized TTS voice for national disaster alerts** in five languages — the world's most disaster-drilled nation validates exactly iTantra's core mechanism at production scale.
10. **FEMA IPAWS officially warns that TTS mispronunciation is a real failure mode** and recommends human-recorded audio instead — the strongest available evidence that pronunciation accuracy (place names, numbers) is the hard, jury-credible problem iTantra must visibly solve, not gloss over.

---

### Gaps / follow-ups before finalizing the deck
- Exact PS26173 brief text (background, expected outcome, dataset, and any explicit evaluation rubric weighting) could not be retrieved — the vuce.in mirror 404s on this specific PS. Pull live from sih.gov.in and cross-check the "20/40/20/20" rubric assumption before quoting numbers against it.
- Odisha's current state-level literacy figure wasn't pinned to a single clean number (only district-level 2024 data surfaced).
- The two conflicting SACHET SMS totals (6,899 crore vs 134 billion) should be resolved against a single primary NDMA/PIB source before using in a slide with a hard number — currently safe only as an order-of-magnitude claim.
