"""VarnaCode v2 EXPERIMENT — static arithmetic (range) coding over the same
per-language char+bigram frequencies as v1's Huffman. Measurement only:
kept as the wire format ONLY if it beats v1 by >=0.25 bits/char on held-out
sentences AND round-trips losslessly (see RESULTS.md for the verdict).
Stdlib only. Same greedy tokenization as v1 so the comparison isolates the
entropy-coder change.
"""
import varnacode as vc

_TOP = 0xFFFFFFFF
_HALF = 0x80000000
_QTR = 0x40000000
_3QTR = 0xC0000000
_MAX_TOTAL = 1 << 15  # keep range/total >= 1 with 32-bit registers


class _Model:
    """Static cumulative-frequency model built from v1's frequency table."""

    def __init__(self, lang):
        freq = vc._freqs(lang)
        # scale totals under _MAX_TOTAL, keeping every count >= 1
        total = sum(freq.values())
        scale = max(1.0, total / (_MAX_TOTAL - len(freq)))
        self.syms = list(freq)
        self.counts = [max(1, int(freq[s] / scale)) for s in self.syms]
        self.cum = [0]
        for c in self.counts:
            self.cum.append(self.cum[-1] + c)
        self.total = self.cum[-1]
        self.index = {id(s) if s in (vc.ESC, vc.EOF) else s: i for i, s in enumerate(self.syms)}

    def range_of(self, sym):
        i = self.index[id(sym) if sym in (vc.ESC, vc.EOF) else sym]
        return self.cum[i], self.cum[i + 1]

    def find(self, value):
        # ponytail: linear-free bisect over cum
        import bisect
        i = bisect.bisect_right(self.cum, value) - 1
        return self.syms[i], self.cum[i], self.cum[i + 1]


_models = {}


def _model(lang):
    if lang not in _models:
        _models[lang] = _Model(lang)
    return _models[lang]


class _Enc:
    def __init__(self):
        self.low, self.high, self.pending, self.bits = 0, _TOP, 0, []

    def _bit(self, b):
        self.bits.append(b)
        self.bits.extend('1' if b == '0' else '0' for _ in range(self.pending))
        self.pending = 0

    def emit(self, lo_c, hi_c, total):
        rng = self.high - self.low + 1
        self.high = self.low + rng * hi_c // total - 1
        self.low = self.low + rng * lo_c // total
        while True:
            if self.high < _HALF:
                self._bit('0')
            elif self.low >= _HALF:
                self._bit('1')
                self.low -= _HALF
                self.high -= _HALF
            elif self.low >= _QTR and self.high < _3QTR:
                self.pending += 1
                self.low -= _QTR
                self.high -= _QTR
            else:
                break
            self.low <<= 1
            self.high = (self.high << 1) | 1

    def flush(self):
        self.pending += 1
        self._bit('0' if self.low < _QTR else '1')
        s = ''.join(self.bits)
        s += '0' * (-len(s) % 8)
        return bytes(int(s[i:i + 8], 2) for i in range(0, len(s), 8))


def _tokens(text, lang):
    """Same greedy bigram tokenization as v1 (Huffman code lengths decide)."""
    enc, _ = vc._table(lang)
    i = 0
    while i < len(text):
        pair = text[i:i + 2]
        if len(pair) == 2 and pair in enc and len(enc[pair]) < len(enc.get(text[i], 'x' * 99)) + len(enc.get(text[i + 1], 'x' * 99)):
            yield pair
            i += 2
            continue
        yield text[i]
        i += 1


def encode(text, lang):
    m = _model(lang)
    e = _Enc()
    for tok in _tokens(text, lang):
        if tok in m.index:
            lo, hi = m.range_of(tok)
            e.emit(lo, hi, m.total)
        else:  # escape + 21 raw bits, each as a uniform binary symbol
            lo, hi = m.range_of(vc.ESC)
            e.emit(lo, hi, m.total)
            for b in format(ord(tok), '021b'):
                e.emit(int(b), int(b) + 1, 2)
    lo, hi = m.range_of(vc.EOF)
    e.emit(lo, hi, m.total)
    return e.flush()


def decode(data, lang):
    m = _model(lang)
    bits = ''.join(format(b, '08b') for b in data) + '0' * 64
    low, high, pos = 0, _TOP, 32
    value = int(bits[:32], 2)

    def scaled(total):
        rng = high - low + 1
        return ((value - low + 1) * total - 1) // rng

    def consume(lo_c, hi_c, total):
        nonlocal low, high, value, pos
        rng = high - low + 1
        high = low + rng * hi_c // total - 1
        low = low + rng * lo_c // total
        while True:
            if high < _HALF:
                pass
            elif low >= _HALF:
                low -= _HALF
                high -= _HALF
                value -= _HALF
            elif low >= _QTR and high < _3QTR:
                low -= _QTR
                high -= _QTR
                value -= _QTR
            else:
                break
            low <<= 1
            high = (high << 1) | 1
            value = (value << 1) | int(bits[pos])
            pos += 1

    out = []
    while True:
        sym, lo_c, hi_c = m.find(scaled(m.total))
        consume(lo_c, hi_c, m.total)
        if sym is vc.EOF:
            break
        if sym is vc.ESC:
            cp = 0
            for _ in range(21):
                b = scaled(2)
                consume(b, b + 1, 2)
                cp = (cp << 1) | b
            out.append(chr(cp))
        else:
            out.append(sym)
    return ''.join(out)


def bits_per_char(text, lang):
    return len(encode(text, lang)) * 8 / max(1, len(text))


if __name__ == '__main__':
    # self-check: lossless on the v1 test surface
    from test_p0 import SAMPLES, EDGE
    n = 0
    for lang, text in SAMPLES.items():
        assert decode(encode(text, lang), lang) == text, lang
        n += 1
    for lang in vc.LANGS:
        for text in EDGE:
            assert decode(encode(text, lang), lang) == text, (lang, repr(text))
            n += 1
    print(f'varnacode2 lossless: {n} cases OK')
