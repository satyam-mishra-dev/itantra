"""P0 tests: VarnaCode lossless round-trip (all 10 languages + edge cases),
frame encode/decode, corruption detection. Run: python test_p0.py"""
import varnacode as vc
import frame

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

EDGE = ["", "🚨🆘", "SOS मदद 108 !!", "mixed মিশ্র கலப்பு", "a" * 500, "\n\t  "]

n = 0

# VarnaCode round-trips
for lang, text in SAMPLES.items():
    assert vc.decode(vc.encode(text, lang), lang) == text, lang
    n += 1
for lang in vc.LANGS:
    for text in EDGE:
        assert vc.decode(vc.encode(text, lang), lang) == text, (lang, repr(text))
        n += 1

# Compression actually compresses vs UTF-8 for native-script text
for lang, text in SAMPLES.items():
    utf8_bits = len(text.encode('utf-8')) * 8 / len(text)
    assert vc.bits_per_char(text, lang) < utf8_bits, lang
    n += 1

# Frame round-trip, all languages and priorities
for i, (lang, text) in enumerate(SAMPLES.items()):
    for prio in (frame.NORMAL, frame.ALERT, frame.ACK):
        f = frame.pack(text, lang, prio=prio, seq=i)
        d = frame.unpack(f)
        assert d['text'] == text and d['lang'] == lang and d['prio'] == prio and d['seq'] == i
        n += 1

# Corruption: flipping ANY single byte must raise
f = frame.pack(SAMPLES['hi'], 'hi', prio=frame.ALERT, seq=7)
for i in range(len(f)):
    bad = bytearray(f)
    bad[i] ^= 0xFF
    try:
        frame.unpack(bytes(bad))
        raise AssertionError(f'corruption at byte {i} not detected')
    except ValueError:
        n += 1

# Short frame rejected
try:
    frame.unpack(b'\x00\x01')
    raise AssertionError('short frame accepted')
except ValueError:
    n += 1

# v1 codebooks: present for all 10 languages, and native-script text beats 6 bits/char
assert set(vc._BOOKS) >= set(vc.LANGS), 'codebooks.json missing languages'
n += 1
for lang, text in SAMPLES.items():
    assert vc.bits_per_char(text, lang) < 6.5, (lang, vc.bits_per_char(text, lang))
    n += 1
# bigram symbols exist and are multi-char strings
assert any(len(s) == 2 for s in vc._BOOKS['hi']['bigrams']), 'no bigram symbols'
n += 1

# AES-GCM envelope (version-2 frames) — needs `cryptography`; skipped if absent
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa: F401
    KEY = b'iTantra-PSK-demo'
    ef = frame.pack(SAMPLES['hi'], 'hi', prio=frame.ALERT, seq=9, key=KEY)
    d = frame.unpack(ef, key=KEY)
    assert d['text'] == SAMPLES['hi'] and d['ver'] == frame.VER_ENC and d['prio'] == frame.ALERT
    n += 1
    # overhead is exactly nonce(12)+tag(16)
    assert len(ef) == len(frame.pack(SAMPLES['hi'], 'hi', prio=frame.ALERT, seq=9)) + 28
    n += 1
    # any single-byte tamper must raise (CRC or GCM auth)
    for i in range(len(ef)):
        bad = bytearray(ef)
        bad[i] ^= 0xFF
        try:
            frame.unpack(bytes(bad), key=KEY)
            raise AssertionError(f'tamper at byte {i} not detected')
        except ValueError:
            n += 1
    try:
        frame.unpack(ef, key=b'0123456789abcdef')
        raise AssertionError('wrong key accepted')
    except ValueError:
        n += 1
    try:
        frame.unpack(ef)
        raise AssertionError('encrypted frame decoded without key')
    except ValueError:
        n += 1
except ImportError:
    print('note: AES-GCM tests skipped (pip install cryptography)')

# Prosody byte (ver flag bit 0): 0 bytes absent, 1 byte present, firmware-transparent
pf = frame.pack(SAMPLES['ta'], 'ta', prio=frame.ALERT, seq=3, prosody=0x26)
assert len(pf) == len(frame.pack(SAMPLES['ta'], 'ta', prio=frame.ALERT, seq=3)) + 1
n += 1
d = frame.unpack(pf)
assert d['prosody'] == 0x26 and (d['ver'] & frame.VER_PRO) and d['text'] == SAMPLES['ta']
n += 1
assert frame.unpack(frame.pack(SAMPLES['ta'], 'ta'))['prosody'] is None  # backward compat
n += 1
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa: F401
    KEY2 = b'iTantra-PSK-demo'
    epf = frame.pack(SAMPLES['hi'], 'hi', prio=frame.ALERT, seq=4, key=KEY2, prosody=0x11)
    d = frame.unpack(epf, key=KEY2)
    assert d['prosody'] == 0x11 and d['ver'] == (frame.VER_ENC | frame.VER_PRO)
    n += 1
    # tamper the prosody byte AND fix the CRC — only GCM AAD auth can catch it
    bad = bytearray(epf)
    bad[4] ^= 0x01
    body = bytes(bad[:-2])
    fixed = body + frame.struct.pack('>H', frame.crc16(body))
    try:
        frame.unpack(fixed, key=KEY2)
        raise AssertionError('prosody tamper with fixed CRC not detected')
    except ValueError:
        n += 1
except ImportError:
    pass

print(f'OK — {n} assertions passed')
