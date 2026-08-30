"""Prosody-over-text: the urgency of a voice, in 1 byte.

STCTS (arXiv 2512.00451) spends 312-592 bps transmitting continuous prosody
contours alongside text. A disaster channel needs the *urgency*, not the
contour: we extract 3 coarse paralinguistic classes from the PTT recording
and pack them into ONE byte per sentence, which the receiver maps onto TTS
speed / playback gain / repetition.

Byte layout: bits 0-1 urgency (CALM/ELEVATED/URGENT/PANIC)
             bits 2-3 pitch class (low/mid/high/very-high)
             bits 4-5 rate class  (slow/normal/fast/very-fast)
             bits 6-7 reserved (0)

Stdlib + numpy only. No model inference — sub-millisecond on a phone.
"""
import numpy as np

CALM, ELEVATED, URGENT, PANIC = 0, 1, 2, 3
URGENCY_NAMES = ['CALM', 'ELEVATED', 'URGENT', 'PANIC']

SR = 16000
FRAME = 512  # 32 ms
# ponytail: absolute thresholds calibrated on desktop synth voices; real mics/
# speakers vary — expose as module constants, tune per-device in Evaluation Mode.
RMS_DB_ELEV, RMS_DB_URGENT = -30.0, -22.0
F0_MID, F0_HIGH, F0_VHIGH = 140.0, 190.0, 240.0
RATE_NORM, RATE_FAST, RATE_VFAST = 2.0, 3.5, 5.0  # energy onsets / second


def _frames(x):
    n = len(x) // FRAME
    return x[:n * FRAME].reshape(n, FRAME)


def _f0_autocorr(frame):
    """Median-friendly single-frame F0 via autocorrelation, 60-350 Hz band."""
    f = frame - frame.mean()
    ac = np.correlate(f, f, 'full')[len(f) - 1:]
    lo, hi = SR // 350, SR // 60
    if hi >= len(ac):
        return 0.0
    seg = ac[lo:hi]
    peak = np.argmax(seg)
    if ac[0] <= 0 or seg[peak] < 0.3 * ac[0]:
        return 0.0  # unvoiced
    return SR / (lo + peak)


def features(x):
    """x: mono float32/-1..1 (or int16) at 16 kHz -> (rms_db, f0_med, onset_rate)."""
    x = np.asarray(x, dtype=np.float64)
    if x.size and np.abs(x).max() > 1.5:  # int16 input
        x = x / 32768.0
    if x.size < FRAME * 4:
        return -60.0, 0.0, 0.0
    fr = _frames(x)
    rms = np.sqrt((fr ** 2).mean(axis=1))
    voiced = rms > max(rms.max() * 0.15, 1e-4)
    rms_db = 20 * np.log10(rms[voiced].mean() + 1e-9) if voiced.any() else -60.0
    f0s = [_f0_autocorr(f) for f, v in zip(fr, voiced) if v]
    f0s = [f for f in f0s if f > 0]
    f0_med = float(np.median(f0s)) if f0s else 0.0
    # onset rate: rising edges of the voiced-energy envelope
    onsets = int(((~voiced[:-1]) & voiced[1:]).sum())
    dur = len(x) / SR
    return float(rms_db), f0_med, onsets / dur if dur > 0 else 0.0


def classify(rms_db, f0, rate):
    pitch_c = 0 if f0 < F0_MID else 1 if f0 < F0_HIGH else 2 if f0 < F0_VHIGH else 3
    rate_c = 0 if rate < RATE_NORM else 1 if rate < RATE_FAST else 2 if rate < RATE_VFAST else 3
    loud = 0 if rms_db < RMS_DB_ELEV else 1 if rms_db < RMS_DB_URGENT else 2
    score = loud + (1 if pitch_c >= 2 else 0) + (1 if rate_c >= 2 else 0)
    urgency = min(score, PANIC)
    return urgency, pitch_c, rate_c


def encode(x):
    """wav samples -> prosody byte."""
    u, p, r = classify(*features(x))
    return u | (p << 2) | (r << 4)


def decode(b):
    return b & 3, (b >> 2) & 3, (b >> 4) & 3


def tts_params(prosody_byte):
    """Receiver side: map the byte onto knobs sherpa-onnx/Android already have."""
    u, _, _ = decode(prosody_byte)
    return {
        CALM:     dict(speed=0.95, gain=1.0, repeats=1),
        ELEVATED: dict(speed=1.05, gain=1.2, repeats=1),
        URGENT:   dict(speed=1.12, gain=1.6, repeats=1),
        PANIC:    dict(speed=1.18, gain=2.0, repeats=2),
    }[u] | dict(urgency=URGENCY_NAMES[u])


def _synth(dur, f0, amp, burst_hz):
    """Test helper: bursty harmonic tone imitating speech energy patterns."""
    t = np.arange(int(dur * SR)) / SR
    voice = sum(np.sin(2 * np.pi * f0 * k * t) / k for k in (1, 2, 3))
    gate = (np.sin(2 * np.pi * burst_hz * t) > -0.2).astype(float)
    return (amp * voice * gate / 3).astype(np.float32)


def demo():
    calm = _synth(2.0, 110, 0.05, 1.2)
    panic = _synth(2.0, 260, 0.6, 4.5)
    bc, bp = encode(calm), encode(panic)
    uc, up = decode(bc)[0], decode(bp)[0]
    assert uc <= ELEVATED < up, (URGENCY_NAMES[uc], URGENCY_NAMES[up])
    assert up >= URGENT
    for b in (bc, bp):  # byte round-trip
        u, p, r = decode(b)
        assert b == (u | (p << 2) | (r << 4))
    pp = tts_params(bp)
    assert pp['speed'] > tts_params(bc)['speed'] and pp['gain'] > 1.0
    print(f'prosody ok: calm->{URGENCY_NAMES[uc]} panic->{URGENCY_NAMES[up]} '
          f'params={pp}')


if __name__ == '__main__':
    demo()
