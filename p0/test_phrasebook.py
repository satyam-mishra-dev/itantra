"""Tests for phrasebook.py — run: python test_phrasebook.py"""
import phrasebook as pb
import frame
import rollcall
import reliable
from varnacode import LANGS

N = 0


def ok(cond, msg):
    global N
    N += 1
    assert cond, msg


def test_book_shape():
    b = pb.load()
    ok(len(b['phrases']) == 32, '32 phrases')
    ok(all(set(p) == set(LANGS) for p in b['phrases']), 'every phrase in all 10 languages')
    ok(all(('{n}' in p['en']) == all('{n}' in p[l] for l in LANGS) for p in b['phrases']),
       'slot present in every language or none')
    ok(0 < pb.fingerprint() <= 0xFFFF, 'fingerprint is a crc16')


def test_pack_unpack_sizes():
    f = pb.pack(2, frame.NORMAL, seq=7)
    ok(len(f) == 9, f'no-slot frame is 9 bytes, got {len(f)}')
    u = pb.unpack(f)
    ok(u == {'idx': 2, 'n': None, 'prio': frame.NORMAL, 'seq': 7, 'fp_ok': True}, f'roundtrip, got {u}')
    f = pb.pack(4, frame.ALERT, seq=200, n=12)
    ok(len(f) == 10, 'slot frame is 10 bytes')
    u = pb.unpack(f)
    ok(u['idx'] == 4 and u['n'] == 12 and u['prio'] == frame.ALERT and u['seq'] == 200, 'slot roundtrip')
    ok(pb.render(4, 'hi', 12) == '12 लोग घायल हैं।', 'render hi with slot')
    ok(pb.render(4, 'ta', 12) == '12 பேர் காயமடைந்தனர்।', 'render ta with slot')
    ok(pb.render(2, 'bn') == 'একটি নৌকা পাঠান।', 'render bn no slot')


def test_validation():
    for bad in [lambda: pb.pack(4), lambda: pb.pack(4, n=300), lambda: pb.pack(999), lambda: pb.pack(-1)]:
        try:
            bad()
            ok(False, 'must raise')
        except ValueError:
            ok(True, 'raises')
    f = bytearray(pb.pack(2))
    f[5] ^= 0x01
    try:
        pb.unpack(bytes(f))
        ok(False, 'crc must catch a flipped bit')
    except ValueError:
        ok(True, 'crc catches')
    # fingerprint mismatch is reported, not raised: the receiver can still say "unknown phrase"
    f = bytearray(pb.pack(2))
    f[4] ^= 0xFF
    body = bytes(f[:-2])
    f[-2:] = frame.crc16(body).to_bytes(2, 'big')
    ok(pb.unpack(bytes(f))['fp_ok'] is False, 'fp mismatch flagged')


def test_no_collision_with_other_frame_kinds():
    text = frame.pack('नाव भेजो', 'hi', frame.NORMAL, 3)
    ok(not pb.is_phrase_frame(text), 'text frame is not a phrase frame')
    ok(not pb.is_phrase_frame(rollcall.make_ack('hi', 1, 5, 0)), 'roll-call ack is not a phrase frame')
    ok(not pb.is_phrase_frame(reliable.make_ctrl(1, 0)), 'delivery ctrl is not a phrase frame')
    ok(reliable.parse_ctrl(pb.pack(2)) is None, 'phrase frame is not a delivery ctrl')
    try:
        frame.unpack(pb.pack(2))
        ok(False, 'frame.unpack must not silently decode a phrase frame')
    except (ValueError, IndexError):
        ok(True, 'frame.unpack rejects lang=15 (receiver must check is_phrase_frame first)')


def test_match_exact_paraphrase_offtopic():
    ok(pb.match('नाव भेजो', 'hi')[0][0] == 2, 'exact hi')
    ok(pb.match('Send a boat.', 'en')[0][0] == 2, 'exact en')
    m = pb.match('भेजो नाव जल्दी', 'hi')
    ok(m and m[0][0] == 2 and m[0][1] < 1.0, f'word order + extra word still matches, got {m}')
    ok(pb.match('the weather is nice today', 'en') == [], 'off-topic matches nothing')
    ok(pb.match('', 'en') == [], 'empty matches nothing')
    m = pb.match('जल बढ़ रहा है', 'hi')
    ok(m and m[0][0] == 6, f'synonym-ish still finds water rising, got {m}')


def test_match_numbers_words_and_digits():
    ok(pb.match('5 लोग घायल हैं', 'hi')[0] == (4, 1.0, 5), 'digits hi')
    ok(pb.match('पाँच लोग घायल हैं', 'hi')[0] == (4, 1.0, 5), 'number word hi')
    ok(pb.match('two people are trapped', 'en')[0][0] == 5 and pb.match('two people are trapped', 'en')[0][2] == 2, 'number word en')
    ok(pb.match('பத்து பேர் சிக்கியுள்ளனர்', 'ta')[0] == (5, 1.0, 10), 'number word ta')
    ok(pb.match('people injured', 'en') == [] or all(i != 4 for i, _, _ in pb.match('people injured', 'en')),
       'slot phrase without a number is not offered')
    ok(pb.spoken_number('300 people', 'en') == 300, 'digits > 255 still parsed (pack will reject)')


def test_every_language_exact_self_match():
    b = pb.load()
    misses = []
    for idx, p in enumerate(b['phrases']):
        for l in LANGS:
            said = p[l].replace('{n}', '3')
            m = pb.match(said, l)
            if not m or m[0][0] != idx:
                misses.append((idx, l, m[:1]))
    ok(not misses, f'each phrase matches itself in its own language, misses: {misses[:5]}')


def test_bytes_vs_text_all_languages():
    b = pb.load()
    worse = []
    for l in LANGS:
        for idx, p in enumerate(b['phrases']):
            said = p[l].replace('{n}', '7')
            t = len(frame.pack(said, l, frame.NORMAL, 1))
            q = len(pb.pack(idx, frame.NORMAL, 1, n=7 if '{n}' in p['en'] else None))
            if q >= t:
                worse.append((l, idx, q, t))
    ok(not worse, f'phrase frame always smaller than text frame, exceptions: {worse}')


def test_demo():
    d = pb.demo()
    ok(d['bytes_phrase'] == 10 and d['fp_ok'], 'demo 10 bytes, book matches')
    ok(d['bn_hears'].startswith('5 ') and d['ta_hears'].startswith('5 '), 'receiver renders in its own language')


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
    print(f'phrasebook: {N} assertions passed')
