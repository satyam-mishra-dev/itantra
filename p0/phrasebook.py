"""Phrasebook mode: a whole spoken sentence as a ~9-byte, language-neutral frame.

The emergency register repeats itself ("send a boat", "water is rising", "N people
injured"). Those sentences don't need 45 bytes of VarnaCode text: a 12-bit index into
a shared phrasebook, plus an optional numeric slot, is enough — and because every
phone holds the same phrasebook in all 10 languages, the receiver renders it in ITS
OWN language. This is the first honest step on the receiver-language thesis
(research/thesis-receiver-language.md) with zero model cost.

Wire format — reuses the iTantra header untouched (frame.py is not modified):
    byte 0    : ver=0 | lang=15 (phrase marker; LANGS has 10 entries, 15 is free) | prio
    byte 1    : seq
    bytes 2-3 : payload length (3 or 4)
    payload   : fp8 (low byte of the phrasebook fingerprint — mismatched books are
                detected, not mis-spoken) · idx_hi:4 | flags:4 · idx_lo:8 · [n:8]
    last 2    : CRC-16
So 9 bytes without a slot, 10 with — vs ~45 for the same sentence as text.

Sender policy (research/thesis-channel-adaptive.md): the matcher NEVER snaps silently.
match() returns ranked candidates with a score; the app shows the top hit and the
user confirms with one tap (or it falls back to text). Stdlib only.
"""
import json
import os
import re
import struct
import unicodedata

from frame import crc16, NORMAL
from varnacode import LANGS

PHRASE_LANG = 15
FLAG_SLOT = 1
BOOK_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'phrasebook.json')
_SLOT = '{n}'
_book = None


def load(path=BOOK_PATH):
    global _book
    if _book is None or path != BOOK_PATH:
        with open(path, encoding='utf-8') as f:
            raw = json.load(f)
        phrases = raw['phrases']
        canon = json.dumps(phrases, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        _book = {'phrases': phrases, 'fp': crc16(canon.encode('utf-8')), 'version': raw.get('version', 1)}
    return _book


def fingerprint():
    return load()['fp']


def has_slot(idx):
    return _SLOT in load()['phrases'][idx]['en']


def render(idx, lang, n=None):
    """Phrase idx in the receiver's language, slot filled."""
    if lang not in LANGS:
        raise ValueError(f'unknown lang {lang}')
    t = load()['phrases'][idx][lang]
    if _SLOT in t:
        return t.replace(_SLOT, str(n if n is not None else 0))
    return t


def pack(idx, prio=NORMAL, seq=0, n=None):
    book = load()
    if not 0 <= idx < len(book['phrases']) or idx > 0xFFF:
        raise ValueError('bad phrase index')
    flags = 0
    payload = bytes([book['fp'] & 0xFF, ((idx >> 8) & 0xF) << 4, idx & 0xFF])
    if has_slot(idx):
        if n is None or not 0 <= n <= 255:
            raise ValueError('slot value 0..255 required')
        flags |= FLAG_SLOT
        payload = payload[:1] + bytes([payload[1] | flags]) + payload[2:] + bytes([n])
    hdr = struct.pack('>BBH', (PHRASE_LANG << 2) | (prio & 3), seq & 0xFF, len(payload))
    body = hdr + payload
    return body + struct.pack('>H', crc16(body))


def is_phrase_frame(frame_bytes):
    return len(frame_bytes) >= 6 and ((frame_bytes[0] >> 2) & 0xF) == PHRASE_LANG


def unpack(frame_bytes):
    """-> {'idx','n','prio','seq','fp_ok'}; raises on corruption. Does not render —
    the receiver calls render(idx, its_lang, n)."""
    if not is_phrase_frame(frame_bytes):
        raise ValueError('not a phrase frame')
    body, crc = frame_bytes[:-2], struct.unpack('>H', frame_bytes[-2:])[0]
    if crc16(body) != crc:
        raise ValueError('CRC mismatch')
    b0, seq, plen = struct.unpack('>BBH', body[:4])
    payload = body[4:]
    if len(payload) != plen or plen not in (3, 4):
        raise ValueError('length mismatch')
    fp8, b, lo = payload[0], payload[1], payload[2]
    idx = ((b >> 4) << 8) | lo
    flags = b & 0xF
    n = payload[3] if (flags & FLAG_SLOT) else None
    if (flags & FLAG_SLOT) and plen != 4 or (not flags & FLAG_SLOT) and plen != 3:
        raise ValueError('slot flag / length mismatch')
    book = load()
    if idx >= len(book['phrases']):
        raise ValueError('phrase index out of range')
    return {'idx': idx, 'n': n, 'prio': b0 & 3, 'seq': seq, 'fp_ok': fp8 == (book['fp'] & 0xFF)}


# ---------------------------------------------------------------- matching (sender side)

_DIGITS = re.compile(r'\d+')
# spoken numbers -> digits; STT emits words as often as digits. Small on purpose: slots are 0..255
# and the emergency register mostly says one-digit counts, "twenty", "fifty", "hundred".
_NUMWORDS = {
    'en': {'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10, 'twenty': 20, 'fifty': 50, 'hundred': 100},
    'hi': {'शून्य': 0, 'एक': 1, 'दो': 2, 'तीन': 3, 'चार': 4, 'पाँच': 5, 'पांच': 5, 'छह': 6, 'छः': 6, 'सात': 7, 'आठ': 8, 'नौ': 9, 'दस': 10, 'बीस': 20, 'पचास': 50, 'सौ': 100},
    'bn': {'শূন্য': 0, 'এক': 1, 'দুই': 2, 'তিন': 3, 'চার': 4, 'পাঁচ': 5, 'ছয়': 6, 'সাত': 7, 'আট': 8, 'নয়': 9, 'দশ': 10, 'বিশ': 20, 'পঞ্চাশ': 50, 'একশো': 100},
    'ta': {'பூஜ்யம்': 0, 'ஒன்று': 1, 'இரண்டு': 2, 'மூன்று': 3, 'நான்கு': 4, 'ஐந்து': 5, 'ஆறு': 6, 'ஏழு': 7, 'எட்டு': 8, 'ஒன்பது': 9, 'பத்து': 10, 'இருபது': 20, 'ஐம்பது': 50, 'நூறு': 100},
    'te': {'సున్నా': 0, 'ఒకటి': 1, 'రెండు': 2, 'మూడు': 3, 'నాలుగు': 4, 'ఐదు': 5, 'ఆరు': 6, 'ఏడు': 7, 'ఎనిమిది': 8, 'తొమ్మిది': 9, 'పది': 10, 'ఇరవై': 20, 'యాభై': 50, 'వంద': 100},
    'gu': {'શૂન્ય': 0, 'એક': 1, 'બે': 2, 'ત્રણ': 3, 'ચાર': 4, 'પાંચ': 5, 'છ': 6, 'સાત': 7, 'આઠ': 8, 'નવ': 9, 'દસ': 10, 'વીસ': 20, 'પચાસ': 50, 'સો': 100},
    'mr': {'शून्य': 0, 'एक': 1, 'दोन': 2, 'तीन': 3, 'चार': 4, 'पाच': 5, 'सहा': 6, 'सात': 7, 'आठ': 8, 'नऊ': 9, 'दहा': 10, 'वीस': 20, 'पन्नास': 50, 'शंभर': 100},
    'kn': {'ಸೊನ್ನೆ': 0, 'ಒಂದು': 1, 'ಎರಡು': 2, 'ಮೂರು': 3, 'ನಾಲ್ಕು': 4, 'ಐದು': 5, 'ಆರು': 6, 'ಏಳು': 7, 'ಎಂಟು': 8, 'ಒಂಬತ್ತು': 9, 'ಹತ್ತು': 10, 'ಇಪ್ಪತ್ತು': 20, 'ಐವತ್ತು': 50, 'ನೂರು': 100},
    'ml': {'പൂജ്യം': 0, 'ഒന്ന്': 1, 'രണ്ട്': 2, 'മൂന്ന്': 3, 'നാല്': 4, 'അഞ്ച്': 5, 'ആറ്': 6, 'ഏഴ്': 7, 'എട്ട്': 8, 'ഒമ്പത്': 9, 'പത്ത്': 10, 'ഇരുപത്': 20, 'അമ്പത്': 50, 'നൂറ്': 100},
    'or': {'ଶୂନ୍ୟ': 0, 'ଏକ': 1, 'ଦୁଇ': 2, 'ତିନି': 3, 'ଚାରି': 4, 'ପାଞ୍ଚ': 5, 'ଛଅ': 6, 'ସାତ': 7, 'ଆଠ': 8, 'ନଅ': 9, 'ଦଶ': 10, 'କୋଡ଼ିଏ': 20, 'ପଚାଶ': 50, 'ଶହେ': 100},
}


def spoken_number(text, lang):
    """First number in the utterance, as digits or as a number word in `lang`; None if absent."""
    m = _DIGITS.search(text)
    if m:
        return int(m.group(0))
    words = _NUMWORDS.get(lang, {})
    for tok in _norm(text):
        if tok in words:
            return words[tok]
    return None
_PUNCT = re.compile(r'[\s\.,!?।॥;:\-\'"()]+')


def _norm(s):
    s = unicodedata.normalize('NFC', s).lower()
    s = _DIGITS.sub(' ', s)
    return [t for t in _PUNCT.split(s) if t]


def _grams(tokens, n=3):
    g = set()
    for t in tokens:
        t = f' {t} '
        for i in range(max(1, len(t) - n + 1)):
            g.add(t[i:i + n])
    return g


def match(text, lang, top=3, threshold=0.55):
    """Rank phrasebook entries against STT output. Returns [(idx, score, n)], best
    first, only those with score >= threshold. Score = mean of token Jaccard and
    character-trigram Jaccard, so word-order and small STT slips both degrade
    gracefully. n = first integer in the utterance if the phrase has a slot."""
    book = load()
    toks = _norm(text)
    if not toks:
        return []
    tset, tgr = set(toks), _grams(toks)
    n = spoken_number(text, lang)
    numwords = set(_NUMWORDS.get(lang, {}))
    toks = [t for t in toks if t not in numwords] or toks
    tset, tgr = set(toks), _grams(toks)
    out = []
    for idx, entry in enumerate(book['phrases']):
        ptoks = _norm(entry[lang].replace(_SLOT, ''))
        pset, pgr = set(ptoks), _grams(ptoks)
        j_tok = len(tset & pset) / len(tset | pset)
        j_gr = len(tgr & pgr) / max(1, len(tgr | pgr))
        score = 0.5 * j_tok + 0.5 * j_gr
        if score >= threshold:
            slot = n if _SLOT in entry['en'] else None
            if _SLOT in entry['en'] and (n is None or n > 255):
                continue  # phrase needs a number the utterance doesn't have
            out.append((idx, round(score, 3), slot))
    out.sort(key=lambda x: -x[1])
    return out[:top]


def demo():
    """hi speaker says a phrasebook sentence; bn receiver hears it in Bengali, 10 bytes."""
    from frame import pack as text_pack, ALERT
    said = 'पाँच लोग घायल हैं'
    cands = match(said, 'hi')
    idx, score, n = cands[0]
    wire = pack(idx, ALERT, seq=3, n=5)
    text_wire = text_pack(said, 'hi', ALERT, seq=3)
    got = unpack(wire)
    return {'said': said, 'match': (idx, score), 'bytes_phrase': len(wire), 'bytes_text': len(text_wire),
            'bn_hears': render(got['idx'], 'bn', got['n']), 'ta_hears': render(got['idx'], 'ta', got['n']),
            'fp_ok': got['fp_ok']}


if __name__ == '__main__':
    d = demo()
    for k, v in d.items():
        print(f'{k:13} {v}')
    assert d['bytes_phrase'] == 10 and d['fp_ok'] and 'বন' not in d['bn_hears']
