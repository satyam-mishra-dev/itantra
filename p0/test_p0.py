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

print(f'OK — {n} assertions passed')
