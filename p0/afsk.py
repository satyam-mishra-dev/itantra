"""Voice-channel modem: iTantra frames as audio tones through ANY analog radio.

Bell-202-style AFSK (mark 1200 Hz / space 2200 Hz, 1200 baud, continuous
phase) inside the 300-3400 Hz voice band. A 73-byte encrypted sentence frame
crosses in ~0.6 s of audio — hold the phone to a Rs.500 analog walkie-talkie,
a ham HF set, or a landline call, and it becomes an iTantra bearer.
(ggwave/Gibberlink validate data-over-sound in production; this is the
minimal stdlib+numpy version tuned for our tiny frames.)

Wire format: preamble 0x55*8 | sync 0x7E | len(2B BE) | payload bytes,
bits LSB-first.

ponytail: no AGC/clock recovery — fine for the acoustic-coupling demo path;
upgrade to ggwave's Reed-Solomon protocol if real radio squelch/fading bites.
"""
import numpy as np

from frame import crc16

SR = 16000
BAUD = 1200
MARK, SPACE = 1200.0, 2200.0
SPB = SR / BAUD  # samples per bit (13.33)
PREAMBLE = bytes([0x55] * 8)
SYNC = 0x7E


def _bits(data):
    for byte in data:
        for i in range(8):
            yield (byte >> i) & 1


def modulate(payload, amp=0.7):
    data = (PREAMBLE + bytes([SYNC]) + len(payload).to_bytes(2, 'big')
            + payload + crc16(payload).to_bytes(2, 'big'))
    bits = list(_bits(data))
    n = int(round(len(bits) * SPB))
    freqs = np.empty(n)
    for i in range(n):
        freqs[i] = MARK if bits[min(int(i / SPB), len(bits) - 1)] else SPACE
    phase = 2 * np.pi * np.cumsum(freqs) / SR
    sig = amp * np.sin(phase)
    pad = np.zeros(int(0.05 * SR))
    return np.concatenate([pad, sig, pad]).astype(np.float32)


def _goertzel(x, freq):
    k = 2 * np.pi * freq / SR
    c = np.cos(k * np.arange(len(x)))
    s = np.sin(k * np.arange(len(x)))
    return (x @ c) ** 2 + (x @ s) ** 2


def _demod_bits(x, start, nbits):
    out = []
    for i in range(nbits):
        a, b = int(start + i * SPB), int(start + (i + 1) * SPB)
        if b > len(x):
            break
        w = x[a:b]
        out.append(1 if _goertzel(w, MARK) > _goertzel(w, SPACE) else 0)
    return out


def _debyte(bits):
    out = bytearray()
    for i in range(0, len(bits) - 7, 8):
        out.append(sum(bit << j for j, bit in enumerate(bits[i:i + 8])))
    return bytes(out)


def demodulate(x):
    """-> payload bytes or None. Scans coarse offsets, locks on preamble+sync."""
    x = np.asarray(x, dtype=np.float64)
    x = x / (np.abs(x).max() + 1e-9)
    header_bits = (len(PREAMBLE) + 3) * 8
    step = max(int(SPB / 4), 1)
    for start in range(0, min(len(x) - int(header_bits * SPB), int(SR * 0.5)), step):
        bits = _demod_bits(x, start, header_bits)
        if len(bits) < header_bits:
            return None
        raw = _debyte(bits)
        if raw[:8] == PREAMBLE and raw[8] == SYNC:
            plen = int.from_bytes(raw[9:11], 'big')
            if plen > 4096:
                continue
            total = header_bits + (plen + 2) * 8
            allbits = _demod_bits(x, start, total)
            if len(allbits) < total:
                continue  # misaligned hit misread the length; keep scanning
            raw2 = _debyte(allbits)
            payload = raw2[11:11 + plen]
            if int.from_bytes(raw2[11 + plen:13 + plen], 'big') != crc16(payload):
                continue  # false lock; keep scanning
            return payload
    return None


def voice_channel(sig, snr_db=10.0, seed=0):
    """Test channel: 300-3400 Hz bandpass + white noise at snr_db."""
    spec = np.fft.rfft(sig)
    f = np.fft.rfftfreq(len(sig), 1 / SR)
    spec[(f < 300) | (f > 3400)] = 0
    y = np.fft.irfft(spec, len(sig))
    p_sig = (y ** 2).mean()
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, np.sqrt(p_sig / (10 ** (snr_db / 10))), len(y))
    return y + noise


def seconds(payload_len):
    return ((len(PREAMBLE) + 3 + payload_len + 2) * 8) / BAUD


def demo():
    from frame import pack, unpack
    fr = pack('बाढ़ का पानी बढ़ रहा है, तुरंत निकलें', 'hi', prio=1, seq=42)
    audio = modulate(fr)
    assert demodulate(audio) == fr                          # clean channel
    assert demodulate(voice_channel(audio, 10)) == fr       # noisy voice band
    got = demodulate(voice_channel(audio, 6, seed=3))       # rough channel
    dur = seconds(len(fr))
    _, prio, _, text = unpack(fr)[:4] if isinstance(unpack(fr), tuple) else (None, 1, None, '')
    print(f'afsk ok: {len(fr)}-byte frame -> {dur:.2f}s of audio; '
          f'clean+10dB pass, 6dB {"pass" if got == fr else "fail (expected rough)"}')
    assert dur < 1.5


if __name__ == '__main__':
    demo()
