"""Build docs/SIH2026-iTantra-idea-PPT-replica.pptx — a structural replica of last year's
winning deck (SIH25094.pptx): every shape, font and position kept; only text runs and
picture blobs swapped. Run: p0/.venv/bin/python docs/build_replica.py
"""
import copy, os, sys, tempfile
from lxml import etree
from pptx import Presentation
from pptx.oxml.ns import qn
from PIL import Image
from pptx.util import Pt

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.expanduser("~/Downloads/SIH25094.pptx")
TPL = os.path.expanduser("~/Downloads/SIH2026-IDEA-Presentation-Format.pptx")
OUT = os.path.join(HERE, "SIH2026-iTantra-idea-PPT-replica.pptx")
A = os.path.join(HERE, "assets", "replica")
REPO = "https://github.com/satyam-mishra-dev/itantra"

# ---------------------------------------------------------------- helpers
def shape_by_id(slide, sid):
    for sh in slide.shapes:
        if sh.shape_id == sid:
            return sh
    raise KeyError(sid)


def set_paras(shape, specs):
    """specs: list of (src_para_idx, [(text, bold[, url]), ...]).
    Each new paragraph clones pPr + first-run rPr of the source paragraph."""
    tf = shape.text_frame
    src = [copy.deepcopy(p._p) for p in tf.paragraphs]
    body = tf._txBody
    for p in list(tf.paragraphs):
        body.remove(p._p)
    for src_idx, runs in specs:
        pel = copy.deepcopy(src[src_idx])
        rs = pel.findall(qn("a:r"))
        r_tmpl = copy.deepcopy(rs[0]) if rs else None
        for child in list(pel):
            if child.tag in (qn("a:r"), qn("a:br"), qn("a:fld")):
                pel.remove(child)
        end = pel.find(qn("a:endParaRPr"))
        for spec in runs:
            text, bold = spec[0], spec[1]
            if r_tmpl is not None:
                r = copy.deepcopy(r_tmpl)
            else:
                r = etree.SubElement(pel, qn("a:r"))
                etree.SubElement(r, qn("a:rPr"))
                etree.SubElement(r, qn("a:t"))
            rPr = r.find(qn("a:rPr"))
            if rPr is None:
                rPr = etree.Element(qn("a:rPr")); r.insert(0, rPr)
            rPr.set("b", "1" if bold else "0")
            # drop stale hyperlinks from the template run
            for hl in rPr.findall(qn("a:hlinkClick")):
                rPr.remove(hl)
            r.find(qn("a:t")).text = text
            if end is not None:
                end.addprevious(r)
            else:
                pel.append(r)
        body.append(pel)
    # hyperlinks (need python-pptx wrappers)
    for (src_idx, runs), para in zip(specs, tf.paragraphs):
        for spec, run in zip(runs, para.runs):
            if len(spec) > 2 and spec[2]:
                run.hyperlink.address = spec[2]


def replace_pic(slide, shape, img_path, anchor_right=False):
    left, top, w, h = shape.left, shape.top, shape.width, shape.height
    iw, ih = Image.open(img_path).size
    new_w = int(h * iw / ih)
    if anchor_right:              # keep height, preserve aspect, keep right edge
        left, w = left + w - new_w, new_w
    el = shape._element
    parent = el.getparent(); idx = list(parent).index(el)
    parent.remove(el)
    pic = slide.shapes.add_picture(img_path, left, top, w, h)
    parent.remove(pic._element); parent.insert(idx, pic._element)
    return pic


def small_logo():
    """2026 lockup from the official template, downscaled to a sane size."""
    import zipfile
    with zipfile.ZipFile(TPL) as z:
        data = z.read("ppt/media/image2.png")
    p = os.path.join(tempfile.gettempdir(), "sih2026-logo.png")
    with open(p + ".src", "wb") as f:
        f.write(data)
    im = Image.open(p + ".src"); im.thumbnail((1400, 1400)); im.save(p)
    return p


def B(t):  return (t, True)
def N(t):  return (t, False)
def L(u):  return ("LINK", False, u)

# ---------------------------------------------------------------- content
prs = Presentation(SRC)
s1, s2, s3, s4, s5, s6 = prs.slides
logo = small_logo()

# ---- S1
set_paras(shape_by_id(s1, 92), [(0, [B("SMART INDIA HACKATHON 2026")])])
set_paras(shape_by_id(s1, 93), [
    (0, []),
    (1, [B("Problem Statement ID – "), N("SIH26173")]),
    (2, [B("Problem Statement Title- "), N("iTantra – Indian Multilingual TTS & STT Aided Neural Transceiver Radio Access for low bitrate links")]),
    (3, [B("Theme- "), N("Disaster Management")]),
    (4, [B("PS Category- "), N("Software")]),
    (5, [B("Team ID- "), N("______")]),
    (6, [B("Team Name- "), N("Null Pointers")]),
])
for sid in (94, 96):
    replace_pic(s1, shape_by_id(s1, sid), logo, anchor_right=True)
# long PS title: 20pt + keep the text clear of the brain graphic (was 24pt / 12.69in wide)
fields = shape_by_id(s1, 93)
fields.width = int(fields.width * 0.62)
for para in fields.text_frame.paragraphs:
    for r in para.runs:
        r.font.size = Pt(19)

# ---- S2
set_paras(shape_by_id(s2, 104), [(0, [
    B("iTantra, our offline semantic transceiver,"),
    N(" turns any Android phone into a 10-language walkie-talkie: speech becomes ~45-byte text, crosses any surviving link — Wi-Fi, Bluetooth, LoRa, even an analog radio — and is spoken again at the far end."),
])])
set_paras(shape_by_id(s2, 102), [
    (0, [B(" Challenges in a Disaster:")]),
    (1, [B("Towers Die First:"), N(" Cyclone Amphan downed ~7,000 of 14,167 WB cell sites; networks ran at 65–70% for days.")]),
    (2, [B("Text Alerts Miss the Vulnerable:"), N(" rural literacy 73%, rural women ~51% — silent SMS under-reaches the exposed.")]),
    (3, [B("Language Exclusion:"), N(" ~90% of rural India speaks only its mother tongue, across 22 languages.")]),
    (4, [B("Voice Is Too Heavy for Weak Links:"), N(" raw voice is 64 kbps; even NATO's MELPe codec needs 600 bps.")]),
])
set_paras(shape_by_id(s2, 108), [
    (0, [B("How iTantra Provides Solutions")]),
    (1, [B("On-device STT:"), N(" IndicConformer int8 (MIT) ×9 + English; Silero VAD streams sentences mid-hold; fully offline.")]),
    (2, [B("VarnaCode:"), N(" Indic text at 4.45–5.41 bits/char (measured) — a sentence in ~45 bytes, one LoRa frame.")]),
    (3, [B("Natural Voice Out:"), N(" AI4Bharat FastPitch + Piper TTS (MIT), sentence-streamed; eSpeak-NG fallback.")]),
    (4, [B("Alert Mode:"), N(" priority frames auto-play at max volume, non-interruptible, with a place-name lexicon.")]),
    (5, [B("Any Bearer:"), N(" Wi-Fi (NSD+TCP) · Bluetooth RFCOMM · ₹1,650 ESP32 LoRa · AFSK through any analog radio.")]),
    (6, [B("Prosody Byte:"), N(" 1 byte of urgency — panic is spoken fast, loud and twice at the far end.")]),
    (7, [B("Evaluation Mode:"), N(" the app measures its own CER, RTF and latency on stage — real-speech Hindi CER 2.9%.")]),
])
set_paras(shape_by_id(s2, 113), [
    (0, [B("USP")]),
    (1, [B("Text Is the Codec")]),
    (2, [B("VarnaCode Compression")]),
    (3, [B("Voice via Any Radio")]),
    (4, [B("Live Evaluation Mode")]),
    (5, [B("Offline & Open-Source")]),
])
replace_pic(s2, shape_by_id(s2, 112), os.path.join(A, "mindmap.png"))
replace_pic(s2, shape_by_id(s2, 106), logo, anchor_right=True)

# ---- S3
set_paras(shape_by_id(s3, 124), [
    (0, [B("Semantic Transceiver Pipeline:"), N(" Mic → Silero VAD → IndicConformer STT → VarnaCode → 45-byte frame → any bearer → VarnaCode⁻¹ → FastPitch / Piper TTS, on one sherpa-onnx runtime.")]),
    (1, [B("Native Kotlin App:"), N(" foreground service + audio focus (Android 14+), Oboe 16 kHz capture, 54 MB APK with the full speech runtime; ~200 MB language packs.")]),
    (2, [B("VarnaCode + Frame Protocol:"), N(" corpus-trained Indic Huffman coder; frames carry lang · priority · seq · CRC-16, optional AES-128-GCM and a prosody byte; Kotlin ↔ Python ↔ C byte-identical.")]),
    (3, [B("Pluggable Bearers:"), N(" NSD + TCP over hotspot, Bluetooth RFCOMM, ESP32-LoRa bridge (IN865, 1% duty guard) and a Bell-202 AFSK modem for analog radios.")]),
    (4, [B("Measured, Not Estimated:"), N(" real-speech CER hi 2.9% / bn 4.0% / te 7.8%, RTF 0.06; int8 packs 140 MB; 222 protocol assertions; two-phone loop proven.")]),
    (5, [B("Open-Source & Offline:"), N(" MIT/Apache Bhashini-lineage models, zero network calls; proprietary SDKs and NC-licensed models excluded.")]),
])
replace_pic(s3, shape_by_id(s3, 126), os.path.join(A, "architecture.png"))
replace_pic(s3, shape_by_id(s3, 127), os.path.join(A, "techstack.png"))
replace_pic(s3, shape_by_id(s3, 123), logo, anchor_right=True)

# ---- S4
def grp(title, prob, appr, first=False):
    # header clones P0 (numbering start) only for the first group, P4 for the rest so the list continues
    return [
        (0 if first else 4, [B(title)]),
        (1, [B("Problem: "), N(prob)]),
        (2, [B("Approach: "), N(appr)]),
    ]
sp = [(3, [])]
set_paras(shape_by_id(s4, 137),
    grp("Tech Feasibility : On-Device Speed", "budget phones may run slower than our desktop numbers.",
        "int8 models (measured RTF 0.06) + streaming decode; Conformers already run RTF 0.19 on wearables.", True) + sp +
    grp("Operational Feasibility: Model Availability", "community ONNX conversions of IndicConformer are unofficial.",
        "our converter fixes 12 languages' ONNX metadata; fallback = AI4Bharat's official int8 export.") + sp +
    grp("Market (Demand & Adoption)", "hardware walkie-talkies cost ₹8,000–25,000 and speak one language.",
        "phones people already own + a ₹1,650 LoRa node; pilot with a coastal district committee.") +
    grp("Financial (Cost vs Revenue)", "free tools die when funding dries up.",
        "zero recurring cost (no SIM, server, licence); NDMA/SDMA procurement; open-source self-hosting.") + sp +
    grp("Growth and Potential", "22 languages and many bearers to cover.",
        "one model family covers all 22; frames ride any bearer — Bluetooth today, GSAT tomorrow.") +
    grp("Bridging the Trust Gap", "a mis-recognition could become spoken misinformation.",
        "confidence gate, transcript on both screens, alert pronunciation lexicon, encrypted frames.")
)
for para in shape_by_id(s4, 137).text_frame.paragraphs:   # reference wraps less; 12.5pt keeps 6 groups inside the box
    for r in para.runs:
        r.font.size = Pt(12.5)
# continuous 1..6 numbering regardless of renderer: explicit startAt on each numbered header
n = 0
for para in shape_by_id(s4, 137).text_frame.paragraphs:
    pPr = para._p.find(qn("a:pPr"))
    num = pPr.find(qn("a:buAutoNum")) if pPr is not None else None
    if num is not None:
        n += 1
        num.set("startAt", str(n))
replace_pic(s4, shape_by_id(s4, 142), os.path.join(A, "projection.png"))
replace_pic(s4, shape_by_id(s4, 140), os.path.join(A, "feasibility.png"))
replace_pic(s4, shape_by_id(s4, 138), logo, anchor_right=True)

# ---- S5
set_paras(shape_by_id(s5, 152), [
    (0, [B("Potential Impacts")]),
    (1, [B("Last-Mile Inclusion"), N(": voice-native two-way comms reach the ~50% of rural women and 1-in-4 rural Indians whom text alerts miss — in their own language.")]),
    (2, [B("Completes ISRO's Disaster Stack"), N(": the multilingual voice layer for GSAT mobile-radio and VSAT–SDMA low-bitrate links.")]),
    (3, [B("Two-Way Beats Broadcast"), N(": Kerala 2018 — 40+ ham operators aided 2,000+ people when towers died; iTantra puts that on every phone.")]),
    (4, [B("Research → Reality"), N(": a deployable Indian instance of 6G semantic communication — transmit the meaning, not the bits.")]),
])
set_paras(shape_by_id(s5, 158), [
    (0, [B("Benefits")]),
    (1, [B("Literacy-Independent:"), N(" 10 languages ≈ 85% of India; voice serves the visually impaired, transcript serves the hearing impaired.")]),
    (2, [B("Zero Recurring Cost:"), N(" no SIM, data plan or server; open-source, procurement-friendly for states and NGOs.")]),
    (3, [B("Sovereign Stack:"), N(" Indian models (Bhashini / AI4Bharat), Indian band plan (IN865), no foreign cloud.")]),
    (4, [B("Resilient:"), N(" int8-efficient; LoRa nodes run days on a power bank — deployable on solar in a total blackout.")]),
])
replace_pic(s5, shape_by_id(s5, 154), os.path.join(A, "pies.png"))
replace_pic(s5, shape_by_id(s5, 157), os.path.join(A, "bytes.png"))
replace_pic(s5, shape_by_id(s5, 153), logo, anchor_right=True)

# ---- S6
refs = [
    ("Project Repository : ", "Kotlin app + ESP32 firmware + evaluation harness (private; jury access on submission). ", REPO),
    ("Cyclone Amphan Outage:", " ~7,000 of 14,167 WB towers down; networks at 65–70% capacity for days (COAI).", "https://www.deccanherald.com/india/cyclone-amphan-telecom-networks-operating-at-65-70-capacity-in-affected-districts-says-coai-840844.html"),
    ("The Bitrate Math:", " MELPe 600 bps (NATO STANAG 4591) and Codec2 450 bps vs speech-as-text ≈ 107 bps.", "https://github.com/drowe67/codec2"),
    ("Semantic Communications Survey:", " Qin, Tao, Lu, Tong & Li, 2021 — transmit meaning, not bits.", "https://arxiv.org/abs/2201.01389"),
    ("DeepSC-ST:", " speech transceiver transmitting recognition-domain features, IEEE Trans. Wireless Comm. 2023.", "https://doi.org/10.1109/TWC.2023.3240969"),
    ("STT over Low-Data-Rate Links:", " up to 94% latency reduction vs compressed audio (2025).", "https://www.researchgate.net/publication/394380603_Voice_over_Low_Data_Rate_Networks_Using_Speech-to-Text_and_Semantic_Compression"),
    ("IndicConformer (AI4Bharat):", " MIT, all 22 Indian languages, official int8 ONNX; Hindi WER 13.2 (Vaani).", "https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual"),
    ("AI4Bharat Indic-TTS:", " FastPitch + HiFi-GAN, MIT, 13 Indic languages.", "https://arxiv.org/abs/2211.09536"),
    ("CER, not WER, for Indic ASR:", " WER disproportionately punishes agglutinative languages.", "https://arxiv.org/abs/2203.16601"),
    ("WEA Message-Length Study (2024):", " 360-char alerts no better than 90-char — validates the 45-byte design.", "https://pmc.ncbi.nlm.nih.gov/articles/PMC11424238/"),
    ("IN865 LoRa Legality:", " 865–867 MHz licence-free, 1% duty, 30 dBm — km-range at ₹1,650/node.", "https://www.ensembletech.in/lora-frequency-bands-india/"),
]
set_paras(shape_by_id(s6, 168), [(0, [B(a), N(b), L(u)]) for a, b, u in refs])
replace_pic(s6, shape_by_id(s6, 169), logo, anchor_right=True)

prs.save(OUT)
print("wrote", OUT)
