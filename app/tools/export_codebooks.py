#!/usr/bin/env python3
"""Export p0 VarnaCode codebooks + python-built interop test vectors for the
Kotlin port. Re-run whenever p0/varnacode.py or its codebooks change:
    python3 app/tools/export_codebooks.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
P0 = os.path.join(HERE, '..', '..', 'p0')
sys.path.insert(0, P0)

import varnacode as vc  # noqa: E402
import frame  # noqa: E402

books = {}
for lang in vc.LANGS:
    enc, _ = vc._table(lang)
    sym, esc, eof = {}, None, None
    for k, bits in enc.items():
        if k is vc.ESC:
            esc = bits
        elif k is vc.EOF:
            eof = bits
        else:
            sym[k] = bits
    books[lang] = {'sym': sym, 'esc': esc, 'eof': eof}

out = {'langs': vc.LANGS, 'books': books}

assets = os.path.join(HERE, '..', 'src', 'main', 'assets', 'codebooks.json')
test_res = os.path.join(HERE, '..', 'src', 'test', 'resources', 'codebooks.json')
for path in (assets, test_res):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False)

# Interop vectors: python-packed frames the Kotlin side must unpack identically.
SAMPLES = {
    'en': "Cyclone alert: move to shelter 12 now!",
    'hi': "बाढ़ का पानी बढ़ रहा है, तुरंत निकलें।",
    'bn': "নদীর জল বাড়ছে, এখনই সরে যান।",
    'ta': "வெள்ளம் உயர்கிறது, உடனே வெளியேறுங்கள்.",
    'te': "వరద పెరుగుతోంది, వెంటనే బయలుదేరండి.",
    'gu': "પૂરનું પાણી વધી રહ્યું છે, તરત નીકળો.",
    'mr': "पुराचे पाणी वाढत आहे, लगेच निघा.",
    'kn': "ಪ್ರವಾಹದ ನೀರು ಏರುತ್ತಿದೆ, ಕೂಡಲೇ ಹೊರಡಿ.",
    'ml': "വെള്ളപ്പൊക്കം ഉയരുന്നു, ഉടനെ പുറപ്പെടുക.",
    'or': "ବନ୍ୟା ପାଣି ବଢୁଛି, ତୁରନ୍ତ ବାହାରନ୍ତୁ।",
}
vectors = []
for i, (lang, text) in enumerate(SAMPLES.items()):
    for prio in (frame.NORMAL, frame.ALERT, frame.ACK):
        vectors.append({'lang': lang, 'text': text, 'prio': prio, 'seq': i,
                        'hex': frame.pack(text, lang, prio=prio, seq=i).hex()})

# prosody-flagged plain vector (ver bit 0)
vectors.append({'lang': 'ta', 'text': SAMPLES['ta'], 'prio': frame.ALERT, 'seq': 31, 'pro': 0x26,
                'hex': frame.pack(SAMPLES['ta'], 'ta', prio=frame.ALERT, seq=31, prosody=0x26).hex()})

vec_path = os.path.join(HERE, '..', 'src', 'test', 'resources', 'testvectors.json')
with open(vec_path, 'w', encoding='utf-8') as f:
    json.dump(vectors, f, ensure_ascii=False)

# Encrypted (version-2) vectors — fixed PSK + nonce so Kotlin re-pack is byte-identical.
KEY = b'iTantra-PSK-demo'
NONCE = bytes(range(12))
encv = []
for i, lang in enumerate(('en', 'hi', 'ta')):
    for prio in (frame.NORMAL, frame.ALERT):
        encv.append({'lang': lang, 'text': SAMPLES[lang], 'prio': prio, 'seq': 90 + i,
                     'hex': frame.pack(SAMPLES[lang], lang, prio=prio, seq=90 + i,
                                       key=KEY, nonce=NONCE).hex()})
# encrypted + prosody (ver bits 0+1): prosody outside ciphertext, inside AAD
encv.append({'lang': 'hi', 'text': SAMPLES['hi'], 'prio': frame.ALERT, 'seq': 99, 'pro': 0x26,
             'hex': frame.pack(SAMPLES['hi'], 'hi', prio=frame.ALERT, seq=99,
                               key=KEY, nonce=NONCE, prosody=0x26).hex()})

enc_path = os.path.join(HERE, '..', 'src', 'test', 'resources', 'testvectors_enc.json')
with open(enc_path, 'w', encoding='utf-8') as f:
    json.dump(encv, f, ensure_ascii=False)

print(f'exported {len(books)} codebooks, {len(vectors)} vectors, {len(encv)} encrypted vectors')
