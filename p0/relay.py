"""Flood relay: multi-hop delivery over any mix of bearers, as a decorator around them.

Two phones that can't hear each other still talk if a third phone hears both. Every
node rebroadcasts every new frame once, on every bearer it has, until the TTL runs
out — the mesh that Meshtastic uses (managed flood + hop limit + dedup), sized for
frames that are 9–45 bytes, where the overhead of a flood is nothing.

Envelope (frame.py untouched; lang=14 marks it, like lang=15 marks a phrase frame):
    byte 0    : ver=0 | lang=14 | prio   (prio copied from the inner frame so a relay
                                          can prioritise ALERT without decoding it)
    byte 1    : inner seq (cheap peek)
    bytes 2-3 : payload length
    payload   : origin (2 B) · ttl:4|hops:4 (1 B) · inner frame bytes (with its own CRC)
    last 2    : CRC-16
9 B on top of the inner frame; a 45 B sentence becomes 54 B on the wire.

Dedup key = (origin, inner seq, inner CRC) — restart-safe (see reliable.py).
Rebroadcast waits a random jitter so two relays that heard the same frame don't
collide; ALERT rebroadcasts with no jitter. Delivery ACKs from the far end ride the
same flood back, so reliable.py works end-to-end across hops unchanged.

Bearer-agnostic and clock-injected: on_receive() returns what to deliver to the app,
tick(now) returns what to put on which bearer. Stdlib only.
"""
import random
import struct
from collections import OrderedDict

from frame import crc16, ALERT

RELAY_LANG = 14
DEFAULT_TTL = 3
SEEN = 256
JITTER_MS = (20, 120)


def is_envelope(b):
    return len(b) >= 9 and ((b[0] >> 2) & 0xF) == RELAY_LANG


def wrap(inner, origin, ttl=DEFAULT_TTL, hops=0):
    if not 0 <= ttl <= 15 or not 0 <= hops <= 15 or not 0 <= origin <= 0xFFFF:
        raise ValueError('bad envelope fields')
    payload = struct.pack('>HB', origin, (ttl << 4) | hops) + bytes(inner)
    hdr = struct.pack('>BBH', (RELAY_LANG << 2) | (inner[0] & 3), inner[1], len(payload))
    body = hdr + payload
    return body + struct.pack('>H', crc16(body))


def unwrap(b):
    """-> (inner, origin, ttl, hops); raises on corruption."""
    if not is_envelope(b):
        raise ValueError('not an envelope')
    body, crc = b[:-2], struct.unpack('>H', b[-2:])[0]
    if crc16(body) != crc:
        raise ValueError('CRC mismatch')
    plen = struct.unpack('>H', body[2:4])[0]
    payload = body[4:]
    if len(payload) != plen or plen < 3 + 6:
        raise ValueError('length mismatch')
    origin, th = struct.unpack('>HB', payload[:3])
    inner = payload[3:]
    if crc16(inner[:-2]) != struct.unpack('>H', inner[-2:])[0]:
        raise ValueError('inner CRC mismatch')
    return bytes(inner), origin, th >> 4, th & 0xF


def _key(inner, origin):
    return (origin, inner[1], struct.unpack('>H', inner[-2:])[0])


class Relay:
    """Wraps a set of bearers. bearers: list of names (the app maps them to transports).

    send(inner) -> [(bearer, bytes)]                      local frame, enveloped, to every bearer
    on_receive(bytes, bearer, now) -> inner | None        what to hand to the app (None = dup/none)
    tick(now) -> [(bearer, bytes)]                        delayed rebroadcasts due now
    """

    def __init__(self, my_id, bearers, ttl=DEFAULT_TTL, rng=None, jitter_ms=JITTER_MS):
        self.my_id, self.bearers, self.ttl = my_id, list(bearers), ttl
        self.rng = rng or random.Random(my_id)
        self.jitter = jitter_ms
        self.seen = OrderedDict()
        self.pending = []          # [(due, bearer, bytes)]
        self.relayed = 0
        self.dropped = 0

    def _remember(self, key):
        self.seen[key] = True
        while len(self.seen) > SEEN:
            self.seen.popitem(last=False)

    def send(self, inner):
        env = wrap(inner, self.my_id, self.ttl, 0)
        self._remember(_key(inner, self.my_id))
        return [(b, env) for b in self.bearers]

    def on_receive(self, b, bearer, now):
        if not is_envelope(b):
            return bytes(b)            # legacy peer without relay: deliver as-is, do not relay
        inner, origin, ttl, hops = unwrap(b)
        key = _key(inner, origin)
        if key in self.seen:
            self.dropped += 1
            return None
        self._remember(key)
        if ttl > 0:
            env = wrap(inner, origin, ttl - 1, hops + 1)
            delay = 0.0 if (inner[0] & 3) == ALERT else self.rng.uniform(*self.jitter) / 1000.0
            for out in self.bearers:   # every bearer, including the one it came from: BT is point-to-point
                self.pending.append((now + delay, out, env))
            self.relayed += 1
        return inner

    def tick(self, now):
        due = [p for p in self.pending if p[0] <= now]
        self.pending = [p for p in self.pending if p[0] > now]
        return [(b, env) for _, b, env in due]


def demo():
    """A—B—C chain over Bluetooth: A cannot hear C. A's sentence reaches C through B, once."""
    from frame import pack, unpack
    nodes = {n: Relay(i, ['bt'], rng=random.Random(i)) for i, n in enumerate('ABC', start=1)}
    links = {'A': ['B'], 'B': ['A', 'C'], 'C': ['B']}   # who hears whom
    inbox, wire, t = {n: [] for n in nodes}, [], 0.0

    def emit(src, outs):
        for _, env in outs:
            for dst in links[src]:
                wire.append((dst, env))

    emit('A', nodes['A'].send(pack('नाव भेजो', 'hi', seq=1)))
    for _ in range(40):
        while wire:
            dst, env = wire.pop(0)
            inner = nodes[dst].on_receive(env, 'bt', t)
            if inner:
                inbox[dst].append(unpack(inner)['text'])
        for n in nodes:
            emit(n, nodes[n].tick(t))
        t += 0.05
    return {n: inbox[n] for n in nodes}, {n: (nodes[n].relayed, nodes[n].dropped) for n in nodes}


if __name__ == '__main__':
    inbox, stats = demo()
    print(inbox)
    print(stats)
    assert inbox['C'] == ['नाव भेजो'] and inbox['B'] == ['नाव भेजो'] and inbox['A'] == []
