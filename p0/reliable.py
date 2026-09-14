"""Reliable delivery on top of iTantra frames: delivery ACK/NACK, retransmit, dedup.

Adds nothing to frame.py. Uses the existing ACK priority class (frame.ACK) with a
1-byte payload so it can never be mistaken for a roll-call ACK (3-byte payload,
rollcall.parse_ack rejects plen != 3):

    delivery ACK  : prio=ACK, seq=<acked seq>, payload = b'\\x00'   (7 bytes on the wire)
    delivery NACK : prio=ACK, seq=<missing seq>, payload = b'\\x01' (7 bytes)

Policy (matches what the strongest rivals ship, tuned for our 45-byte frames):
    retransmit after RTO (default 800 ms); NORMAL gets 3 tries, ALERT gets 5;
    ALERT frames jump the send queue; receiver dedups by seq within a window and
    NACKs gaps it observes (sender resends the missing seq at once).

Transport-agnostic and clock-injected: the caller feeds bytes in, gets bytes out,
and calls tick(now). Stdlib only.
"""
import struct
from collections import OrderedDict

from frame import crc16, unpack, NORMAL, ALERT, ACK
from varnacode import LANGS

ACK_BYTE, NACK_BYTE = 0, 1
RTO = 0.8
TRIES = {NORMAL: 3, ALERT: 5}   # None = never give up (store-and-forward), backoff x2 capped at 8x RTO
BACKOFF_CAP = 3                  # 2**3 = 8x
DEDUP_WINDOW = 64  # seqs remembered per link


def make_ctrl(seq, kind, lang='hi'):
    payload = bytes([kind])
    hdr = struct.pack('>BBH', (LANGS.index(lang) << 2) | ACK, seq & 0xFF, 1)
    body = hdr + payload
    return body + struct.pack('>H', crc16(body))


def parse_ctrl(frame_bytes):
    """-> (seq, kind) for a delivery ACK/NACK, else None (not raising: other ACK-class
    frames such as roll-call answers are legitimate on the same link)."""
    if len(frame_bytes) != 7:
        return None
    body, crc = frame_bytes[:-2], struct.unpack('>H', frame_bytes[-2:])[0]
    if crc16(body) != crc:
        return None
    b0, seq, plen = struct.unpack('>BBH', body[:4])
    if (b0 & 3) != ACK or plen != 1 or body[4] > NACK_BYTE:
        return None
    return seq, body[4]


def _seq_gap(a, b):
    """Number of seqs strictly between a and b going forward mod 256."""
    return (b - a - 1) % 256


class ReliableSender:
    """Queue outgoing frames; hand back what to put on the wire now.

    send(frame_bytes, prio) -> None            (enqueue; ALERT goes to the front)
    on_ctrl(frame_bytes) -> bool               (feed every received frame; True if consumed)
    tick(now) -> [bytes]                       (frames to transmit right now)
    status(seq) -> 'queued' | 'sent' | 'acked' | 'failed'
    """

    def __init__(self, rto=RTO, tries=None, now=0.0):
        self.rto = rto
        self.tries = dict(TRIES if tries is None else tries)
        self.queue = []            # [(seq, frame, prio)] not yet transmitted
        self.inflight = {}         # seq -> {'frame','prio','sent','left','tries'}
        self.state = {}            # seq -> status string
        self.now = now
        self._seq = 0
        self.retransmits = 0

    def next_seq(self):
        """Next wire seq, skipping any still in flight so the 1-byte wrap never clobbers a queued frame."""
        busy = set(self.inflight) | {q[0] for q in self.queue}
        for _ in range(256):
            s = self._seq & 0xFF
            self._seq += 1
            if s not in busy:
                return s
        return self._seq & 0xFF  # 256 unacked: the peer has been gone half a conversation; oldest loses

    @staticmethod
    def seq_of(frame_bytes):
        return frame_bytes[1]

    def send(self, frame_bytes, prio=NORMAL):
        seq = self.seq_of(frame_bytes)
        item = (seq, frame_bytes, prio)
        if prio == ALERT:
            self.queue.insert(0, item)
        else:
            self.queue.append(item)
        self.state[seq] = 'queued'

    def on_ctrl(self, frame_bytes):
        c = parse_ctrl(frame_bytes)
        if c is None:
            return False
        seq, kind = c
        if seq not in self.inflight:
            return True  # stale/duplicate control frame, still ours
        if kind == ACK_BYTE:
            del self.inflight[seq]
            self.state[seq] = 'acked'
        else:  # NACK: resend immediately, does not consume a try
            self.inflight[seq]['nack'] = True
        return True

    def tick(self, now):
        self.now = now
        out = []
        # 1. retransmits / expiries, oldest first
        for seq in sorted(self.inflight, key=lambda s: self.inflight[s]['sent']):
            f = self.inflight[seq]
            if f.pop('nack', False) or f.pop('flush', False):
                f['sent'] = now
                out.append(f['frame'])
                continue
            wait = self.rto * (1 << min(f['tries'] - 1, BACKOFF_CAP)) if f['left'] is None else self.rto
            if now - f['sent'] < wait:
                continue
            if f['left'] is not None:
                if f['left'] <= 0:
                    del self.inflight[seq]
                    self.state[seq] = 'failed'
                    continue
                f['left'] -= 1
            f['tries'] += 1
            f['sent'] = now
            self.retransmits += 1
            out.append(f['frame'])
        # 2. fresh sends
        while self.queue:
            seq, frame_bytes, prio = self.queue.pop(0)
            budget = self.tries.get(prio, TRIES[NORMAL])
            self.inflight[seq] = {'frame': frame_bytes, 'prio': prio, 'sent': now, 'tries': 1,
                                  'left': None if budget is None else budget - 1}
            self.state[seq] = 'sent'
            out.append(frame_bytes)
        return out

    def flush(self):
        """Peer (re)connected: resend everything in flight on the next tick, no backoff wait."""
        for f in self.inflight.values():
            f['flush'] = True

    def status(self, seq):
        return self.state.get(seq)


class ReliableReceiver:
    """ingest(frame_bytes, key=None) -> (decoded | None, [ctrl frames to send back])

    decoded is frame.unpack(...) for a new data frame, None for a duplicate or a
    control frame. Duplicates are still ACKed (the first ACK may have been lost).
    """

    def __init__(self, lang='hi', window=DEDUP_WINDOW):
        self.lang = lang
        self.window = window
        self.seen = OrderedDict()  # seq -> True, insertion ordered
        self.last = None           # last in-order seq observed

    def _remember(self, seq):
        self.seen[seq] = True
        while len(self.seen) > self.window:
            self.seen.popitem(last=False)

    def ingest(self, frame_bytes, key=None):
        if parse_ctrl(frame_bytes) is not None:
            return None, []
        msg = unpack(frame_bytes, key=key)
        seq = msg['seq']
        if msg['prio'] == ACK:
            return msg, []  # roll-call or other ACK-class payload: not ours to ack
        ctrl = [make_ctrl(seq, ACK_BYTE, self.lang)]
        if seq in self.seen:
            return None, ctrl
        if self.last is not None:
            gap = _seq_gap(self.last, seq)
            if 0 < gap <= 8:  # a small forward gap = something was lost; ask for it
                for k in range(1, gap + 1):
                    missing = (self.last + k) % 256
                    if missing not in self.seen:
                        ctrl.append(make_ctrl(missing, NACK_BYTE, self.lang))
        self._remember(seq)
        self.last = seq
        return msg, ctrl


def demo():
    """Lossy link, one ALERT and two NORMAL sentences: everything arrives exactly once."""
    from frame import pack
    tx, rx = ReliableSender(now=0.0), ReliableReceiver('hi')
    frames = [pack('पानी बढ़ रहा है', 'hi', ALERT, seq=1),
              pack('गाँव खाली करो', 'hi', NORMAL, seq=2),
              pack('नाव भेजो', 'hi', NORMAL, seq=3)]
    for f in frames:
        tx.send(f, prio=unpack(f)['prio'])
    drop_first = {1: True, 2: True}   # first transmission of seq 1 and 2 is lost
    delivered, t = [], 0.0
    for _ in range(12):
        for f in tx.tick(t):
            seq = f[1]
            if drop_first.pop(seq, False):
                continue
            msg, ctrls = rx.ingest(f)
            if msg:
                delivered.append((msg['seq'], msg['text']))
            for c in ctrls:
                tx.on_ctrl(c)
        t += 0.5
    return delivered, {s: tx.status(s) for s in (1, 2, 3)}


if __name__ == '__main__':
    d, st = demo()
    print(d)
    print(st)
    assert sorted(s for s, _ in d) == [1, 2, 3] and all(v == 'acked' for v in st.values())
