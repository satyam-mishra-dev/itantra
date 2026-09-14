"""Tests for reliable.py — run: python test_reliable.py"""
import reliable as r
from frame import pack, unpack, NORMAL, ALERT
import rollcall

N = 0


def ok(cond, msg):
    global N
    N += 1
    assert cond, msg


def test_ctrl_roundtrip_and_no_collision():
    a = r.make_ctrl(42, r.ACK_BYTE)
    n = r.make_ctrl(7, r.NACK_BYTE, 'ta')
    ok(len(a) == 7 and len(n) == 7, 'ctrl frame is 7 bytes')
    ok(r.parse_ctrl(a) == (42, r.ACK_BYTE), 'ack parses')
    ok(r.parse_ctrl(n) == (7, r.NACK_BYTE), 'nack parses')
    ok(r.parse_ctrl(a[:-1] + bytes([a[-1] ^ 1])) is None, 'crc flips reject')
    rc = rollcall.make_ack('hi', 3, 1234, rollcall.SOS)
    ok(r.parse_ctrl(rc) is None, 'roll-call ack is not a delivery ctrl')
    try:
        rollcall.parse_ack(a)
        ok(False, 'roll-call must reject delivery ack')
    except ValueError:
        ok(True, 'roll-call rejects delivery ack')
    ok(r.parse_ctrl(pack('hi', 'hi', NORMAL, 5)) is None, 'data frame is not ctrl')


def test_ack_stops_retransmit():
    tx = r.ReliableSender()
    f = pack('ok', 'hi', NORMAL, 9)
    tx.send(f)
    out = tx.tick(0.0)
    ok(out == [f] and tx.status(9) == 'sent', 'first send')
    ok(tx.tick(0.5) == [], 'nothing before RTO')
    ok(tx.on_ctrl(r.make_ctrl(9, r.ACK_BYTE)), 'ack consumed')
    ok(tx.status(9) == 'acked', 'acked')
    ok(tx.tick(5.0) == [], 'no retransmit after ack')


def test_retry_budget_normal_vs_alert():
    tx = r.ReliableSender()
    fn = pack('n', 'hi', NORMAL, 1)
    fa = pack('a', 'hi', ALERT, 2)
    tx.send(fn, NORMAL)
    tx.send(fa, ALERT)
    first = tx.tick(0.0)
    ok(first == [fa, fn], 'ALERT jumps the queue')
    sends = {1: 1, 2: 1}
    t = 0.0
    for _ in range(10):
        t += r.RTO
        for f in tx.tick(t):
            sends[f[1]] += 1
    ok(sends[1] == 3 and sends[2] == 5, f'tries NORMAL=3 ALERT=5, got {sends}')
    ok(tx.status(1) == 'failed' and tx.status(2) == 'failed', 'both fail after budget')
    ok(tx.inflight == {}, 'nothing left in flight')


def test_nack_resends_without_consuming_try():
    tx = r.ReliableSender()
    f = pack('x', 'hi', NORMAL, 4)
    tx.send(f)
    tx.tick(0.0)
    ok(tx.on_ctrl(r.make_ctrl(4, r.NACK_BYTE)), 'nack consumed')
    ok(tx.tick(0.1) == [f], 'nack triggers immediate resend')
    ok(tx.inflight[4]['left'] == 2, 'nack did not consume a try')


def test_receiver_dedup_ack_and_gap_nack():
    rx = r.ReliableReceiver('hi')
    f1, f2, f4 = (pack(s, 'hi', NORMAL, q) for s, q in (('एक', 1), ('दो', 2), ('चार', 4)))
    m, c = rx.ingest(f1)
    ok(m['text'] == 'एक' and [r.parse_ctrl(x) for x in c] == [(1, r.ACK_BYTE)], 'first frame acked')
    m, c = rx.ingest(f1)
    ok(m is None and [r.parse_ctrl(x) for x in c] == [(1, r.ACK_BYTE)], 'duplicate: no deliver, re-ack')
    m, c = rx.ingest(f2)
    ok(m['seq'] == 2 and len(c) == 1, 'in-order: ack only')
    m, c = rx.ingest(f4)
    kinds = [r.parse_ctrl(x) for x in c]
    ok(m['seq'] == 4 and kinds == [(4, r.ACK_BYTE), (3, r.NACK_BYTE)], f'gap -> nack 3, got {kinds}')
    f3 = pack('तीन', 'hi', NORMAL, 3)
    m, c = rx.ingest(f3)
    ok(m['seq'] == 3 and len(c) == 1, 'late frame delivered and acked')


def test_receiver_ignores_ctrl_and_rollcall():
    rx = r.ReliableReceiver()
    ok(rx.ingest(r.make_ctrl(1, r.ACK_BYTE)) == (None, []), 'ctrl frames pass through silently')
    m, c = rx.ingest(rollcall.make_question('सब ठीक?', 'hi', 5))
    ok(m['prio'] == ALERT and len(c) == 1, 'ALERT question acked like any data frame')


def test_seq_wrap():
    rx = r.ReliableReceiver()
    rx.ingest(pack('a', 'hi', NORMAL, 254))
    m, c = rx.ingest(pack('b', 'hi', NORMAL, 1))
    kinds = sorted(k for _, k in [r.parse_ctrl(x) for x in c])
    nacked = sorted(s for s, k in [r.parse_ctrl(x) for x in c] if k == r.NACK_BYTE)
    ok(nacked == [0, 255], f'gap across wrap nacks 255 and 0, got {nacked}')


def test_encrypted_frames_ack_too():
    key = bytes(range(16))
    rx = r.ReliableReceiver()
    f = pack('गुप्त', 'hi', NORMAL, 8, key=key)
    m, c = rx.ingest(f, key=key)
    ok(m['text'] == 'गुप्त' and r.parse_ctrl(c[0]) == (8, r.ACK_BYTE), 'encrypted frame delivered + acked')


def test_demo_end_to_end():
    d, st = r.demo()
    ok(sorted(s for s, _ in d) == [1, 2, 3], f'each delivered exactly once (3 arrives first: 1,2 were dropped then NACKed), got {d}')
    ok(all(v == 'acked' for v in st.values()), f'all acked, got {st}')


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
    print(f'reliable: {N} assertions passed')
