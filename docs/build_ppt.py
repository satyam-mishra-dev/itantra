#!/usr/bin/env python3
"""Build iTantra SIH2026 idea PPT from the official empty template."""
import copy, shutil
from pptx import Presentation
from pptx.util import Inches as I, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn

SRC = '/Users/satyammishra/Downloads/SIH2026-IDEA-Presentation-Format.pptx'
OUT = '/Users/satyammishra/Desktop/new-project/sih2026/itantra/docs/SIH2026-iTantra-idea-PPT.pptx'

NAVY = RGBColor(0x1F, 0x38, 0x64)
ORANGE = RGBColor(0xC5, 0x5A, 0x11)
INK = RGBColor(0x26, 0x26, 0x26)
GRAY = RGBColor(0x59, 0x59, 0x59)
LINKBLUE = RGBColor(0x05, 0x63, 0xC1)

prs = Presentation(SRC)
S = list(prs.slides)

def clear_tb(tf):
    for p in list(tf.paragraphs[1:]):
        p._p.getparent().remove(p._p)
    p0 = tf.paragraphs[0]
    for r in list(p0.runs):
        r._r.getparent().remove(r._r)
    return tf

def para(tf, runs, size=11, space_after=4, space_before=0, align=None, first=False, line=None):
    """runs: list of (text, bold, color) or (text,bold,color,url)"""
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    if space_after is not None: p.space_after = Pt(space_after)
    if space_before: p.space_before = Pt(space_before)
    if align: p.alignment = align
    if line: p.line_spacing = line
    for spec in runs:
        text, bold, color = spec[0], spec[1], spec[2]
        r = p.add_run(); r.text = text
        r.font.name = 'Arial'; r.font.size = Pt(size); r.font.bold = bold
        r.font.color.rgb = color
        if len(spec) > 3 and spec[3]:
            r.hyperlink.address = spec[3]
    return p

def box(slide, x, y, w, h, fill=None, border=None, bw=1.0, shadow=False, rounded=True):
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE, I(x), I(y), I(w), I(h))
    sh.shadow.inherit = False
    if fill: sh.fill.solid(); sh.fill.fore_color.rgb = fill
    else: sh.fill.background()
    if border: sh.line.color.rgb = border; sh.line.width = Pt(bw)
    else: sh.line.fill.background()
    tf = sh.text_frame; tf.word_wrap = True
    tf.margin_left = I(0.08); tf.margin_right = I(0.08); tf.margin_top = I(0.04); tf.margin_bottom = I(0.04)
    for r in list(tf.paragraphs[0].runs): r._r.getparent().remove(r._r)
    return sh

def tbox(slide, x, y, w, h):
    sh = slide.shapes.add_textbox(I(x), I(y), I(w), I(h))
    tf = sh.text_frame; tf.word_wrap = True
    return sh, tf

def stage(slide, x, y, w, h, label, fill, border, size=8.5):
    sh = box(slide, x, y, w, h, fill=fill, border=border, bw=1.25)
    tf = sh.text_frame; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    para(tf, [(label, True, INK)], size=size, space_after=0, align=PP_ALIGN.CENTER, first=True, line=0.95)
    return sh

def arrow(slide, x, y, w, h, shape=MSO_SHAPE.RIGHT_ARROW):
    sh = slide.shapes.add_shape(shape, I(x), I(y), I(w), I(h))
    sh.shadow.inherit = False
    sh.fill.solid(); sh.fill.fore_color.rgb = RGBColor(0xAE, 0xB6, 0xC3)
    sh.line.fill.background()
    return sh

# ---------- SLIDE 1: title fields ----------
s1 = S[0]
for sh in s1.shapes:
    if sh.name == 'TextBox 9':
        tf = clear_tb(sh.text_frame)
        rows = [
            ('Problem Statement ID – ', 'SIH26173', 22),
            ('Problem Statement Title- ', 'iTantra – Indian Multilingual TTS & STT Aided Neural Transceiver Radio Access for low bitrate links', 17),
            ('Theme- ', 'Disaster Management / Miscellaneous', 22),
            ('PS Category- ', 'Software', 22),
            ('Team ID- ', '______', 22),
            ('Team Name- ', 'Null Pointers', 22),
        ]
        first = True
        for label, val, sz in rows:
            para(tf, [(label, True, INK), (val, False, INK)], size=sz, space_after=10, first=first, line=1.05)
            first = False

# team-name ovals on all slides
for s in S:
    for sh in s.shapes:
        if sh.has_text_frame and 'Your Team Name' in sh.text:
            tf = clear_tb(sh.text_frame)
            tf.word_wrap = True
            para(tf, [('Null\nPointers', True, INK)], size=11, space_after=0, align=PP_ALIGN.CENTER, first=True)

def kill_placeholder(slide):
    for sh in list(slide.shapes):
        if sh.name == 'TextBox 8':
            sh._element.getparent().remove(sh._element)

# ---------- SLIDE 2: IDEA TITLE ----------
s2 = S[1]; kill_placeholder(s2)
_, tf = tbox(s2, 0.30, 1.10, 12.75, 0.82)
para(tf, [('iTantra', True, ORANGE),
          (' turns any Android phone into an offline semantic transceiver: speech → on-device STT (10 Indian languages) → ~45-byte compressed text over any surviving link → natural speech at the far end. ', True, INK),
          ('Voice that travels as text — 100–600× less bandwidth than any voice codec.', True, NAVY)], size=13, first=True, line=1.05)

_, tf = tbox(s2, 0.30, 1.95, 8.35, 4.95)
para(tf, [('The Problem We Solve', True, NAVY)], size=13, first=True, space_after=3)
prob = [
    ('Towers die in disasters: ', 'Cyclone Amphan knocked out ~7,000 of 14,167 WB cell towers; networks ran at 65–70% for days (COAI).'),
    ('Text alerts miss the vulnerable: ', 'rural literacy 67.8% (female ~50.6%) — SMS structurally under-reaches disaster-prone belts.'),
    ('Language exclusion: ', '~90% of rural India communicates only in its mother tongue, across 22 scheduled languages.'),
    ('Voice is too heavy for weak links: ', 'raw voice is 64,000 bps; even NATO’s MELPe codec needs 600 bps — nothing survives a dying channel.'),
]
for i, (b, rest) in enumerate(prob, 1):
    para(tf, [(f'{i}. ', True, INK), (b, True, INK), (rest, False, INK)], size=10.5, space_after=2, line=1.0)
para(tf, [('How iTantra Solves It', True, NAVY)], size=13, space_after=3, space_before=6)
sol = [
    ('On-device STT: ', 'AI4Bharat IndicConformer (int8 ONNX, MIT) — 9 Indic languages + Whisper English; fully offline.'),
    ('Pause-aware sentences: ', 'Silero VAD segments speech into sentences during the PTT hold, streamed as they form.'),
    ('Text, not waveform: ', 'the speech content is ~107 bps as text — under Codec2’s 450 bps floor.'),
    ('VarnaCode: ', 'Indic-script entropy coding ~5–6 bits/char vs UTF-8’s 24 → a sentence in ~45 bytes = one LoRa frame.'),
    ('Natural voice out: ', 'AI4Bharat FastPitch + Piper TTS (MIT), sentence-streamed; eSpeak-NG fallback — never silent.'),
    ('Alert mode: ', 'priority frames auto-play at max volume, non-interruptible, with a place-name pronunciation lexicon.'),
    ('Walkie-talkie loop: ', 'two phones, push-to-talk: STT mode ↔ TTS mode; app off = normal phone (the PS verification loop).'),
    ('Any bearer: ', 'Wi-Fi (NSD+TCP) · Bluetooth RFCOMM · ₹1,650 ESP32-LoRa bridge (km-range, IN865 license-free).'),
    ('Live Evaluation Mode: ', 'the app measures its own CER/WER, RTF & mouth-to-ear latency — the rubric, demoed live.'),
]
for i, (b, rest) in enumerate(sol, 1):
    para(tf, [(f'{i}. ', True, INK), (b, True, INK), (rest, False, INK)], size=10.5, space_after=2, line=1.0)

usp = box(s2, 8.85, 1.95, 4.18, 4.35, fill=RGBColor(0xFD, 0xF3, 0xEC), border=ORANGE, bw=1.5)
tf = usp.text_frame
para(tf, [('USP', True, ORANGE)], size=14, first=True, space_after=6, align=PP_ALIGN.CENTER)
for i, u in enumerate(['Text is the codec — 100–600× below any voice codec',
                       'VarnaCode — compression built for Indic scripts',
                       'Live Evaluation Mode — rubric measured on stage',
                       '₹1,650 LoRa bridge — the low-bitrate link, physical',
                       '100% offline, Bhashini-lineage open models'], 1):
    para(tf, [(f'{i}. ', True, INK), (u, True, INK)], size=11, space_after=7, line=1.05)

# ---------- SLIDE 3: TECHNICAL APPROACH ----------
s3 = S[2]; kill_placeholder(s3)
_, tf = tbox(s3, 0.28, 1.12, 5.25, 5.75)
para(tf, [('Technologies', True, NAVY)], size=12.5, first=True, space_after=3)
tech = [
    ('Native Kotlin + Jetpack Compose; ', 'foreground service (mic type) + audio-focus discipline built for Android 14+.'),
    ('sherpa-onnx (Apache-2.0): ', 'one JNI surface for STT + TTS + VAD — 14.5k★, active.'),
    ('STT: ', 'IndicConformer int8 ONNX (MIT) ×9 languages + whisper.cpp tiny for English.'),
    ('TTS: ', 'Piper VITS ×6 + AI4Bharat FastPitch+HiFi-GAN ONNX ×4; eSpeak-NG fallback.'),
    ('Silero VAD (~2 MB) ', 'sentence chunking; Oboe (AAudio) 16 kHz low-latency audio.'),
    ('Transports: ', 'NSD/mDNS + TCP · Bluetooth RFCOMM · ESP32+SX127x LoRa (IN865, 1% duty).'),
    ('Protocol: ', 'VarnaCode coder + iTantra Frame [lang | priority | seq | CRC-16] — bearer-agnostic.'),
    ('Compliance: ', '100% open-source (NC/proprietary SDKs excluded) · zero network calls.'),
]
for b, rest in tech:
    para(tf, [('• ', False, INK), (b, True, INK), (rest, False, INK)], size=10, space_after=2.5, line=1.0)
para(tf, [('Methodology', True, NAVY)], size=12.5, space_after=3, space_before=5)
for b, rest in [
    ('P0 desktop twin: ', 'same models on laptop — CER/RTF measured before any Android code; int8 ladder if tight.'),
    ('P1→P5: ', 'Android spine + Hindi loop → 10 languages + alerts → Evaluation Mode → LoRa bridge + AES-GCM hardening.')]:
    para(tf, [('• ', False, INK), (b, True, INK), (rest, False, INK)], size=10, space_after=2.5, line=1.0)

# diagram
_, tf = tbox(s3, 5.75, 1.10, 7.3, 0.32)
para(tf, [('iTantra Pipeline — offline end-to-end', True, NAVY)], size=11, first=True, align=PP_ALIGN.CENTER)
AI_F, AI_B = RGBColor(0xFD, 0xEB, 0xD9), ORANGE
IO_F, IO_B = RGBColor(0xD9, 0xE8, 0xF5), NAVY
PR_F, PR_B = RGBColor(0xE4, 0xF3, 0xE5), RGBColor(0x2E, 0x7D, 0x32)
LK_F, LK_B = RGBColor(0xFF, 0xF6, 0xD6), RGBColor(0xB8, 0x86, 0x0B)
AL_F, AL_B = RGBColor(0xFD, 0xEC, 0xEA), RGBColor(0xC0, 0x39, 0x2B)
bw_, bh, gap, x0, y1 = 1.52, 0.78, 0.34, 5.78, 1.52
r1 = [('Mic\n(Oboe 16 kHz)', IO_F, IO_B), ('Silero VAD\nsentence chunks', AI_F, AI_B),
      ('STT IndicConformer\nint8 · 10 langs', AI_F, AI_B), ('VarnaCode +\niTantra Frame', PR_F, PR_B)]
for j, (lbl, f, b) in enumerate(r1):
    x = x0 + j * (bw_ + gap)
    stage(s3, x, y1, bw_, bh, lbl, f, b)
    if j < 3: arrow(s3, x + bw_ + 0.03, y1 + bh/2 - 0.09, gap - 0.06, 0.18)
xl = x0 + 3 * (bw_ + gap)
arrow(s3, xl + bw_/2 - 0.09, y1 + bh + 0.05, 0.18, 0.32, MSO_SHAPE.DOWN_ARROW)
y2 = y1 + bh + 0.42
r2 = [('Speaker\nvoice-note out', IO_F, IO_B), ('TTS FastPitch/\nPiper · streamed', AI_F, AI_B),
      ('Decode + de-dup\nVarnaCode⁻¹', PR_F, PR_B), ('Link: Wi-Fi · BT ·\nLoRa ~45 B/sent.', LK_F, LK_B)]
for j, (lbl, f, b) in enumerate(r2):
    x = x0 + j * (bw_ + gap)
    stage(s3, x, y2, bw_, bh, lbl, f, b)
    if j < 3: arrow(s3, x + bw_ + 0.03, y2 + bh/2 - 0.09, gap - 0.06, 0.18, MSO_SHAPE.LEFT_ARROW)
arrow(s3, x0 + 1*(bw_+gap) + bw_/2 - 0.09, y2 + bh + 0.05, 0.18, 0.30, MSO_SHAPE.DOWN_ARROW)
stage(s3, x0 + 0.55*(bw_+gap), y2 + bh + 0.38, 2.9, 0.55, 'ALERT frames → max volume, non-interruptible', AL_F, AL_B, size=8.5)

_, tf = tbox(s3, 5.75, 4.62, 7.3, 0.3)
para(tf, [('Proposed Tech Stack', True, NAVY)], size=11, first=True, align=PP_ALIGN.CENTER)
stack = ['Kotlin + Compose', 'sherpa-onnx (Apache-2.0)', 'IndicConformer int8 (MIT)', 'Piper / FastPitch ONNX',
         'Silero VAD', 'Oboe low-latency audio', 'NSD + BT RFCOMM', 'ESP32 LoRa · IN865']
sw, sh_, sg = 1.76, 0.46, 0.10
for j, lbl in enumerate(stack):
    row, col = divmod(j, 4)
    stage(s3, 5.78 + col * (sw + sg), 4.98 + row * (sh_ + 0.12), sw, sh_, lbl,
          RGBColor(0xF2, 0xF3, 0xF7), RGBColor(0x8A, 0x93, 0xA6), size=8)

# ---------- SLIDE 4: FEASIBILITY ----------
s4 = S[3]; kill_placeholder(s4)
pairs = [
    ('On-device speed unproven on budget phones', 'All RTF figures are ARM proxies (Pi-5 class).',
     'P0 benchmarks on a real budget phone first; fallback ladder: int8 → smaller voices → streaming-decode overlap. Edge Conformers already hit RTF 0.19.'),
    ('Community ONNX conversions', 'sherpa-onnx IndicConformer wrappers are community-made, not official.',
     'Budgeted per-language QA; hard fallback = direct ONNX Runtime Mobile on AI4Bharat’s official int8 export.'),
    ('TTS export for 4 languages is our own work', 'Gujarati, Kannada, Tamil, Odia have no ready ONNX voice.',
     'Same FastPitch→ONNX recipe as NVIDIA Riva production; scoped to 4 languages; eSpeak-NG keeps every language audible meanwhile.'),
    ('Wi-Fi Direct is OEM-flaky', 'Pairing silently fails on some skins — a demo-day risk.',
     'Not on the critical path: hotspot + NSD + TCP is the default, Bluetooth RFCOMM the backup; Wi-Fi Direct demoted to stretch.'),
    ('Modern Android background-audio policy', 'Where every stale sample app dies (fg-service types, audio focus).',
     'Built fresh and first in P1 from the current Android 14+ checklist — a known list, not a research problem.'),
    ('STT errors become spoken misinformation', 'A mis-recognition would be confidently re-spoken.',
     'Confidence gate (“repeat that?”), transcript shown both ends, alert pronunciation lexicon for the highest-stakes content.'),
]
colw, colx = 6.20, [0.35, 6.80]
ys = 1.30
for i, (h, pr_, ap) in enumerate(pairs):
    col, row = divmod(i, 3)
    _, tf = tbox(s4, colx[col], ys + row * 1.86, colw, 1.80)
    para(tf, [(f'{i+1}. {h}', True, NAVY)], size=11.5, first=True, space_after=1.5, line=1.0)
    para(tf, [('Problem: ', True, INK), (pr_, False, INK)], size=10, space_after=1.5, line=1.0)
    para(tf, [('Approach: ', True, ORANGE), (ap, False, INK)], size=10, space_after=0, line=1.0)

# ---------- SLIDE 5: IMPACT ----------
s5 = S[4]; kill_placeholder(s5)
imp = box(s5, 0.35, 1.30, 6.25, 5.35, fill=RGBColor(0xF5, 0xF8, 0xFC), border=NAVY, bw=1.25)
tf = imp.text_frame
para(tf, [('Potential Impacts', True, NAVY)], size=14, first=True, space_after=5)
for b, rest in [
    ('Last-mile inclusion: ', 'voice-native two-way comms reach the ~50% of rural women and 1-in-3 rural Indians whom text alerts structurally miss — in their own language, on phones they already own.'),
    ('Completes ISRO’s disaster stack: ', 'the multilingual voice layer for GSAT mobile-radio and VSAT–SDMA low-bitrate links under the Disaster Management Support programme.'),
    ('Resilience economics: ', 'existing phones + a ₹1,650 LoRa node replace ₹8,000–25,000 hardware walkie-talkie pairs for village disaster committees, fisherfolk co-ops, border communities.'),
    ('Research → reality: ', 'a deployable Indian instance of 6G semantic communication — transmit the meaning, not the bits.')]:
    para(tf, [('• ', False, INK), (b, True, INK), (rest, False, INK)], size=11, space_after=7, line=1.05)
ben = box(s5, 6.80, 1.30, 6.20, 5.35, fill=RGBColor(0xFD, 0xF3, 0xEC), border=ORANGE, bw=1.25)
tf = ben.text_frame
para(tf, [('Benefits', True, ORANGE)], size=14, first=True, space_after=5)
for b, rest in [
    ('Social: ', 'literacy-independent; 10 languages ≈ 85%+ of India’s population; the same message serves visually-impaired (voice) and hearing-impaired (transcript) users.'),
    ('Economic: ', 'zero recurring cost — no SIM, no data plan, no server; open-source, so states and NGOs deploy without procurement lock-in.'),
    ('Strategic: ', 'fully sovereign stack — Indian models (Bhashini / AI4Bharat lineage), Indian band plan (IN865), no foreign cloud dependency.'),
    ('Environmental / operational: ', 'int8-efficient by design; LoRa nodes run for days on a power bank — deployable on solar in a total blackout.')]:
    para(tf, [('• ', False, INK), (b, True, INK), (rest, False, INK)], size=11, space_after=7, line=1.05)

# ---------- SLIDE 6: REFERENCES ----------
s6 = S[5]; kill_placeholder(s6)
_, tf = tbox(s6, 0.40, 1.15, 12.55, 5.65)
refs = [
    ('Cyclone Amphan outage: ', '~7,000 of 14,167 WB towers down; networks at 65–70% capacity for days (COAI). ',
     'deccanherald.com', 'https://www.deccanherald.com/india/cyclone-amphan-telecom-networks-operating-at-65-70-capacity-in-affected-districts-says-coai-840844.html'),
    ('The bitrate math: ', 'MELPe 600 bps (NATO STANAG 4591) and Codec2 450 bps vs speech-as-text ≈ 107 bps. ',
     'melp.org · github.com/drowe67/codec2', 'https://github.com/drowe67/codec2'),
    ('Semantic communications (foundational survey): ', 'Qin, Tao, Lu, Tong & Li, 2021. ',
     'arxiv.org/abs/2201.01389', 'https://arxiv.org/abs/2201.01389'),
    ('DeepSC-ST: ', 'speech transceiver transmitting recognition-domain features, IEEE Trans. Wireless Comm. 2023. ',
     'doi.org/10.1109/TWC.2023.3240969', 'https://doi.org/10.1109/TWC.2023.3240969'),
    ('STT over low-data-rate networks: ', 'up to 94% latency reduction vs compressed audio (2025). ',
     'researchgate.net/394380603', 'https://www.researchgate.net/publication/394380603_Voice_over_Low_Data_Rate_Networks_Using_Speech-to-Text_and_Semantic_Compression'),
    ('IndicConformer (AI4Bharat): ', 'MIT license, all 22 Indian languages, official int8 ONNX export; Hindi WER 13.2 (Vaani). ',
     'huggingface.co/ai4bharat', 'https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual'),
    ('AI4Bharat Indic-TTS: ', 'FastPitch + HiFi-GAN, MIT, 13 Indic languages — beats prior open baselines. ',
     'arxiv.org/abs/2211.09536', 'https://arxiv.org/abs/2211.09536'),
    ('CER, not WER, for Indic ASR: ', 'WER disproportionately punishes agglutinative languages (Malayalam, Kannada, Telugu). ',
     'arxiv.org/abs/2203.16601', 'https://arxiv.org/abs/2203.16601'),
    ('J-Alert (Japan): ', 'national disaster alerts spoken by TTS in 5 languages — the mechanism, validated at national scale. ',
     'wikipedia.org/wiki/J-Alert', 'https://en.wikipedia.org/wiki/J-Alert'),
    ('IN865 LoRa legality: ', '865–867 MHz license-free, 1% duty cycle, 30 dBm ERP — km-range at ₹1,650/node. ',
     'ensembletech.in', 'https://www.ensembletech.in/lora-frequency-bands-india/'),
    ('Project repository: ', 'app + ESP32 firmware + evaluation harness + license audit (link added on submission). ', '', ''),
]
first = True
for i, (b, rest, ltxt, url) in enumerate(refs, 1):
    runs = [(f'{i}. ', True, INK), (b, True, INK), (rest, False, INK)]
    if ltxt: runs.append((ltxt, False, LINKBLUE, url))
    para(tf, runs, size=10.5, space_after=5, first=first, line=1.02)
    first = False

# ---------- delete slide 7 (drop rel too) ----------
xml_slides = prs.slides._sldIdLst
sld7 = list(xml_slides)[6]
rId = sld7.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
prs.part.drop_rel(rId)
xml_slides.remove(sld7)

prs.save(OUT)
print('saved', OUT)
