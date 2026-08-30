#!/usr/bin/env python3
"""Build iTantra SIH2026 idea PPT v3 — reference geometry + mermaid/chart assets + critique fixes."""
from pptx import Presentation
from pptx.util import Inches as I, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

SRC = '/Users/satyammishra/Downloads/SIH2026-IDEA-Presentation-Format.pptx'
OUT = '/Users/satyammishra/Desktop/new-project/sih2026/itantra/docs/SIH2026-iTantra-idea-PPT.pptx'
A = '/Users/satyammishra/Desktop/new-project/sih2026/itantra/docs/assets/'

NAVY = RGBColor(0x1F, 0x38, 0x64)
ORANGE = RGBColor(0xC5, 0x5A, 0x11)
INK = RGBColor(0x26, 0x26, 0x26)
LINKBLUE = RGBColor(0x05, 0x63, 0xC1)
PURPLE = RGBColor(0x7B, 0x5B, 0xA6)

prs = Presentation(SRC)
S = list(prs.slides)

def clear_tb(tf):
    for p in list(tf.paragraphs[1:]):
        p._p.getparent().remove(p._p)
    for r in list(tf.paragraphs[0].runs):
        r._r.getparent().remove(r._r)
    return tf

def para(tf, runs, size=11, space_after=4, space_before=0, align=None, first=False, line=None):
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

def box(slide, x, y, w, h, fill=None, border=None, bw=1.0, rounded=True):
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE, I(x), I(y), I(w), I(h))
    sh.shadow.inherit = False
    if fill: sh.fill.solid(); sh.fill.fore_color.rgb = fill
    else: sh.fill.background()
    if border: sh.line.color.rgb = border; sh.line.width = Pt(bw)
    else: sh.line.fill.background()
    tf = sh.text_frame; tf.word_wrap = True
    tf.margin_left = I(0.10); tf.margin_right = I(0.10); tf.margin_top = I(0.05); tf.margin_bottom = I(0.04)
    for r in list(tf.paragraphs[0].runs): r._r.getparent().remove(r._r)
    return sh

def tbox(slide, x, y, w, h):
    sh = slide.shapes.add_textbox(I(x), I(y), I(w), I(h))
    tf = sh.text_frame; tf.word_wrap = True
    return sh, tf

def pic(slide, path, x, y, w):
    return slide.shapes.add_picture(A + path, I(x), I(y), width=I(w))

def kill_placeholder(slide):
    for sh in list(slide.shapes):
        if sh.name == 'TextBox 8':
            sh._element.getparent().remove(sh._element)

# ---------- SLIDE 1 ----------
s1 = S[0]
for sh in s1.shapes:
    if sh.name == 'TextBox 9':
        tf = clear_tb(sh.text_frame)
        rows = [
            ('Problem Statement ID – ', 'SIH26173'),
            ('Problem Statement Title- ', 'iTantra – Indian Multilingual TTS & STT Aided Neural Transceiver Radio Access for low bitrate links'),
            ('Theme- ', 'Disaster Management / Miscellaneous'),
            ('PS Category- ', 'Software'),
            ('Team ID- ', '______'),
            ('Team Name- ', 'Null Pointers'),
        ]
        first = True
        for label, val in rows:  # uniform size, per critique
            para(tf, [(label, True, INK), (val, False, INK)], size=18, space_after=8, first=first, line=1.05)
            first = False
# team oval on slide 1 (reference has it; template omits it here)
ov = s1.shapes.add_shape(MSO_SHAPE.OVAL, I(0.10), I(0.06), I(1.45), I(0.88))
ov.shadow.inherit = False
ov.fill.solid(); ov.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
ov.line.color.rgb = PURPLE; ov.line.width = Pt(1.5)
tf = ov.text_frame; tf.word_wrap = True
para(tf, [('Null\nPointers', True, INK)], size=11, space_after=0, align=PP_ALIGN.CENTER, first=True)

# ovals on the other slides (template placeholder text)
for s in S:
    for sh in s.shapes:
        if sh.has_text_frame and 'Your Team Name' in sh.text:
            tf = clear_tb(sh.text_frame); tf.word_wrap = True
            para(tf, [('Null\nPointers', True, INK)], size=11, space_after=0, align=PP_ALIGN.CENTER, first=True)

# ---------- SLIDE 2: IDEA TITLE ----------
s2 = S[1]; kill_placeholder(s2)
_, tf = tbox(s2, 0.30, 1.16, 12.75, 0.62)
para(tf, [('iTantra:', True, ORANGE),
          (' any Android phone becomes an offline semantic transceiver — speech → on-device STT (10 Indian languages) → ~45-byte text over any surviving link → natural speech at the far end. ', True, INK),
          ('Voice as text: 169× less than cellular voice, 889× less than raw.', True, ORANGE)], size=13, first=True, line=1.05)

pic(s2, 'pipeline-mini.png', 0.45, 1.84, 12.40)          # 8.5:1 → 1.46in tall
_, tf = tbox(s2, 0.45, 3.38, 12.40, 0.34)
para(tf, [('The app grades itself on stage — live CER · RTF · latency. Measured Hindi round-trip CER: 1.6%.', True, ORANGE)],
     size=12.5, first=True, align=PP_ALIGN.CENTER)

_, tf = tbox(s2, 0.30, 3.80, 8.15, 1.40)
para(tf, [('The Problem We Solve', True, NAVY)], size=13, first=True, space_after=3)
for i, (b, rest) in enumerate([
    ('Towers die in disasters: ', 'Amphan knocked out ~7,000 of 14,167 WB cell towers; 65–70% capacity for days (COAI).'),
    ('Text alerts miss the vulnerable: ', 'rural female literacy ~50.6% — silent SMS under-reaches disaster-prone belts.'),
    ('Language exclusion: ', '~90% of rural India communicates only in its mother tongue (22 scheduled languages).'),
    ('Voice is too heavy for weak links: ', 'raw voice is 64,000 bps; even NATO’s MELPe needs 600 bps.'),
], 1):
    para(tf, [(f'{i}. ', True, INK), (b, True, INK), (rest, False, INK)], size=10.5, space_after=2, line=1.0)

usp = box(s2, 8.60, 3.80, 4.30, 1.42, fill=RGBColor(0xFD, 0xF3, 0xEC), border=ORANGE, bw=1.5)
tf = usp.text_frame
para(tf, [('USP', True, ORANGE)], size=13, first=True, space_after=4, align=PP_ALIGN.CENTER)
para(tf, [('1. ', True, INK), ('Text is the codec — 169× less than cellular voice', True, INK)], size=11, space_after=5, line=1.05)
para(tf, [('2. ', True, INK), ('VarnaCode — Indic compression at the entropy floor', True, INK)], size=11, space_after=0, line=1.05)

_, tf = tbox(s2, 0.30, 5.28, 12.60, 1.62)
para(tf, [('How iTantra Solves It', True, NAVY)], size=13, first=True, space_after=3)
for i, (b, rest) in enumerate([
    ('On-device STT with pause-aware sentences: ', 'IndicConformer int8 (MIT) ×9 + Whisper English; Silero VAD streams sentences mid-hold — fully offline.'),
    ('VarnaCode over any bearer: ', 'measured 4.45–5.36 bits/char (all 10 languages) — a sentence in ~45 B via Wi-Fi (NSD+TCP) · Bluetooth RFCOMM · ₹1,650 LoRa (km-range, IN865).'),
    ('Natural voice out: ', 'AI4Bharat FastPitch + Piper TTS (MIT), sentence-streamed; eSpeak-NG fallback — never silent.'),
    ('Alert mode: ', 'priority frames auto-play at max volume, non-interruptible, with a place-name pronunciation lexicon.'),
    ('Walkie-talkie loop: ', 'two phones, push-to-talk: STT mode ↔ TTS mode; app off = normal phone (the PS verification loop).'),
], 1):
    para(tf, [(f'{i}. ', True, INK), (b, True, INK), (rest, False, INK)], size=10.5, space_after=2, line=1.0)

# ---------- SLIDE 3: TECHNICAL APPROACH ----------
s3 = S[2]; kill_placeholder(s3)
_, tf = tbox(s3, 0.28, 1.08, 5.70, 5.75)
para(tf, [('Technologies', True, NAVY)], size=12.5, first=True, space_after=3)
for b, rest in [
    ('Native Kotlin + Jetpack Compose; ', 'foreground service (mic type) + audio-focus discipline for Android 14+; APK 54 MB incl. full speech runtime.'),
    ('sherpa-onnx v1.13.6 (Apache-2.0): ', 'one JNI surface for STT + TTS + VAD — 14.5k★, active.'),
    ('STT: ', 'IndicConformer int8 ONNX (MIT) ×9 languages + whisper.cpp tiny for English.'),
    ('TTS: ', 'Piper VITS ×6 + AI4Bharat FastPitch+HiFi-GAN ONNX ×4; eSpeak-NG fallback.'),
    ('Silero VAD (~2 MB) ', 'sentence chunking · Oboe (AAudio) 16 kHz low-latency audio.'),
    ('Transports: ', 'NSD/mDNS + TCP · Bluetooth RFCOMM · ESP32+SX127x LoRa (IN865, 1% duty).'),
    ('Protocol: ', 'VarnaCode + iTantra Frame [lang · priority · seq · CRC-16] — bearer-agnostic, Kotlin↔Python byte-identical.'),
    ('Compliance: ', '100% open-source (NC/proprietary SDKs excluded) · zero network calls.'),
]:
    para(tf, [('• ', False, INK), (b, True, INK), (rest, False, INK)], size=11, space_after=3.5, line=1.02)
para(tf, [('Methodology', True, NAVY)], size=12.5, space_after=3, space_before=5)
for b, rest in [
    ('P0 desktop twin measured first ', '(CER · RTF · compression) → '),
    ('P1–P5: ', 'Android spine + Hindi loop → 10 languages + alerts → Evaluation Mode → LoRa bridge + AES-GCM.')]:
    para(tf, [('• ', False, INK), (b, True, INK), (rest, False, INK)], size=11, space_after=3.5, line=1.02)

pic(s3, 'architecture.png', 6.20, 1.30, 6.55)             # 1.94:1 → 3.37in tall, clears logo (starts y1.30)
mb = box(s3, 6.20, 4.90, 6.55, 1.55, fill=RGBColor(0xF5, 0xF8, 0xFC), border=NAVY, bw=1.5)
tf = mb.text_frame
para(tf, [('Measured, not estimated — desktop CPU, real models', True, NAVY)], size=12.5, first=True, space_after=4, align=PP_ALIGN.CENTER)
para(tf, [('STT RTF 0.055–0.119 · TTS RTF 0.049 · Hindi round-trip CER 1.6% / WER 7.1%', True, INK)], size=11, space_after=3, align=PP_ALIGN.CENTER)
para(tf, [('VarnaCode v1: 4.45–5.36 bits/char across all 10 languages · 154 protocol assertions green', False, INK)], size=10.5, space_after=3, align=PP_ALIGN.CENTER)
para(tf, [('Kotlin ↔ Python wire-compatible · Android APK builds & tests green', False, INK)], size=10.5, space_after=0, align=PP_ALIGN.CENTER)

# ---------- SLIDE 4: FEASIBILITY ----------
s4 = S[3]; kill_placeholder(s4)
risks = [
    ('On-device speed on budget phones', 'desktop/ARM-proxy RTF only; a budget phone may run tighter.',
     'P0 measured RTF 0.049–0.119 (8–20× real-time headroom); int8 ladder + smaller voices + streaming-decode overlap if a budget phone runs tight. Edge Conformers already hit RTF 0.19.'),
    ('Community ONNX conversions', 'sherpa-onnx IndicConformer wrappers are community-made, not official k2-fsa artifacts.',
     'Per-language QA budgeted; hard fallback = direct ONNX Runtime Mobile on AI4Bharat’s official int8 export — more glue, zero conversion risk.'),
    ('STT errors become spoken misinformation', 'a mis-recognition would be confidently re-spoken at the far end.',
     'Confidence gate (“repeat that?”), transcript shown on both screens, and a pronunciation lexicon for the highest-stakes alert content.'),
]
for i, (h, pr_, ap) in enumerate(risks):
    _, tf = tbox(s4, 0.35, 1.25 + i * 1.62, 8.25, 1.55)
    para(tf, [(f'{i+1}. {h}', True, NAVY)], size=14, first=True, space_after=2.5, line=1.0)
    para(tf, [('Problem: ', True, INK), (pr_, False, INK)], size=12, space_after=2.5, line=1.05)
    para(tf, [('Approach: ', True, NAVY), (ap, False, INK)], size=12, space_after=0, line=1.05)
_, tf = tbox(s4, 0.35, 6.15, 8.25, 0.70)
para(tf, [('Also handled: ', True, NAVY),
          ('Wi-Fi Direct flakiness (hotspot+NSD default, BT RFCOMM backup) · Android bg-audio policy (fg-service built first, compiling) · TTS export scope (4 languages, NVIDIA-Riva recipe, eSpeak-NG meanwhile).', False, INK)],
     size=10.5, first=True, line=1.05)
pic(s4, 'feasibility-card.png', 8.85, 1.05, 4.05)          # 0.698 → 5.81in tall

# ---------- SLIDE 5: IMPACT ----------
s5 = S[4]; kill_placeholder(s5)
imp = box(s5, 0.35, 1.20, 6.15, 2.60, fill=RGBColor(0xF5, 0xF8, 0xFC), border=NAVY, bw=1.25)
tf = imp.text_frame
para(tf, [('Potential Impacts', True, NAVY)], size=13.5, first=True, space_after=4)
for b, rest in [
    ('Last-mile inclusion: ', 'voice-native comms for the ~50% of rural women and 1-in-3 rural Indians whom text alerts miss — in their own language.'),
    ('Completes ISRO’s disaster stack: ', 'the multilingual voice layer for GSAT mobile-radio / VSAT–SDMA low-bitrate links.'),
    ('Resilience economics: ', 'phones + ₹1,650 LoRa node vs ₹8,000–25,000 hardware walkie-talkie pairs.'),
    ('Research → reality: ', 'a deployable Indian instance of 6G semantic communication.')]:
    para(tf, [('• ', False, INK), (b, True, INK), (rest, False, INK)], size=10.5, space_after=4, line=1.03)

# hero number (per critique: the number is the hero, not the chart)
_, tf = tbox(s5, 6.75, 1.02, 6.25, 1.00)
p = para(tf, [('45 bytes', True, ORANGE), ('  = one spoken sentence', True, INK)], size=40, first=True, space_after=1, align=PP_ALIGN.CENTER)
p.runs[1].font.size = Pt(16)
para(tf, [('vs 7,625 B cellular (AMR-NB) · 40,000 B raw voice (G.711)', False, INK)], size=12.5, space_after=0, align=PP_ALIGN.CENTER)

pic(s5, 'chart-bytes.png', 6.95, 2.12, 5.70)               # 1.833 → 3.11in tall, ends 5.23
ben = box(s5, 6.75, 5.33, 6.25, 1.52, fill=RGBColor(0xF5, 0xF8, 0xFC), border=NAVY, bw=1.25)
tf = ben.text_frame
para(tf, [('Benefits', True, NAVY)], size=12.5, first=True, space_after=3)
for b, rest in [
    ('Social: ', 'literacy-independent · 10 languages ≈ 85%+ of India · voice + transcript serve both impairments.'),
    ('Economic & strategic: ', 'zero recurring cost (no SIM/server) · sovereign stack: Indian models, IN865 band, no foreign cloud.'),
    ('Operational: ', 'int8-efficient; LoRa nodes run days on a power bank — solar-deployable in a blackout.')]:
    para(tf, [('• ', False, INK), (b, True, INK), (rest, False, INK)], size=10, space_after=2.5, line=1.0)

pic(s5, 'chart-bitschar.png', 0.55, 3.92, 5.55)            # 1.833 → 3.03in tall, ends 6.95 edge-safe at 6.95? -> y ends 6.95; footer at 6.95
# nudge: chart placed at 3.92 with 3.03h ends 6.95 exactly — acceptable flush with footer top.

# ---------- SLIDE 6: REFERENCES ----------
s6 = S[5]; kill_placeholder(s6)
_, tf = tbox(s6, 0.40, 1.10, 12.55, 4.90)
refs = [
    ('Project repository: ', 'Kotlin app + evaluation harness + firmware — private; jury access on submission. ',
     'github.com/satyam-mishra-dev/itantra', 'https://github.com/satyam-mishra-dev/itantra'),
    ('Working demo: ', 'compiling APK + measured benchmark CSVs live in the repo; demo video added on submission. ', '', ''),
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
    ('IndicConformer (AI4Bharat): ', 'MIT, all 22 Indian languages, official int8 ONNX; Hindi WER 13.2 (Vaani). ',
     'huggingface.co/ai4bharat', 'https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual'),
    ('AI4Bharat Indic-TTS: ', 'FastPitch + HiFi-GAN, MIT, 13 Indic languages — beats prior open baselines. ',
     'arxiv.org/abs/2211.09536', 'https://arxiv.org/abs/2211.09536'),
    ('CER, not WER, for Indic ASR: ', 'WER disproportionately punishes agglutinative languages. ',
     'arxiv.org/abs/2203.16601', 'https://arxiv.org/abs/2203.16601'),
    ('J-Alert (Japan): ', 'national disaster alerts spoken by TTS in 5 languages, validated at national scale. ',
     'wikipedia.org/wiki/J-Alert', 'https://en.wikipedia.org/wiki/J-Alert'),
    ('IN865 LoRa legality: ', '865–867 MHz license-free, 1% duty, 30 dBm — km-range at ₹1,650/node. ',
     'ensembletech.in', 'https://www.ensembletech.in/lora-frequency-bands-india/'),
]
first = True
for i, (b, rest, ltxt, url) in enumerate(refs, 1):
    runs = [(f'{i}. ', True, INK), (b, True, NAVY if i > 2 else ORANGE), (rest, False, INK)]
    if ltxt: runs.append((ltxt, False, LINKBLUE, url))
    para(tf, runs, size=11.5, space_after=11, first=first, line=1.05)
    first = False

ab = box(s6, 0.40, 6.06, 12.55, 0.72, fill=RGBColor(0xF5, 0xF8, 0xFC), border=NAVY, bw=1.5)
tf = ab.text_frame; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
para(tf, [('Already built: ', True, ORANGE),
          ('154 protocol assertions green · measured Hindi loop CER 1.6% · Android APK builds (54 MB incl. speech runtime) · Kotlin ↔ Python wire-compatibility proven on 30 test vectors.', True, INK)],
     size=11.5, first=True, align=PP_ALIGN.CENTER, line=1.05)

# ---------- delete slide 7 ----------
xml_slides = prs.slides._sldIdLst
sld7 = list(xml_slides)[6]
rId = sld7.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
prs.part.drop_rel(rId)
xml_slides.remove(sld7)

prs.save(OUT)
print('saved', OUT)
