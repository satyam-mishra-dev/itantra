"""Far-end speech policy: TTS text normalisation + clause-chunked queue with ALERT preemption.

Why this exists (measured, not guessed): Piper reads the danda aloud as "पूर्णविराम"
(pipeline_demo.py), Indian-grouped numbers like 1,50,000 come out as digit soup, and
acronyms (NDRF) get pronounced as a word. And the ALERT class in the frame header
currently only changes urgency; it should also *interrupt*: an alert must start at the
next clause boundary, the interrupted message must resume afterwards, and the alert
should be heard twice (the strongest rival implementations do exactly this).

normalise(text, lang) -> [clause, ...]   clauses ready for TTS, in order
SpeakQueue                               deterministic scheduler; the app drives it

Stdlib only. Kotlin port mirrors these functions 1:1 (see HANDOFF.md).
"""
import re

from varnacode import LANGS

# thousand / lakh / crore in each language (digits stay digits; TTS reads them fine)
_UNITS = {
    'en': ('thousand', 'lakh', 'crore'),
    'hi': ('हज़ार', 'लाख', 'करोड़'),
    'bn': ('হাজার', 'লাখ', 'কোটি'),
    'ta': ('ஆயிரம்', 'லட்சம்', 'கோடி'),
    'te': ('వేలు', 'లక్షలు', 'కోట్లు'),
    'gu': ('હજાર', 'લાખ', 'કરોડ'),
    'mr': ('हजार', 'लाख', 'कोटी'),
    'kn': ('ಸಾವಿರ', 'ಲಕ್ಷ', 'ಕೋಟಿ'),
    'ml': ('ആയിരം', 'ലക്ഷം', 'കോടി'),
    'or': ('ହଜାର', 'ଲକ୍ଷ', 'କୋଟି'),
}

# unit abbreviations that TTS mangles; extend per language as the lexicon grows
_ABBR = {
    'en': {'km': 'kilometre', 'kg': 'kilogram', 'hrs': 'hours', 'hr': 'hour', 'min': 'minutes', 'ft': 'feet'},
    'hi': {'km': 'किलोमीटर', 'kg': 'किलो', 'hrs': 'घंटे', 'hr': 'घंटा', 'min': 'मिनट', 'ft': 'फ़ीट'},
    'mr': {'km': 'किलोमीटर', 'kg': 'किलो', 'hrs': 'तास', 'hr': 'तास', 'min': 'मिनिटे', 'ft': 'फूट'},
    'bn': {'km': 'কিলোমিটার', 'kg': 'কেজি', 'hrs': 'ঘণ্টা', 'hr': 'ঘণ্টা', 'min': 'মিনিট', 'ft': 'ফুট'},
}

# pronunciation lexicon for alert vocabulary: acronyms are spelled out, letter by letter
_ACRONYM = re.compile(r'\b([A-Z]{2,6})\b')
_INDIAN_NUMBER = re.compile(r'\d{1,2}(?:,\d{2})*,\d{3}|\d{4,}')  # 1,50,000 or 150000
_CLAUSE_END = re.compile(r'[।॥\.!?]+\s*|[\n]+')
_SOFT_BREAK = re.compile(r'[,;:]\s*|[،]\s*')
MAX_CLAUSE = 90  # chars; longer clauses are split at a soft break so first audio starts early


def indian_number_words(n, lang):
    """150000 -> '1 लाख 50 हज़ार' (hi). Numbers < 1000 are returned unchanged."""
    thou, lakh, crore = _UNITS.get(lang, _UNITS['en'])
    if n < 1000:
        return str(n)
    parts = []
    c, rest = divmod(n, 10_000_000)
    l, rest = divmod(rest, 100_000)
    t, rest = divmod(rest, 1000)
    if c:
        parts.append(f'{c} {crore}')
    if l:
        parts.append(f'{l} {lakh}')
    if t:
        parts.append(f'{t} {thou}')
    if rest:
        parts.append(str(rest))
    return ' '.join(parts)


def normalise_text(text, lang):
    """Single string, not yet split: numbers, abbreviations, acronyms fixed."""
    abbr = _ABBR.get(lang, {})
    if abbr:
        text = re.sub(r'\b(' + '|'.join(map(re.escape, abbr)) + r')\b',
                      lambda m: abbr[m.group(1)], text)
    text = _INDIAN_NUMBER.sub(lambda m: indian_number_words(int(m.group(0).replace(',', '')), lang), text)
    text = _ACRONYM.sub(lambda m: ' '.join(m.group(1)), text)
    return text


def split_clauses(text):
    """Split on danda / sentence punctuation; long clauses split again at commas."""
    out = []
    for piece in _CLAUSE_END.split(text):
        piece = piece.strip()
        if not piece:
            continue
        if len(piece) <= MAX_CLAUSE:
            out.append(piece)
            continue
        buf = ''
        for sub in _SOFT_BREAK.split(piece):
            sub = sub.strip()
            if not sub:
                continue
            if buf and len(buf) + len(sub) + 1 > MAX_CLAUSE:
                out.append(buf)
                buf = sub
            else:
                buf = f'{buf}, {sub}' if buf else sub
        if buf:
            out.append(buf)
    return out


def normalise(text, lang):
    if lang not in LANGS:
        raise ValueError(f'unknown lang {lang}')
    return split_clauses(normalise_text(text, lang))


class SpeakQueue:
    """Clause-level scheduler with ALERT preemption.

    enqueue(text, lang, alert=False, gain=1.0, msg_id=None)
    next() -> {'msg_id', 'lang', 'clause', 'alert', 'gain', 'replay'} | None
        Call once per clause the TTS engine is about to speak. An ALERT arriving
        while a NORMAL message is mid-way takes over at the next call (clause
        boundary); the NORMAL message's remaining clauses return to the front and
        resume after the alert. ALERT clauses are spoken ALERT_REPLAYS+1 times.
    pending() -> number of clauses still queued
    """
    ALERT_REPLAYS = 1
    ALERT_GAIN = 1.6  # the app maps this onto STREAM_ALARM at max, then restores

    def __init__(self):
        self.normal = []   # list of msgs; each msg = dict(msg_id, lang, clauses:list, gain, alert)
        self.alerts = []
        self._n = 0
        self.spoken = []   # log of (msg_id, clause, alert) for tests/telemetry

    def enqueue(self, text, lang, alert=False, gain=1.0, msg_id=None):
        clauses = normalise(text, lang)
        if not clauses:
            return None
        self._n += 1
        mid = msg_id if msg_id is not None else self._n
        msg = {'msg_id': mid, 'lang': lang, 'clauses': list(clauses), 'gain': gain,
               'alert': alert, 'replays_left': self.ALERT_REPLAYS if alert else 0,
               'full': list(clauses)}
        (self.alerts if alert else self.normal).append(msg)
        return mid

    def _pop_clause(self, msg):
        clause = msg['clauses'].pop(0)
        item = {'msg_id': msg['msg_id'], 'lang': msg['lang'], 'clause': clause,
                'alert': msg['alert'], 'gain': self.ALERT_GAIN if msg['alert'] else msg['gain'],
                'replay': msg['alert'] and msg['replays_left'] < self.ALERT_REPLAYS}
        self.spoken.append((msg['msg_id'], clause, msg['alert']))
        return item

    def next(self):
        # alerts first; a NORMAL message mid-way simply keeps its remaining clauses at the
        # front of self.normal, so it resumes at exactly the clause where it was cut
        if self.alerts:
            msg = self.alerts[0]
            item = self._pop_clause(msg)
            if not msg['clauses']:
                if msg['replays_left'] > 0:
                    msg['replays_left'] -= 1
                    msg['clauses'] = list(msg['full'])
                else:
                    self.alerts.pop(0)
            return item
        if self.normal:
            msg = self.normal[0]
            item = self._pop_clause(msg)
            if not msg['clauses']:
                self.normal.pop(0)
            return item
        return None

    def pending(self):
        return sum(len(m['clauses']) for m in self.normal) + \
            sum(len(m['clauses']) + len(m['full']) * m['replays_left'] for m in self.alerts)


def demo():
    q = SpeakQueue()
    q.enqueue('राहत शिविर 3 km दूर है। वहाँ 1,50,000 लोग हैं। NDRF की टीम आ रही है।', 'hi')
    first = q.next()                     # clause 1 of the normal message
    q.enqueue('बाढ़ का पानी आ रहा है। तुरंत ऊँची जगह जाओ।', 'hi', alert=True)
    seq = [first['clause']]
    while (it := q.next()):
        seq.append(('ALERT ' if it['alert'] else '') + it['clause'])
    return seq


if __name__ == '__main__':
    for line in demo():
        print(line)
