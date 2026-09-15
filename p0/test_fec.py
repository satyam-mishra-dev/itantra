"""Tests for fec.py — run: python test_fec.py (≈10 s: a few AFSK round trips)"""
import random

import fec
import afsk
import phrasebook as pb
from frame import pack, unpack, NORMAL, ALERT

N = 0


def ok(cond, msg):
    global N
    N += 1
    assert cond, msg


FR = pack('बाढ़ का पानी बढ़ रहा है, तुरंत निकलें', 'hi', ALERT, 42)


def test_protect_recover_sizes():
    for nsym in (fec.RS8, fec.RS16):
        cw = fec.protect(FR, nsym)
        ok(len(cw) == len(FR) + nsym, f'RS{nsym} adds {nsym} parity bytes')
        ok(cw[:len(FR)] == FR, 'systematic: frame bytes lead, parity trails')
        got = fec.recover(cw, nsym)
        ok(got == (FR, 0), 'clean codeword recovers with 0 corrections')


def test_corrects_up_to_half_nsym_byte_errors():
    rng = random.Random(1)
    for nsym in (fec.RS8, fec.RS16):
        cw = fec.protect(FR, nsym)
        t = nsym // 2
        for k in range(1, t + 1):
            bad = bytearray(cw)
            for i in rng.sample(range(len(cw)), k):
                bad[i] ^= rng.randrange(1, 256)
            got = fec.recover(bytes(bad), nsym)
            ok(got is not None and got[0] == FR and got[1] == k, f'RS{nsym} fixes {k} byte errors (got {got and got[1]})')
        bad = bytearray(cw)
        for i in rng.sample(range(len(cw)), t + 3):
            bad[i] ^= 0xFF
        got = fec.recover(bytes(bad), nsym)
        ok(got is None or got[0] == FR, 'never returns a wrong frame (frame CRC gate)')


def test_burst_errors():
    cw = bytearray(fec.protect(FR, fec.RS16))
    for i in range(12, 20):  # 8 consecutive bytes destroyed (a squelch tail)
        cw[i] = 0
    got = fec.recover(bytes(cw), fec.RS16)
    ok(got is not None and got[0] == FR and got[1] == 8, f'RS16 repairs an 8-byte burst, got {got and got[1]}')


def test_phrase_frame_tier():
    ph = pb.pack(4, ALERT, 3, n=5)
    cw = fec.protect(ph, 4)
    ok(len(cw) == 14, '10 B phrase frame + RS4 = 14 B')
    bad = bytearray(cw)
    bad[2] ^= 0xFF
    bad[9] ^= 0x0F
    got = fec.recover(bytes(bad), 4)
    ok(got is not None and got[0] == ph, 'phrase frame survives 2 byte errors with 4 parity bytes')


def test_afsk_roundtrip_clean_and_noisy():
    audio = fec.afsk_send(FR, fec.RS8)
    ok(fec.afsk_recv(audio, len(FR), fec.RS8) == FR, 'clean channel')
    ok(fec.afsk_recv(afsk.voice_channel(audio, 6, seed=3), len(FR), fec.RS8) == FR, '6 dB channel with RS8')
    ok(unpack(fec.afsk_recv(audio, len(FR), fec.RS8))['prio'] == ALERT, 'frame decodes after the trip')


def test_wrong_length_hint_fails_safely():
    audio = fec.afsk_send(FR, fec.RS8)
    ok(fec.afsk_recv(audio, len(FR) + 5, fec.RS8) is None, 'wrong frame length hint → None, never garbage')
    ok(fec.afsk_recv(audio, len(FR), fec.RS16) is None, 'wrong nsym → None, never garbage')


def test_demo():
    table = fec.demo()
    ok(table[fec.RS8][0] >= table[0][0], 'RS8 never worse than no FEC at 2 dB')


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
    print(f'fec: {N} assertions passed')
