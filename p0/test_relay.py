"""Tests for relay.py — run: python test_relay.py"""
import random

import relay as rl
import reliable as r
import phrasebook as pb
from frame import pack, unpack, NORMAL, ALERT

N = 0


def ok(cond, msg):
    global N
    N += 1
    assert cond, msg


def test_envelope_roundtrip_and_size():
    inner = pack('नाव भेजो', 'hi', NORMAL, 5)
    env = rl.wrap(inner, origin=0xBEEF, ttl=3, hops=1)
    ok(len(env) == len(inner) + 9, f'envelope adds 9 B, got {len(env) - len(inner)}')
    ok(rl.is_envelope(env) and not rl.is_envelope(inner), 'marker')
    ok(env[0] & 3 == NORMAL and env[1] == 5, 'prio + seq peekable without decoding')
    i2, o, t, h = rl.unwrap(env)
    ok(i2 == inner and (o, t, h) == (0xBEEF, 3, 1), 'roundtrip')
    ok(unpack(i2)['text'] == 'नाव भेजो', 'inner still decodes')
    a = pack('x', 'hi', ALERT, 9)
    ok(rl.wrap(a, 1)[0] & 3 == ALERT, 'ALERT prio copied to envelope')


def test_envelope_validation():
    inner = pack('x', 'hi', NORMAL, 1)
    for bad in [lambda: rl.wrap(inner, 70000), lambda: rl.wrap(inner, 1, ttl=16), lambda: rl.wrap(inner, 1, hops=16)]:
        try:
            bad()
            ok(False, 'must raise')
        except ValueError:
            ok(True, 'raises')
    env = bytearray(rl.wrap(inner, 1))
    env[-1] ^= 1
    try:
        rl.unwrap(bytes(env))
        ok(False, 'outer crc')
    except ValueError:
        ok(True, 'outer crc catches')
    env = bytearray(rl.wrap(inner, 1))
    env[8] ^= 1  # inside the inner frame
    try:
        rl.unwrap(bytes(env))
        ok(False, 'inner crc')
    except ValueError:
        ok(True, 'inner crc catches (outer would too, but inner is checked independently)')
    try:
        rl.unwrap(inner)
        ok(False, 'not envelope')
    except ValueError:
        ok(True, 'plain frame is not an envelope')


def _chain(names, ttl=rl.DEFAULT_TTL):
    nodes = {n: rl.Relay(i, ['bt'], ttl=ttl, rng=random.Random(i)) for i, n in enumerate(names, start=1)}
    links = {n: [m for m in names if abs(names.index(m) - names.index(n)) == 1] for n in names}
    return nodes, links


def _run(nodes, links, first, steps=60, dt=0.05, hook=None):
    inbox, wire, t = {n: [] for n in nodes}, list(first), 0.0
    for _ in range(steps):
        while wire:
            dst, env = wire.pop(0)
            inner = nodes[dst].on_receive(env, 'bt', t)
            if inner:
                inbox[dst].append(inner)
                if hook:
                    for _, env2 in hook(dst, inner):
                        wire.extend((d, env2) for d in links[dst])
        for n in nodes:
            for _, env in nodes[n].tick(t):
                wire.extend((d, env) for d in links[n])
        t += dt
    return inbox


def test_chain_delivery_once_and_ttl_exhaustion():
    """ttl=3 = three rebroadcasts (Meshtastic hop-limit semantics): A reaches E (4 hops), not F."""
    names = list('ABCDEF')
    nodes, links = _chain(names, ttl=3)
    outs = nodes['A'].send(pack('एक', 'hi', NORMAL, 1))
    inbox = _run(nodes, links, [(d, env) for _, env in outs for d in links['A']])
    got = {n: [unpack(i)['text'] for i in inbox[n]] for n in names}
    ok(all(got[n] == ['एक'] for n in 'BCDE'), f'B..E each receive exactly once, got {got}')
    ok(got['F'] == [], f'F is 5 hops away, ttl=3 stops at E, got {got["F"]}')
    ok(got['A'] == [], 'origin never re-delivers its own frame')
    ok(nodes['E'].relayed == 0, 'E received with ttl 0 and did not rebroadcast')
    ok(all(nodes[n].relayed == 1 for n in 'BCD'), 'B, C, D relayed exactly once each')


def test_alert_no_jitter_normal_jitter():
    node = rl.Relay(7, ['bt', 'wifi'], rng=random.Random(0))
    env_n = rl.wrap(pack('n', 'hi', NORMAL, 1), origin=1)
    env_a = rl.wrap(pack('a', 'hi', ALERT, 2), origin=1)
    node.on_receive(env_n, 'bt', now=10.0)
    node.on_receive(env_a, 'bt', now=10.0)
    now_out = node.tick(10.0)
    ok(len(now_out) == 2 and all(e[0] & 3 == ALERT for _, e in now_out), 'ALERT rebroadcast immediately on both bearers')
    later = node.tick(10.2)
    ok(len(later) == 2 and all(e[0] & 3 == NORMAL for _, e in later), 'NORMAL rebroadcast after jitter on both bearers')
    _, _, ttl, hops = rl.unwrap(later[0][1])
    ok((ttl, hops) == (rl.DEFAULT_TTL - 1, 1), 'ttl decremented, hops incremented')


def test_dedup_is_restart_safe_and_legacy_passthrough():
    node = rl.Relay(9, ['bt'])
    old = rl.wrap(pack('पुराना', 'hi', NORMAL, 0), origin=3)
    ok(node.on_receive(old, 'bt', 0) is not None, 'first delivered')
    ok(node.on_receive(old, 'bt', 0) is None and node.dropped == 1, 'dup dropped')
    new = rl.wrap(pack('नया', 'hi', NORMAL, 0), origin=3)  # peer 3 restarted, seq 0 again
    ok(node.on_receive(new, 'bt', 0) is not None, 'same origin+seq, different bytes = new')
    plain = pack('legacy', 'hi', NORMAL, 4)
    before = len(node.pending)
    ok(node.on_receive(plain, 'bt', 0) == plain and len(node.pending) == before, 'plain frame delivered, never relayed')


def test_phrase_and_ctrl_frames_ride_the_flood():
    node = rl.Relay(1, ['bt'])
    ph = pb.pack(2, NORMAL, 3)
    ctrl = r.make_ctrl(3, r.ACK_BYTE)
    ok(node.on_receive(rl.wrap(ph, 2), 'bt', 0) == ph, 'phrase frame delivered intact')
    ok(node.on_receive(rl.wrap(ctrl, 2), 'bt', 0) == ctrl, 'ctrl frame delivered intact')
    ok(len(node.tick(1.0)) == 2, 'both rebroadcast')


def test_reliable_end_to_end_across_a_hop():
    """A's ReliableSender talks to C's ReliableReceiver through B; B is a dumb relay."""
    names = list('ABC')
    nodes, links = _chain(names)
    tx, rx = r.ReliableSender(now=0.0), r.ReliableReceiver('hi')
    delivered, wire, t = [], [], 0.0
    for f in [pack('एक', 'hi', NORMAL, 1), pack('दो', 'hi', ALERT, 2)]:
        tx.send(f, prio=unpack(f)['prio'])
    for _ in range(80):
        for f in tx.tick(t):
            wire.extend((d, env) for _, env in nodes['A'].send(f) for d in links['A'])
        while wire:
            dst, env = wire.pop(0)
            inner = nodes[dst].on_receive(env, 'bt', t)
            if inner is None:
                continue
            if dst == 'C':
                msg, ctrls = rx.ingest(inner)
                if msg:
                    delivered.append(msg['text'])
                for c in ctrls:  # C's ACKs go back through the flood
                    wire.extend((d, env2) for _, env2 in nodes['C'].send(c) for d in links['C'])
            elif dst == 'A':
                tx.on_ctrl(inner)
        for n in nodes:
            for _, env in nodes[n].tick(t):
                wire.extend((d, env) for d in links[n])
        t += 0.05
    ok(sorted(delivered) == ['एक', 'दो'], f'both delivered once at C, got {delivered}')
    ok(tx.status(1) == 'acked' and tx.status(2) == 'acked', f'A sees ACKs from two hops away, got {tx.state}')
    ok(tx.retransmits == 0, 'no retransmits needed on a clean 2-hop path')


def test_demo():
    inbox, stats = rl.demo()
    ok(inbox == {'A': [], 'B': ['नाव भेजो'], 'C': ['नाव भेजो']}, f'demo, got {inbox}')


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
    print(f'relay: {N} assertions passed')
