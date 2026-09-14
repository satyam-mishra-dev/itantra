"""Tests for speak.py — run: python test_speak.py"""
import speak as sp

N = 0


def ok(cond, msg):
    global N
    N += 1
    assert cond, msg


def test_indian_numbers():
    ok(sp.indian_number_words(999, 'hi') == '999', 'small numbers untouched')
    ok(sp.indian_number_words(1500, 'hi') == '1 हज़ार 500', '1,500')
    ok(sp.indian_number_words(150000, 'hi') == '1 लाख 50 हज़ार', '1,50,000 hi')
    ok(sp.indian_number_words(150000, 'bn') == '1 লাখ 50 হাজার', '1,50,000 bn')
    ok(sp.indian_number_words(23456789, 'en') == '2 crore 34 lakh 56 thousand 789', 'crore en')
    ok(sp.indian_number_words(10000000, 'ta') == '1 கோடி', 'exact crore ta')
    t = sp.normalise_text('वहाँ 1,50,000 लोग और 2,000 नावें हैं', 'hi')
    ok(t == 'वहाँ 1 लाख 50 हज़ार लोग और 2 हज़ार नावें हैं', f'inline grouped numbers, got {t}')
    t = sp.normalise_text('flood at 150000 homes', 'en')
    ok(t == 'flood at 1 lakh 50 thousand homes', f'ungrouped 6-digit, got {t}')
    ok(sp.normalise_text('call 100', 'hi') == 'call 100', '3-digit stays')


def test_abbreviations_and_acronyms():
    ok(sp.normalise_text('3 km दूर, 2 hrs में', 'hi') == '3 किलोमीटर दूर, 2 घंटे में', 'hi units')
    ok(sp.normalise_text('NDRF and ISRO teams', 'en') == 'N D R F and I S R O teams', 'acronyms spelled')
    ok(sp.normalise_text('ok Go', 'en') == 'ok Go', 'normal words untouched')
    ok(sp.normalise_text('5 km', 'or') == '5 km', 'no lexicon for lang -> unchanged, not an error')


def test_clause_split():
    c = sp.split_clauses('पहला वाक्य। दूसरा वाक्य॥ तीसरा?  चौथा!')
    ok(c == ['पहला वाक्य', 'दूसरा वाक्य', 'तीसरा', 'चौथा'], f'danda/punct split, got {c}')
    long = ', '.join(['क' * 30] * 5)
    c = sp.split_clauses(long)
    ok(len(c) == 3 and all(len(x) <= sp.MAX_CLAUSE for x in c), f'long clause split at commas, got {[len(x) for x in c]}')
    ok(sp.split_clauses('   ') == [], 'blank -> no clauses')
    ok(sp.normalise('a. b', 'hi') == ['a', 'b'], 'normalise returns clauses')
    try:
        sp.normalise('x', 'xx')
        ok(False, 'unknown lang must raise')
    except ValueError:
        ok(True, 'unknown lang raises')


def test_queue_order_and_resume():
    q = sp.SpeakQueue()
    q.enqueue('एक। दो। तीन।', 'hi', msg_id='n')
    ok(q.next()['clause'] == 'एक', 'first clause')
    q.enqueue('सावधान। भागो।', 'hi', alert=True, msg_id='a')
    seq = []
    while (it := q.next()):
        seq.append((it['msg_id'], it['clause'], it['alert'], it['replay']))
    ok([s[1] for s in seq] == ['सावधान', 'भागो', 'सावधान', 'भागो', 'दो', 'तीन'],
       f'alert at boundary, twice, then resume at clause 2, got {[s[1] for s in seq]}')
    ok([s[3] for s in seq[:4]] == [False, False, True, True], 'replay flag marks the second pass')
    ok(all(s[2] for s in seq[:4]) and not any(s[2] for s in seq[4:]), 'alert flag correct')
    ok(q.pending() == 0 and q.next() is None, 'drained')


def test_alert_gain_and_pending():
    q = sp.SpeakQueue()
    q.enqueue('normal', 'en', gain=0.7)
    q.enqueue('alert', 'en', alert=True)
    ok(q.pending() == 3, 'pending counts the replay')
    it = q.next()
    ok(it['alert'] and it['gain'] == sp.SpeakQueue.ALERT_GAIN, 'alert gain override')
    q.next()
    it = q.next()
    ok(not it['alert'] and it['gain'] == 0.7, 'normal keeps its gain')


def test_two_alerts_fifo_and_empty_enqueue():
    q = sp.SpeakQueue()
    ok(q.enqueue('   ', 'hi') is None, 'empty text not queued')
    q.enqueue('A', 'en', alert=True, msg_id=1)
    q.enqueue('B', 'en', alert=True, msg_id=2)
    ids = [q.next()['msg_id'] for _ in range(4)]
    ok(ids == [1, 1, 2, 2], f'alerts FIFO, each twice, got {ids}')


def test_demo():
    seq = sp.demo()
    ok(seq[0] == 'राहत शिविर 3 किलोमीटर दूर है' and seq[-1] == 'N D R F की टीम आ रही है', 'demo shape')
    ok(sum(s.startswith('ALERT') for s in seq) == 4, 'demo alert spoken twice (2 clauses x 2)')


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
    print(f'speak: {N} assertions passed')
