"""Forward error correction for the analog-radio (AFSK) path.

Today afsk.demodulate() throws away any frame with a single flipped bit — the CRC
gate runs before anything can be repaired. On a real radio at 0–6 dB SNR that is
most frames. Reed–Solomon fixes up to nsym/2 wrong BYTES anywhere in the frame,
which suits AFSK's failure mode (bursts from squelch tails and fades), and costs
nsym bytes: a 45 B sentence becomes 53 B (RS8) or 61 B (RS16).

    protect(frame, nsym)  -> codeword          frame + nsym parity bytes
    recover(codeword, nsym) -> (frame, fixed) | None   fixed = bytes corrected
    afsk_send(frame, nsym) -> audio            modulate(protect(frame))
    afsk_recv(audio, nsym) -> frame | None     raw demod → RS repair → frame CRC

LoRa (SX127x) has its own PHY FEC (CR 4/5–4/8) and drops whole packets rather
than flipping bits, so app-layer RS is NOT applied there — repetition is the
right knob for LoRa (research/thesis-channel-adaptive.md). BLE/Wi-Fi are
lossless: no FEC.

RS implementation: `reedsolo` (public domain / MIT, pure Python). Firmware uses
libcorrect (BSD); Kotlin port pending. The modem's own CRC still guards false
preamble locks; the *frame* CRC is the final truth after repair.
"""
import numpy as np
from reedsolo import RSCodec, ReedSolomonError

import afsk
from frame import crc16

RS8, RS16 = 8, 16
_codecs = {}


def _rs(nsym):
    if nsym not in _codecs:
        _codecs[nsym] = RSCodec(nsym)
    return _codecs[nsym]


def protect(frame, nsym=RS8):
    return bytes(_rs(nsym).encode(bytes(frame)))


def recover(codeword, nsym=RS8):
    """-> (frame_bytes, n_corrected) or None when beyond nsym/2 byte errors."""
    try:
        msg, _full, errata = _rs(nsym).decode(bytes(codeword))
    except ReedSolomonError:
        return None
    frame = bytes(msg)
    if len(frame) < 6 or crc16(frame[:-2]) != int.from_bytes(frame[-2:], 'big'):
        return None  # RS "succeeded" onto a wrong codeword (possible past nsym/2 errors)
    return frame, len(errata)


def afsk_send(frame, nsym=RS8, amp=0.7):
    return afsk.modulate(protect(frame, nsym), amp=amp)


def _demodulate_raw(x, expect_len):
    """Like afsk.demodulate but returns candidate payloads even when the modem CRC
    fails, so RS gets a chance. Yields (payload, modem_crc_ok) per plausible lock."""
    x = np.asarray(x, dtype=np.float64)
    x = x / (np.abs(x).max() + 1e-9)
    header_bits = (len(afsk.PREAMBLE) + 3) * 8
    step = max(int(afsk.SPB / 4), 1)
    for start in range(0, min(len(x) - int(header_bits * afsk.SPB), int(afsk.SR * 0.5)), step):
        bits = afsk._demod_bits(x, start, header_bits)
        if len(bits) < header_bits:
            return
        raw = afsk._debyte(bits)
        # tolerate a damaged preamble: 6 of 8 preamble bytes + sync is enough to try
        if sum(b == 0x55 for b in raw[:8]) >= 6 and raw[8] == afsk.SYNC:
            plen = int.from_bytes(raw[9:11], 'big')
            if plen != expect_len:  # the length field itself may be corrupted; trust the caller
                plen = expect_len
            total = header_bits + (plen + 2) * 8
            allbits = afsk._demod_bits(x, start, total)
            if len(allbits) < total:
                continue
            raw2 = afsk._debyte(allbits)
            payload = raw2[11:11 + plen]
            ok = int.from_bytes(raw2[11 + plen:13 + plen], 'big') == crc16(payload)
            yield payload, ok


def afsk_recv(x, frame_len, nsym=RS8):
    """frame_len = length of the un-coded frame (known to the receiver from the
    ARQ/tier negotiation, or tried over the few sizes in use). -> frame | None."""
    for payload, _ok in _demodulate_raw(x, frame_len + nsym):
        got = recover(payload, nsym)
        if got is not None:
            return got[0]
    return None


def sweep(frame, snrs=(0, 2, 4, 6, 8, 10), trials=40, nsyms=(0, RS8, RS16)):
    """Frame-success rate vs SNR through afsk.voice_channel, per FEC setting."""
    table = {}
    for nsym in nsyms:
        row = []
        for snr in snrs:
            hits = 0
            for seed in range(trials):
                if nsym == 0:
                    audio = afsk.modulate(frame)
                    got = afsk.demodulate(afsk.voice_channel(audio, snr, seed=seed))
                else:
                    audio = afsk_send(frame, nsym)
                    got = afsk_recv(afsk.voice_channel(audio, snr, seed=seed), len(frame), nsym)
                hits += got == frame
            row.append(hits / trials)
        table[nsym] = row
    return snrs, table


def demo():
    from frame import pack
    fr = pack('बाढ़ का पानी बढ़ रहा है, तुरंत निकलें', 'hi', prio=1, seq=42)
    cw = protect(fr, RS8)
    assert len(cw) == len(fr) + 8
    bad = bytearray(cw)
    for i in (3, 10, 20, len(cw) - 2):
        bad[i] ^= 0xFF
    got = recover(bytes(bad), RS8)
    assert got is not None and got[0] == fr and got[1] == 4, got
    snrs, table = sweep(fr, snrs=(2, 4, 6), trials=8)
    print(f'{len(fr)} B frame; success rate at SNR {snrs} dB:')
    for nsym, row in table.items():
        print(f'  {"no FEC" if nsym == 0 else f"RS{nsym}":7} {row}  ({afsk.seconds(len(fr) + nsym):.2f} s audio)')
    return table


if __name__ == '__main__':
    demo()
