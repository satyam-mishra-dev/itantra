"""Digital roll-call: offline evacuation headcount over 3-byte ACK frames.

A coordinator broadcasts one spoken question (a normal ALERT frame). Every
phone answers with an ACK frame carrying a 3-byte payload:
    respondent_id (2 B, big-endian) + status (1 B)
40 households = 120 payload bytes total. All existing mustering products
(Stratus-io, EmergencyOS, headcount.io) assume internet/QR kiosks; this works
over the same 45-byte bearer as everything else in iTantra.

Reuses frame.crc16 and the exact frame header layout; raw (non-VarnaCode)
payload, so ACK parsing lives here instead of touching frame.py.
"""
import struct

from frame import crc16, pack, unpack, ALERT, ACK
from varnacode import LANGS

SAFE, NEED_HELP, SOS = 0, 1, 2
STATUS_NAMES = ['SAFE', 'NEED_HELP', 'SOS']


def make_question(text, lang, seq):
    """The coordinator's spoken question — an ordinary ALERT frame."""
    return pack(text, lang, prio=ALERT, seq=seq)


def make_ack(lang, qseq, respondent_id, status):
    payload = struct.pack('>HB', respondent_id, status)
    hdr = struct.pack('>BBH', (0 << 6) | (LANGS.index(lang) << 2) | ACK,
                      qseq & 0xFF, len(payload))
    body = hdr + payload
    return body + struct.pack('>H', crc16(body))


def parse_ack(frame_bytes):
    """-> (qseq, respondent_id, status). Raises on corruption/non-ACK."""
    if len(frame_bytes) != 9:
        raise ValueError('bad ack length')
    body, crc = frame_bytes[:-2], struct.unpack('>H', frame_bytes[-2:])[0]
    if crc16(body) != crc:
        raise ValueError('CRC mismatch')
    b0, qseq, plen = struct.unpack('>BBH', body[:4])
    if (b0 & 3) != ACK or plen != 3:
        raise ValueError('not a roll-call ack')
    rid, status = struct.unpack('>HB', body[4:])
    if status > SOS:
        raise ValueError('bad status')
    return qseq, rid, status


class RollCall:
    def __init__(self, lang, seq, expected=None):
        self.lang, self.seq = lang, seq
        self.expected = expected  # optional headcount target
        self.responses = {}  # rid -> status (worst status wins on duplicates)

    def question(self, text):
        return make_question(text, self.lang, self.seq)

    def ingest(self, ack_bytes):
        qseq, rid, status = parse_ack(ack_bytes)
        if qseq != self.seq:
            return False
        self.responses[rid] = max(self.responses.get(rid, SAFE), status)
        return True

    def tally(self):
        t = {name: 0 for name in STATUS_NAMES}
        for s in self.responses.values():
            t[STATUS_NAMES[s]] += 1
        t['responded'] = len(self.responses)
        if self.expected is not None:
            t['silent'] = max(self.expected - len(self.responses), 0)
        return t


def demo():
    rc = RollCall('or', seq=7, expected=8)
    q = rc.question('सभी सुरक्षित हैं? जवाब दें')  # hi text on 'or' channel is fine for the demo
    # question is a normal frame — receivers decode it as usual
    lang, prio, seq, text = unpack(q)[:4] if isinstance(unpack(q), tuple) else (None,) * 4
    acks = [make_ack('or', 7, rid, st) for rid, st in
            [(101, SAFE), (102, SAFE), (103, NEED_HELP), (104, SOS), (105, SAFE)]]
    acks.append(make_ack('or', 7, 103, SAFE))       # duplicate: worst status must win
    for a in acks:
        assert rc.ingest(a)
    assert not rc.ingest(make_ack('or', 9, 200, SAFE))  # wrong question seq ignored
    corrupted = bytearray(acks[0]); corrupted[5] ^= 0xFF
    try:
        rc.ingest(bytes(corrupted)); assert False
    except ValueError:
        pass
    t = rc.tally()
    assert t == {'SAFE': 3, 'NEED_HELP': 1, 'SOS': 1, 'responded': 5, 'silent': 3}, t
    assert len(acks[0]) == 9  # 9 bytes on the wire per answer
    print(f'rollcall ok: {t} (9 B per answer)')


if __name__ == '__main__':
    demo()
