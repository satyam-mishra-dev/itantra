# Low-Bitrate Voice Communication — Research for iTantra

Research date: 2026-08-31. Compiled for SIH 2026 PS "iTantra" (offline STT+TTS walkie-talkie app).

---

## 1. The bitrate math: raw voice vs codecs vs text

| Representation | Bitrate | Notes |
|---|---|---|
| Raw telephone PCM (G.711) | **64,000 bps** | 8kHz × 8 bit/sample, μ-law/A-law, telephony standard since 1960s |
| AMR-NB (cellular voice) | **4,750–12,200 bps** | 8 rates; 12.2 kbps is the common "full rate" used on GSM/3G |
| Opus (VoIP) | ~6,000–24,000 bps for speech | Reference point used by Lyra/EnCodec papers |
| Codec2 | **450–3200 bps** | Open-source, sinusoidal coding, purpose-built for HF/VHF radio. Modes: 3200, 2400, 1600, 1400, 1300, 1200, 700, 450 bps. 8kHz sample rate. [GitHub](https://github.com/drowe67/codec2) |
| MELPe (NATO STANAG 4591 / MIL-STD-3005) | **600 / 1200 / 2400 bps** | Triple-rate, 22.5ms frames, 180 samples @ 8kHz, includes noise preprocessor. [melp.org](https://melp.org/) |
| Google Lyra (neural) | **3,000 bps** | Beats Opus @ 8kbps (>60% bandwidth reduction) via generative model on speech features, 40ms frames. [Google Research blog](https://research.google/blog/lyra-a-new-very-low-bitrate-codec-for-speech-compression/) |
| Lyra v2 | **3.2 / 6 / 9.2 kbps** | Matches Opus at 10/13/14 kbps respectively. [Google Open Source blog](https://opensource.googleblog.com/2022/09/lyra-v2-a-better-faster-and-more-versatile-speech-codec.html) |
| Meta EnCodec (neural) | **1.5–24 kbps** | 3kbps EnCodec beats Lyra-v2@6kbps and Opus@12kbps (MUSHRA scores); ~10x compression vs MP3 at equal quality via entropy coding on top. [alphaXiv](https://www.alphaxiv.org/abs/2210.13438), [AudioCraft](https://audiocraft.metademolab.com/encodec.html) |
| **Raw ASCII text of speech content** | **~100–125 bps** | Derived below |
| Phoneme-sequence transmission | **~80–100 bps** | Academic ultra-low-rate reference point |
| STCTS (2025, generative semantic codec) | **~80 bps** | Decomposes speech into linguistic content + prosody + timbre; claims 75× reduction vs Opus. [arXiv 2512.00451](https://arxiv.org/html/2512.00451v1) |

**Text-as-transport math (the core argument for iTantra):**
- Average conversational speaking rate: **130–150 words/min** ([VirtualSpeech](https://virtualspeech.com/blog/average-speaking-rate-words-per-minute), [Podcastify](https://podcastify.io/blog/how-many-words-per-minute-speaking))
- Average English word length ≈ 4.7 characters + 1 space ≈ 5.7 chars/word
- 140 wpm × 5.7 chars ≈ 800 chars/min ≈ **13.3 chars/sec**
- At 8 bits/char (plain ASCII, no compression): **~107 bps**
- With simple entropy coding (English text entropy ≈ 1.0–1.5 bits/char): could drop to **~15–20 bps**

**So: text needs roughly 100–125 bps raw, vs**
- Codec2 (450–3200 bps): **4×–30× more** than text
- MELPe (600–2400 bps): **6×–22× more** than text
- AMR-NB (12,200 bps): **~115× more** than text — lands right in the "100–200×" range
- Raw PCM (64,000 bps): **~600× more** than text

This is the headline number for iTantra: **transmitting recognized text instead of any waveform is a ~100–600× bandwidth reduction over even the best low-bitrate speech codecs**, and text survives on links (LoRa, weak Bluetooth, SMS-class bearers) where no voice codec — not even 450bps Codec2 — can get a usable signal through.

Sources: [Codec2 GitHub](https://github.com/drowe67/codec2), [MELPe/melp.org](https://melp.org/), [Lyra](https://research.google/blog/lyra-a-new-very-low-bitrate-codec-for-speech-compression/), [Lyra v2](https://opensource.googleblog.com/2022/09/lyra-v2-a-better-faster-and-more-versatile-speech-codec.html), [EnCodec](https://www.alphaxiv.org/abs/2210.13438), [G.711/AMR](https://www.gl.com/voice-codecs.html), [VoiceAge AMR-NB](https://voiceage.com/AMR-NB.AMR.html), [speaking rate](https://virtualspeech.com/blog/average-speaking-rate-words-per-minute).

---

## 2. Ham/military precedent + STT-TTS transceiver prior art

### Military: why 600bps MELPe
MELPe (Mixed-Excitation Linear Predictive enhanced) is the US DoD standard (MIL-STD-3005, 1997) and NATO standard (STANAG 4591, 2002), derived from LPC-10. It runs at 600/1200/2400 bps specifically because military HF/tactical radio links are bandwidth-starved, noisy, and jammed/contested — the same constraints (unreliable, low-throughput channel) that disaster-zone comms face. Source: [MELP.org](https://melp.org/), [Adaptive Digital](https://www.adaptivedigital.com/melpe/), [RadioReference wiki](https://wiki.radioreference.com/index.php/MELP).

### Ham radio: FreeDV
FreeDV is open-source HF digital voice (LGPL), built by David Rowe (VK5DGR) and an international ham team, and is the reference application for Codec2. It fits Codec2-encoded voice (700–2400 bps typical) inside a standard SSB channel using a 15-carrier FDM modem. The flagship new mode is "RADE" (Radio Autoencoder — a neural-net-based mode). [freedv.org](https://freedv.org/), [FreeDV spec](https://freedv.org/freedv-specification/).

### LoRa + Codec2 voice — direct hardware prior art relevant to iTantra's "radio device" leg
- **QMesh** (Hackaday.io project) — LoRa mesh voice network where every node is also a repeater; carries Codec2-encoded voice frames over LoRa using KISS-protocol framing, aimed at emergency comms (EMCOMM). [Hackaday.io](https://hackaday.io/project/161491-qmesh-a-lora-based-voice-mesh-network)
- **esp32_loradv** — ESP32-based handheld using SX1268 LoRa/FSK radio modules (UHF 70cm) running Codec2/Opus digital voice, functions like a standard FM walkie-talkie. [GitHub](https://github.com/sh123/esp32_loradv)
- **codec2_talkie** — turns an Android phone itself into a Codec2/Opus DV APRS transceiver over Bluetooth/BLE/USB/TCPIP to an external radio. [GitHub](https://github.com/sh123/codec2_talkie)
- **LILYGO T3-S3 MVSR** — commercial LoRa walkie-talkie kit (2025). [CNX Software](https://www.cnx-software.com/2025/03/28/a-lora-based-walkie-talkie-meet-lilygo-t3-s3-mvsr-lora-voice-communication-kit/)
- **lora_codec2** (STM32F4 + SX1262) — half-duplex Codec2-over-LoRa transceiver reference build. [GitHub](https://github.com/dudmuck/lora_codec2)

This is strong "prior art exists, ours is smarter" ammo: these projects all still ship a compressed **voice waveform** (Codec2 frames) over LoRa. iTantra's differentiator is going one level further — shipping **recognized text**, which is 4–30× smaller than even Codec2 frames and re-synthesizing speech only at the receiving end.

### Academic STT→TTS transmission papers (direct precedent for iTantra's core idea)
- **"Voice over Low Data Rate Networks Using Speech-to-Text and Semantic Compression"** (2025) — architecture: speech-to-text → optional LLM-based semantic summarization → text-to-speech at receiver, explicitly to cut transmission time/latency. Reports **up to 94% latency reduction** vs sending compressed audio. [ResearchGate](https://www.researchgate.net/publication/394380603_Voice_over_Low_Data_Rate_Networks_Using_Speech-to-Text_and_Semantic_Compression) — this is almost exactly iTantra's architecture, published as research in 2025.
- **STCTS** (2025) — generative semantic speech compression decomposing speech into content/prosody/timbre, ~80 bps, 75× reduction vs Opus. [arXiv 2512.00451](https://arxiv.org/html/2512.00451v1)
- **"Semantic-preserved Communication System for Highly Efficient Speech Transmission"** (2022) — transmits only semantic-relevant info for speech recognition, ~90% reduction in latent semantic features vs full waveform. [arXiv 2205.12727](https://arxiv.org/pdf/2205.12727)
- Phoneme-sequence transmission cited at **80–100 bps** vs 32–64 kbps for waveform — direct academic confirmation of the order-of-magnitude iTantra relies on.

---

## 3. Semantic communication research (6G academic legitimacy)

This is a recognized, active 6G research subfield — good for a literature-review slide giving the project academic grounding.

- **Qin, Tao, Lu, Tong, Li — "Semantic Communications: Principles and Challenges"** (arXiv 2201.01389, Dec 2021). Foundational survey. Authors: Zhijin Qin, Xiaoming Tao (Tsinghua), Jianhua Lu, Wen Tong, Geoffrey Ye Li. Defines semantic communication as "transmission of semantic information conveyed by the source rather than accurate reception of each bit." [arXiv](https://arxiv.org/abs/2201.01389)
- **DeepSC-S** — deep-learning semantic communication system for speech signals; attention mechanism + squeeze-and-excitation network to preserve essential (semantic) speech information at low bitrate/SNR. [arXiv 2102.12605](https://arxiv.org/pdf/2102.12605)
- **DeepSC-ST** — successor using speech recognition + speech synthesis as the transmission task itself: encoder extracts recognition-relevant semantic features, decoder recovers text at the receiver, "significantly reduces required data transmission without performance degradation." (IEEE Trans. Wireless Comm.) [ACM DL](https://dl.acm.org/doi/10.1109/TWC.2023.3240969), [ResearchGate](https://www.researchgate.net/publication/368316993_Deep_Learning_Enabled_Semantic_Communications_with_Speech_Recognition_and_Synthesis)
- **Task-Oriented Multi-User Semantic Communications** — Xie, Qin, Tao, Letaief, IEEE JSAC 2022, vol 40(9), pp.2584-2597.
- Broader context: semantic communications are called out by IEEE ComSoc as a "Best Readings" topic and are widely framed as core to native-AI 6G standardization roadmaps (arXiv 2509.12758).

**Framing for the SIH pitch**: iTantra's STT→text→TTS pipeline is a real-world, deployable instance of exactly what semantic communication researchers are trying to formalize (Tsinghua/Qin-Tao school, Google Lyra, Meta EnCodec) — except instead of transmitting learned latent embeddings, it transmits human-readable text, which is simpler, more robust, debuggable, and works over any bearer including SMS-class links.

---

## 4. LoRa: Meshtastic, hardware, legal (India)

### Meshtastic
Open-source firmware for LoRa mesh text messaging on cheap ESP32+LoRa boards.
- Real-world range: **1–3 km urban**, **3–10 km rural**, up to **15–20 km line-of-sight** from elevation with standard dipole antennas.
- Bitrate: LoRa typically **1–5 kbps**, messages capped around **~200 characters**.
- This is well above iTantra's text bitrate need (~13 chars/sec / ~100 bps) — meaning LoRa is comfortably enough bandwidth for STT-text payloads with huge margin, unlike for compressed voice.
Source: [Meshtastic DIY guide](https://adrelien.com/meshtastic-diy-how-to-build-your-own-meshtatic-node-esp32-lora-radio/), [CircuitDigest](https://circuitdigest.com/videos/diy-meshtastic-using-esp32-build-your-own-private-off-grid-network), [Seeed Studio guide](https://www.seeedstudio.com/blog/2026/05/26/esp32-lora-guide/)

### Hardware cost (India)
- XIAO ESP32S3 + LoRa (862–930MHz): ~thumb-sized, 2–5km range w/ antenna. [Fab.to.Lab](https://www.fabtolab.com/seeed-xiao-esp32s3-meshtastic-lora)
- ESP32 + SX1278 LoRa module w/ OLED: **₹1,650–₹1,990** in India (Compo India / Prayog India / Robocraze / Robu.in / Zbotic). SX1278 (433MHz): ~-148dBm sensitivity, +20dBm output, up to **2.6km open-air**. [Compo India](https://compoindia.com/product/esp32-lora-sx1278-0-96-inch-blue-oled-display-bt-wifi-module-for-arduino/), [Prayog India](https://www.prayogindia.in/product/esp32-lora-sx1278-0-96-inch-blue-oled-display-bt-wifi-module-for-arduino/)
- Global reference (US pricing, gives scale): ESP32S3 + SX1262 for **~$10 (~₹850)**. [via Seeed/Meshnology search]

### Legal / regulatory (India)
- LoRa 865–867 MHz = **IN865** frequency plan, license-exempt short-range device band under DoT/WPC regulations.
- **Duty cycle: max 1% per channel per hour** (transmit 1 sec → wait 99 sec on same freq) — same order as European ETSI rules.
- Three mandatory IN865 channels: **865.0625, 865.4025, 865.985 MHz**, 125kHz bandwidth each.
- Max ERP: **30 dBm**.
- Important note: 868MHz is *not* license-free in India — must use the IN865 (865–867) band specifically, not the EU 868MHz plan.
Sources: [Zbotic](https://zbotic.in/2-4ghz-vs-915mhz-lora-frequency-band-selection-guide-india/), [Ensemble Tech](https://www.ensembletech.in/lora-frequency-bands-india/), [Valetron Systems](https://www.valetron.com/868-mhz-frequency-is-not-license-free-in-india-lora-in-india/), [Thejesh GN](https://thejeshgn.com/wiki/notebook/license-free-bands-in-india/)

**Implication**: iTantra's compressed text is small enough to fit comfortably inside the 1% duty-cycle budget even on cheap ₹1,650–2,000 LoRa modules, at multi-km range, fully legally in India with no license.

---

## 5. Disaster comms context — India

### NDMA / SACHET (Common Alerting Protocol)
- **SACHET** = "System for Advanced Communication and Holistic Emergency Transmission" ("sachet" = "to be alert" in Hindi), built by NDMA + C-DOT, launched nationwide **August 2021**.
- Uses **CAP (Common Alerting Protocol)** — open XML standard so alerts from IMD, Central Water Commission, INCOIS, Geological Survey of India all share one structure for interoperable dissemination.
- Delivers via **SMS and Cell Broadcast**, geo-targeted.
- Track record: **over 134 billion SMS alerts** delivered in **19+ Indian languages** to date.
- India also launched a **Cell Broadcast Alert System** for extreme/severe alerts (broadcasts to all phones in a cell regardless of number, no SIM/network registration needed for delivery — bypasses congestion).
Sources: [MSC blog on SACHET](https://www.microsave.net/2025/07/24/turning-the-tide-how-indias-sachet-system-is-reshaping-disaster-preparedness/), [sachet.ndma.gov.in](https://sachet.ndma.gov.in/), [Vajiram cell broadcast](https://vajiramandravi.com/current-affairs/extremely-severe-alert/), [Wikipedia Sachet app](https://en.wikipedia.org/wiki/Sachet_(app))

**Implication for iTantra**: SACHET solves *broadcast* alerting (one-to-many, government-to-citizen) assuming the cellular network is up. iTantra's niche is the gap SACHET can't fill: **peer-to-peer, offline, two-way** voice comms when the tower itself is down — see next section.

### Cell tower failure during disasters — concrete numbers
- **Cyclone Fani (2019)**: only 3% of towers physically lost, but power backup was just 8 hours and power-supply cuts + fiber damage during tree clearance meant restoration took much longer than the physical loss rate suggests. [Deccan Herald / search summary]
- **Cyclone Amphan (2020)**: telecom networks ran at only **65–70% capacity** on day 3 post-cyclone in affected West Bengal coastal districts, due to continuous power outages, fiber cuts, and downed electricity wires blocking restoration crews. [Deccan Herald](https://www.deccanherald.com/india/cyclone-amphan-telecom-networks-operating-at-65-70-capacity-in-affected-districts-says-coai-840844)
- **Himachal Pradesh floods/heavy rain (Aug 2025)**: of 1,761 telecom sites (Airtel/Jio/BSNL/VI) in Chamba, **~66% were down** at rain peak (Aug 27, 2025); network overall restored to 65% a week later. [Diary Times](https://diarytimes.com/2025/09/04/himachal-pradesh-restores-65-of-damaged-telecom-network-after-heavy-rains/)
- **Systemic exposure**: a Coalition for Disaster Resilient Infrastructure study found **~770,000 Indian telecom towers** exposed to climate/disaster hazards (floods, cyclones, earthquakes, lightning, heat stress, landslides). [Business Standard](https://www.business-standard.com/article/economy-policy/telecom-infrastructure-in-india-may-soon-get-disaster-resilient-standards-119102600658_1.html), [Manish Marwah blog](https://www.manishmarwah.org/indias-digital-lifeline-at-risk-the-silent-climate-threat-to-telecom-networks/)

**Implication**: This is the direct justification for iTantra bypassing cellular entirely — real events show 30–70% of local capacity gone for days, precisely when coordination matters most. SACHET/cell broadcast assumes surviving infra; iTantra assumes none.

### Literacy — why voice beats text/SMS-only alerts
- National literacy (2011 census): **74.04%** overall.
- **Rural literacy: 67.77%** (male 76.9%, female 50.6% — big gender gap).
- Lowest state literacy: Arunachal Pradesh 67.44%, Andhra Pradesh 69.38%, Bihar 69.67%, Meghalaya 71.46%, Jharkhand 72.86% — several of these overlap with flood/cyclone-exposed belts (coastal AP, Bihar's flood plains, NE hill-state landslide zones).
Sources: [Vedantu Census 2011 literacy](https://www.vedantu.com/general-knowledge/literacy-rate-among-the-indian-states-census-2011), [Wikipedia Literacy in India](https://en.wikipedia.org/wiki/Literacy_in_India)

**Implication**: In the states most exposed to disaster (rural, flood/cyclone belts), effective literacy for reading an SMS alert quickly under stress is meaningfully below the national average, and rural female literacy is only ~50%. A voice-native system (speak → text → speak) reaches people SMS/text-only alerting structurally under-serves — this is the core equity argument for iTantra's voice-first design over a text-messaging alternative.

---

## 6. Bluetooth/Wi-Fi phone-to-phone (the "or another phone" leg)

| Tech | Range | Throughput | Notes |
|---|---|---|---|
| Bluetooth Classic (RFCOMM) | ~10–100m (varies by class/environment) | up to ~2-3 Mbps (BR/EDR) | Used by Briar for point-to-point sockets |
| BLE (GATT) | ~50m indoor, ~150m outdoor | ~1 Mbps standard; some profiles 125kbps–2Mbps | Low power; EATT allows parallel GATT transactions for better throughput |
| Wi-Fi Direct | 200m+ claimed max | up to ~250 Mbps (regular Wi-Fi speeds) | Device-to-device without AP |
| Wi-Fi Aware (NAN) | 10–90m (30-90m typical) | up to ~100–250 Mbps | Discovery + data session without AP/internet |

Source: [BLE vs WiFi Aware vs NFC](https://bleadvertiserapp.medium.com/ble-vs-wifi-aware-vs-nfc-in-2026-which-wins-3812347834e5)

### How offline P2P messaging apps actually do it
- **Bridgefy**: Bluetooth **mesh**, ~**100m per hop**, self-healing multi-hop topology (message hops device-to-device to extend reach beyond direct range), uses BLE for power efficiency, has end-to-end encryption. **Caveat**: 2020 security research found serious vulnerabilities (deanonymization, message interception/impersonation) in its original protocol — worth citing as a "what not to do" / security-hardening angle if iTantra does mesh relay. [Bridgefy breaking paper](https://eprint.iacr.org/2021/214.pdf), [BrightCoding](https://www.blog.brightcoding.dev/2026/05/25/bridgefy-ios-sdk-revolutionize-offline-messaging-with-bluetooth-mesh)
- **Briar**: does **not** do mesh — opens direct point-to-point sockets over **Bluetooth Classic** (not BLE) to nearby contacts; simpler, no multi-hop relay, messages stored on-device until a connection exists. [Haven blog on Briar](https://havenmessenger.com/blog/posts/mesh-networking-briar/)
- General direct-Bluetooth range across these apps: **10–100m** depending on device/environment.

**Implication**: For iTantra's phone-to-phone leg, direct Bluetooth Classic/BLE gives single-hop range comparable to a room/building (10–100m) — useful for very local relay (e.g., handoff to a person who then relays via LoRa/radio) but not disaster-area range. Wi-Fi Direct/Aware trades some range for far higher throughput, useful if iTantra ever wants to send audio previews, not just text. Given iTantra's payload is tiny (STT text, ~100bps-equivalent), even the slowest of these (BLE at ~1Mbps) is wildly oversized for the payload — the bottleneck is never phone-to-phone throughput, it's the long-haul radio leg (LoRa/embedded radio device), which is why the codec/text-compression story in sections 1-3 matters far more than the BLE/WiFi numbers here.

---

## Implications for iTantra

1. **Lead with the compression number, not the codec.** Text beats even the best purpose-built military/ham vocoders (MELPe 600bps, Codec2 450bps) by 4–30×, and beats standard cellular/VoIP codecs (AMR-NB 12.2kbps, Opus) by ~100–200×. This is a stronger, more defensible pitch than "we compress audio" — iTantra doesn't compress voice at all, it eliminates the waveform.

2. **This is not a novel idea in isolation — cite that as a strength.** A 2025 paper ("Voice over Low Data Rate Networks Using Speech-to-Text and Semantic Compression") describes almost exactly iTantra's architecture and reports 94% latency reduction. DeepSC-S/DeepSC-ST (Tsinghua, Qin/Tao) and STCTS (~80bps, 75× vs Opus) are the academic vanguard of "semantic communication," a recognized hot 6G research area. Frame iTantra as **a deployable, India-context implementation of state-of-the-art semantic communication research**, not a hackathon toy.

3. **LoRa is the right radio leg, with huge margin to spare.** Meshtastic-class LoRa hardware (₹1,650–2,000 in India) delivers 1–5 kbps at 1–10km range — that's 10-50× more bitrate than iTantra's text payload needs, and legally usable in India's IN865 band at 1% duty cycle without a license. This means: don't over-engineer the radio protocol; the bottleneck was never bandwidth, it's STT/TTS quality and offline model size on-device. Consider quoting "our payload is <150bps, LoRa gives us 1-5kbps — we have 10-30x headroom for redundancy/FEC/multi-hop" as a wow-line in the pitch.

4. **Existing LoRa-voice hobby projects (QMesh, esp32_loradv, codec2_talkie) are useful "prior art, but we go further" comparisons.** They ship compressed voice (Codec2 frames) over LoRa. iTantra shipping recognized text instead is the next logical step down in bitrate and up in robustness — worth a comparison slide.

5. **Voice-first is an equity argument, not just a UX choice.** Rural literacy (67.77%, rural female 50.6%) in exactly the states most exposed to cyclones/floods (AP, Bihar, NE hill states) means SMS/CAP-based alerting (SACHET) structurally under-serves the people most at risk. iTantra's speak-to-speak pipeline reaches this population where text-based systems can't. Use the SACHET comparison explicitly: SACHET = one-to-many broadcast assuming towers survive; iTantra = two-way peer comms for when towers don't.

6. **Real disaster telecom-outage numbers (Amphan 65-70% capacity, HP floods 2025 ~66% sites down, 770,000 towers exposed nationally) are the strongest available justification for "why bypass cellular at all."** Use these instead of generic "disasters knock out networks" claims — they're specific, recent (2025), and Indian.

7. **Bluetooth/Wi-Fi P2P range/throughput is a non-issue for the payload size** — don't spend pitch time optimizing this leg; the interesting engineering (and the demo's wow-factor) is entirely in the STT/TTS quality at the edges and the radio-leg compression story.

8. **Security note worth flagging internally (not necessarily in the pitch)**: if iTantra does any multi-hop mesh relay (like Bridgefy), the 2020 Bridgefy vulnerability disclosure (deanonymization, message tampering) is a cautionary precedent — plan encryption/auth from day one rather than retrofitting.
