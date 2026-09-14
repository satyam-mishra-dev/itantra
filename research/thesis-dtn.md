# research_dtn.md — Is "delivery-under-disconnection" the right thesis for iTantra (SIH26173)?

Written 2026-09-15. Adversarial check of: "bottleneck is intermittency/asymmetry, not bits; build a DTN message layer; measure delivery ratio + latency."

## 0. The PS text itself (the thing a jury holds in its hand)

Full PS (scraped from the SIH portal dump, `data/sih2026_ps_20260822_211225.json` in
https://github.com/NoBugNinja/Smart-India-Hackathon-SIH-2026-Problem-Statements):

- "stream the data through wifi/Bluetooth connected embedded device or another phone with same application with **minimal latency**"
- "alert type messages will be announced at highest volume **non-interruptible**"
- "two phones ... connected via wifi or Bluetooth ... work like a **walkie talkie** using push to talk"
- **Rubric: Efficiency 20% (model/app size, idle CPU) · Accuracy 40% (WER, TTS legibility) · Latency 20% (STT delay, TTS delay, RTF, end-to-end delta)** — 80% named; nothing names range, mesh, delivery, or disconnection.
- Restrictions: open-source only, fully offline, low/mid-range Android.

So the PS is 100% about the STT/TTS loop over a *connected* Wi-Fi/BT link. "Low bitrate links" is in the title only. That is the strongest counter-argument and it is not hand-wavy: a DTN layer scores in **none** of the three weighted buckets and actively raises the one called "latency".

## 1. What links ISRO / NDMA / Indian disaster comms actually use

| Link | Bitrate | Msg size | Latency | Duplex | Outage pattern | Source |
|---|---|---|---|---|---|---|
| **NavIC Messaging Service (L5)** | 50 sym/s, rate-1/2 FEC → **25 bps raw**; one 292-bit subframe / 12 s; **220 bits DAT-SG payload** of which **max 23 bytes text** | 23 B text or 1-byte emergency code (6 codes: border, high tide, cyclone, heavy rain, terrorist attack, tsunami) | ≥12 s per frame per satellite; only PRN 1 (1A) & 7 (1G) (ICD) / 1A & 1E (2022 slides) carry messaging; channel is **time-shared, priority-scheduled** at ISRO's WIMS portal | **One-way broadcast**, addressed by 24-bit terminal ID | It's a scheduled queue, not a link you can lose: "in case when no messages are being uplinked ... the latest message will keep repeating" | ISRO DAT-SG ICD v1.2 (Feb 2021) https://www.isro.gov.in/media_isro/pdf/SateliteNavigation/icd_for_dat-sg_22feb2021_v1.2.pdf ; ICG-16 Oct 2022 slides https://www.unoosa.org/documents/pdf/icg/2022/ICG16/wgc-04.pdf |
| **DAT / DAT-SG uplink** (INSAT UHF DRT transponder) | one burst: ID + GPS position + distress code (Fire/Sinking/Medical/MOB) | ~tens of bytes | burst repeats "every minute for first five minutes and then every five minutes" | Uplink only; DAT-SG gets ack back via NavIC (auto-ack 0x4, manual ack 0x2) | 2022 volume: **325 SG-DAT acks Jan–Oct 2022**; 50 DAT-SG units in ICG trial; ~1 lakh boats with DAT | Azista https://www.azistaaerospace.com/distress-alert-transmitter-dat ; ICG-16 slides; ISRO update on DAT-SG https://www.isro.gov.in/update/09-dec-2021/isro-and-oppo-india-to-work-towards-providing-navic-messaging-services-mobile |
| Inmarsat ISAT phones / BGAN Explorer 510 (NDRF, OSDMA: 58 ISAT phones, all 30 Odisha collectors) | voice 2.4 kbps; BGAN ≤464 kbps | n/a | seconds | full duplex | sky-view + battery; per-minute airtime cost | NIDM training report https://nidm.gov.in/pdf/trgReports/2022/July/Report_18-22July2022aak.pdf ; OSDMA https://www.osdma.org/preparedness/early-warning-communications/satelite-phones/ |
| NDRF HF / VHF sets, ham radio (Kerala 2018: 40+ hams, ~2000 people helped, HF to state EOC) | analog voice; digital 300 bps HF (AX.25/PACTOR), 1200 bps VHF packet, VARA HF ≤8.5 kbps | — | seconds (voice) | half-duplex, one talker at a time | ionospheric fading, operator availability, shared channel | https://thefederal.com/states/south/kerala/network-down-ham-radios-help-coordinate-rescue-in-rain-hit-kerala ; https://www.onallbands.com/emcomm-ham-radio-digital-modes-for-use-during-emergencies/ |
| **LoRa (Meshtastic, IN865, 865–867 MHz, 30 dBm, 100 % duty)** | presets 0.18 kbps (SF12/125k) … 1.07 kbps (LongFast SF11/250k, default) … 21.9 kbps | ~230 B/frame | 1–5 s per hop; hop_limit default 3, max 7 | half-duplex, contention | range gaps (terrain, no LoS), nodes power off, collisions in dense mesh | https://meshtastic.org/docs/overview/radio-settings/ ; https://meshtastic.org/docs/configuration/radio/lora/ ; Meshtastic India (NDRF/SDRF kits) https://www.meshtastic.in/ |

**NavIC killer-fit check — result: NOT a fit as a bearer, but a strong fit as a *design precedent*.**
- Phones cannot transmit on NavIC. The only user→ground path is the DAT UHF burst to an INSAT DRT transponder; the NavIC side is downlink-only, uplinked by ISRO from a web portal (WIMS), then relayed to the phone by the DAT-SG box over Bluetooth (ICD §1, §6).
- Capacity: 23 B text per 12 s subframe per satellite ≈ **15 bps of text, shared nationally**, 2 satellites. A 45 B iTantra sentence = 2 subframes ≈ 24 s + queue wait. So VarnaCode's bytes *do* matter on NavIC, but at "2 frames vs 4" scale, not "possible vs impossible".
- What ISRO actually built around that channel: message IDs per broadcaster, **priority classes (disaster warning, distress alerts) that preempt**, staggering across satellites, repeat-until-replaced, CAP ingestion (IMD/CWC/SASE) → this is exactly a priority store-and-forward queue. That is the honest way to cite NavIC: "ISRO's own emergency channel is a priority-preempted S&F broadcast of ≤23-byte messages; we mirror that on the last mile."

## 2. DTN state of the art that fits phone + ESP32

| Project | What it gives | Licence | Fit |
|---|---|---|---|
| RFC 9171 BPv7 | bundle = primary block (dest/src/report-to EIDs, creation timestamp+seq, lifetime, flags, optional fragment offset) + canonical blocks (hop count, previous node, bundle age), CBOR. **Custody transfer removed from core**; lives in the BIBE draft (custody transfer extension block + compressed custody signal). | spec | Too heavy verbatim (EIDs, CRC, CBOR); the *field list* is the right checklist. https://www.rfc-editor.org/info/rfc9171/ ; https://datatracker.ietf.org/doc/html/draft-ietf-dtn-bibect-04 |
| µD3TN (D3TN GmbH) | lean BPv7/BPv6, POSIX + STM32 origin, MTCP/TCPCL/SPP/BIBE CLAs, "space-tested" | AGPLv3 (GitLab page) — docs page still says BSD; **check before copying** | C, POSIX daemon; not ESP32; AGPL contaminates. Reference only. https://gitlab.com/d3tn/ud3tn ; https://d3tn.gitlab.io/ud3tn/ |
| dtn7-rs | Rust BPv7, epidemic/S&W routing, external CLAs | MIT/Apache-2.0 | Runs on RPi; **BPoL (GHTC 2023) already put it over LoRa on ESP32** — see §4. https://github.com/dtn7/dtn7-rs |
| IBR-DTN | C++ BPv6, had an Android port | Apache-2.0 | Dead since ~2017; Android build bit-rotted. https://github.com/ibrdtn/ibrdtn/wiki |
| Meshtastic | managed flood (SNR-sized contention window; ROUTER role rebroadcasts anyway), dedup on (NodeID, 32-bit packet id), hop_limit 3/7, implicit ACK on broadcast, next-hop for DMs; **Store&Forward = a mailbox on one ESP32-with-PSRAM server**, text only, default 25 msgs / 240-min window, client pulls with "SF" DM; not on the default public channel | GPL-3.0 | Prior art for flood+dedup. Its S&F is *server-pull*, not carry-forward by mobile nodes. https://meshtastic.org/docs/overview/mesh-algo/ ; https://meshtastic.org/docs/configuration/module/store-and-forward-module/ |
| Serval Mesh / Rhizome | epidemic file-bundle sync over Wi-Fi ad-hoc/BT; MeshMS on top | GPLv2 (serval-dna) / GPLv3 (batphone) | Android-native but abandoned; GPL. https://developer.servalproject.org/dokuwiki/doku.php?id=content:tech:rhizome |
| Briar / Bramble (BSP/BTP) | sync protocol over BT/Wi-Fi/Tor, forwarded messages via mailbox | GPLv3 / AGPL desktop | Group-sync semantics, no LoRa, no priority. https://code.briarproject.org/briar/briar-spec |
| Reticulum / Sideband (LXMF) | announce-based routing, LoRa (RNode), propagation nodes = S&F | **"Reticulum License" — non-free, not OSI**; forbids use in ML datasets etc. | **Do not vendor.** Cite only. https://reticulum.network/license.html ; https://github.com/markqvist/Reticulum/discussions/1062 |
| ONE simulator (Keränen/Ott/Kärkkäinen, SIMUTools 2009) | Java DTN sim; standard metrics delivery probability, latency, overhead ratio | GPLv3 | Jury-recognised metric definitions. https://www.netlab.tkk.fi/tutkimus/dtn/theone/pub/the_one_simutools.pdf |
| Meshtasticator (GUVWAF) | discrete-event LoRa/Meshtastic sim in Python | GPL-3.0 | BPoL used it as the Meshtastic baseline. https://github.com/GUVWAF/Meshtasticator |
| Spray-and-Wait (Spyropoulos 2005) | L copies, binary halving; ~90 % fewer transmissions than epidemic, similar delay | paper | The routing to implement. http://conferences.sigcomm.org/sigcomm/2005/paper-SpyPso.pdf |

**Smallest correct subset (write it ourselves, ~300 lines Kotlin + mirrored in Python; no external DTN lib):**
```
bundle header (10 B, prepended inside the existing v2 frame, before AES-GCM so it is authenticated):
  id        4 B  = src16 << 16 | seq16          (dedup key; also the roll-call ACK key)
  created   4 B  unix-seconds                   (bundle age; also orders TTS playback)
  ttl       1 B  minutes (0 = 255)              (expire = created + ttl*60)
  flags     1 B  prio:2 (0 BULK,1 NORMAL,2 ALERT,3 reserved) | hops:3 (max 7) | copies:3 (L, binary S&W)
payload    ≤45 B VarnaCode text (unchanged)
```
- Store: per-node buffer (Room table / ring on ESP32), cap N=256 phone / 32 ESP32; evict order = expired → lowest prio → oldest.
- Dedup: LRU set of 1024 ids (Meshtastic does the same with (from,id)).
- Contact = any bearer session (TCP accept, RFCOMM connect, LoRa beacon heard, AFSK carrier): exchange **summary vector** (list of ids, 4 B each; ≤64 ids/beat), then push what the peer lacks, ALERT first, then newest NORMAL, BULK last.
- Forwarding: binary spray-and-wait, L=4 start; handing over halves copies (1 copy = wait mode: only give to destination). hops++ per relay, drop at 7.
- ACK: the existing 9-byte roll-call ACK becomes the **delivery receipt**; propagate receipts epidemically (they are tiny) so relays purge delivered bundles ("antipacket"/VACCINE). This replaces custody transfer — BPv7 itself dropped custody; don't reintroduce it.
- No fragmentation (45 B fits every bearer above except NavIC, which we cannot transmit on anyway). No EIDs, no CBOR, no CRC beyond GCM tag.
- ALERT prio maps straight onto the PS's "non-interruptible highest-volume announcement" and onto the existing prosody/urgency flag byte → derive prio from spoken urgency + CAP severity.

## 3. Evaluation a jury will accept

Metrics exactly as ONE/BPoL/arXiv-2603.15945 report them: **delivery probability** (delivered/created), **average + p95 latency** (created→first delivery), **overhead ratio** ((relayed − delivered)/delivered). BPoL (GHTC 2023): 20 nodes, 3×3 km, 15 mobile random-waypoint + 5 static, 10 runs, 400 s, message every few s; Meshtastic-like flood ≈ 40–60 % delivery, DTN with trail time median 80 %. arXiv 2603.15945 (2026): Epidemic vs S&W in a stadium-earthquake scenario in ONE — S&W wins delivery with far lower overhead. https://peasec.de/paper/2023/2023_SchmidtKuntkeBauerBaumgaertner_BPOL_GHTC.pdf ; https://arxiv.org/abs/2603.15945

**Python sim for p0 (`sim/dtn_sim.py`, stdlib `heapq` + `random`, ~150 lines):**
- N=20 nodes (15 mobile RWP 1–2 m/s, 5 static) on 3×3 km; contact when d < 500 m (LoRa) — or skip geometry and draw contacts from a Poisson process, mean inter-contact 90 s, contact duration 20 s.
- Bearer model per contact: bitrate ∈ {300, 1070, 10000} bps; airtime = (55 B + 10 B hdr)·8 / bitrate + 0.4 s turnaround; Gilbert-Elliott outage bursts (mean good 60 s / bad 120 s) on top.
- Traffic: 45 B sentence every 30 s, random src→dst, 10 % marked ALERT; TTL 30 min; buffer 256; 3600 s sim; 10 seeds.
- Compare 4 policies on the same trace: **direct-only (today's iTantra)**, **managed flood hop 3 (Meshtastic)**, **epidemic**, **binary S&W L=4 + prio + receipt purge (proposed)**.
- Report the 3 numbers per policy, plus "ALERT p95 latency" as the 4th line because it is the PS's own requirement. Expect: direct ≈ 20–35 %, flood ≈ 45–60 %, epidemic ≈ 90 % @ overhead 10–20×, S&W ≈ 85–90 % @ overhead ~3×. Those are the ranges BPoL/ONE papers show; do not promise them until the sim runs.

**Demo on 3 Android emulators (A, B courier, C):** the app already talks TCP; emulators reach each other via host loopback: `adb -s emulator-5554 forward tcp:9001 tcp:9000` etc., peers connect to `10.0.2.2:900x`. Toggle links with `adb -s emulator-5556 shell cmd connectivity airplane-mode enable|disable`. Script: A–B up, B–C down → A speaks a sentence and an ALERT → B stores (bubble shows "carried, 1/4 copies") → cut A–B, raise B–C → C speaks ALERT first, then sentence; Evaluation card shows delivery latency and hop count; roll-call receipt flows back to A when A–B returns. Whole loop < 90 s on stage.

## 4. Prior-art honesty: what makes a jury say "that's Meshtastic/Briar"

Overlap (say it before they do):
- Store-carry-forward over LoRa with BPv7 and spray-and-wait, on ESP32, evaluated on delivery probability/latency vs Meshtastic: **BPoL, GHTC 2023 (TU Darmstadt)** — essentially the proposed thesis, done. Also LoRAgent (GHTC 2020), Höchst et al. ISCRAM 2020 (LoRa D2D smartphones + rf95modem + DTN7), LOCATE (GLOBECOM 2018). https://idl.iscram.org/files/jonashochst/2020/2291_JonasHochst_etal2020.pdf
- Flood + hop limit + dedup + S&F mailbox: Meshtastic; room servers: MeshCore. Sync-based S&F on phones: Briar, Serval. Propagation nodes: Reticulum/LXMF.
- Speech→text→LoRa→speech in rescue: Li Jia, SPCNC 2023 (ACM) https://dl.acm.org/doi/abs/10.1145/3654446.3654484 ; Voice-over-LoRa (Codec2-style) projects.

Still novel / defensible:
1. **Speech-native bundles**: prio derived from the utterance (urgency prosody flag already in frame) + CAP severity; TTS-side playback policy (ALERT preempts, NORMAL queued in `created` order, BULK never auto-spoken) — nobody's DTN carries a "how to speak this" bit.
2. **Bearer-agnostic S&F including analog radio**: the same 10-byte header rides AFSK over a VHF handset and RFCOMM and LoRa; BPoL/Meshtastic are LoRa-only, Briar/Serval are IP/BT-only.
3. **Receipts as roll-call**: the 9-byte ACK doubles as delivery receipt + antipacket + presence; Meshtastic has implicit ACK only, BPv7 has none in core.
4. **Ten-language VarnaCode payload** keeps the bundle ≤55 B so it fits a single LoRa frame at SF12 and 2 NavIC subframes — the only team whose message can be forwarded by ISRO's real channel unmodified.
None of these is a thesis; each is a paragraph.

## 5. Verdict

**(b), leaning hard toward "correct diagnosis, wrong headline."** Concretely:
- **Correct**: on LoRa/HF/ad-hoc the loss mode is disconnection, not bytes (BPoL, Kerala ham logs, NavIC's own priority queue all say so). Measurable in ~1 week: 10-byte header + buffer + S&W + receipt purge is ~2 days Kotlin, ~1 day ESP32 C, ~1 day Python sim + parity tests, ~1 day emulator demo script. Realistic on top of the current framing/ACK code.
- **But overlaps**: BPoL is the same thesis with the same metrics, published, open-source (dtn7-rs). A well-read ISRO jury discounts "DTN over LoRa" as known; a less-read one hears "Meshtastic".
- **And mis-scores**: the PS rubric is 20/40/20 on size/accuracy/latency of the STT-TTS loop over Wi-Fi/BT "with minimal latency". Making delivery-under-disconnection the headline puts 100 % of the pitch on 0 % of the rubric and contradicts "minimal latency". Strongest counter-argument, verbatim from the PS: *"must instantly and efficiently stream the data ... with minimal latency ... work like a walkie talkie."*

**Recommendation**: keep STT/TTS accuracy + latency + footprint as the thesis (that is where 80 % of marks live and where our CER numbers already are). Ship the minimal S&F layer above as the **robustness chapter** — framed as (i) implementing the PS's own "ALERT non-interruptible" as a priority class end-to-end, (ii) "works when the walkie-talkie link drops", (iii) mirroring ISRO's NavIC priority-queue practice on the last mile — with one Evaluation-Mode card: delivery ratio / p95 latency / overhead from the Python sim, and the 3-emulator courier demo as a 90-second closer. Do **not** add custody transfer, EIDs, CBOR, fragmentation, or any third-party DTN stack (licences: Reticulum non-free, µD3TN AGPL, Meshtastic/Serval/Briar GPL).

Sources not linked inline above: ONE metrics usage in DTN routing comparisons https://www.researchgate.net/publication/338133323_Analysis_of_Epidemic_PROPHET_and_Spray_and_Wait_Routing_Protocols_in_the_Mobile_Opportunistic_Networks ; Meshtastic managed-flood rationale https://meshtastic.org/blog/why-meshtastic-uses-managed-flood-routing/ ; Qualcomm NavIC L1 in phones (positioning only, no messaging) https://www.qualcomm.com/news/releases/2023/12/qualcomm-announces-support-for-india-s-navic-satellite-navigatio ; NavIC scale (40,000 vessels) https://telanganatoday.com/navic-tracks-10400-trains-40000-fishing-vessels-disaster-alerts-operational
