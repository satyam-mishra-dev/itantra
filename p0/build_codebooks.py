"""Build corpus-trained VarnaCode codebooks (v1).

Fetches ~200KB of Wikipedia prose per language (build-time only, network OK),
blends char/bigram frequencies with the embedded disaster-domain corpus in
varnacode.CORPUS (domain-weighted), and writes codebooks.json — which is
checked into git so normal builds/tests stay offline-reproducible.
Raw corpus text is NOT committed (goes to ./corpus_cache/, gitignored).

Run: python build_codebooks.py            (uses cache if present)
     python build_codebooks.py --refetch  (force re-download)
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from collections import Counter

import varnacode as vc

WIKI = {'en': 'en', 'hi': 'hi', 'bn': 'bn', 'ta': 'ta', 'te': 'te',
        'gu': 'gu', 'mr': 'mr', 'kn': 'kn', 'ml': 'ml', 'or': 'or'}
TARGET_CHARS = 200_000
CACHE = os.path.join(os.path.dirname(__file__), 'corpus_cache')
OUT = os.path.join(os.path.dirname(__file__), 'codebooks.json')
N_BIGRAMS = 192  # top bigrams promoted to codebook symbols


def fetch_corpus(lang):
    """Random-article plaintext extracts until TARGET_CHARS."""
    text, tries = [], 0
    total = 0
    while total < TARGET_CHARS and tries < 60:
        tries += 1
        q = urllib.parse.urlencode({
            'action': 'query', 'format': 'json', 'generator': 'random',
            'grnnamespace': 0, 'grnlimit': 20, 'prop': 'extracts',
            'explaintext': 1, 'exlimit': 20, 'exintro': 1,
        })
        url = f'https://{WIKI[lang]}.wikipedia.org/w/api.php?{q}'
        req = urllib.request.Request(url, headers={'User-Agent': 'iTantra-SIH2026-codebook-builder/1.0'})
        try:
            data = json.load(urllib.request.urlopen(req, timeout=30))
        except Exception as e:
            print(f'  {lang}: fetch error {e}; retrying')
            continue
        for page in data.get('query', {}).get('pages', {}).values():
            ex = page.get('extract', '')
            if ex:
                text.append(ex)
                total += len(ex)
    got = '\n'.join(text)
    if len(got) < 50_000:  # random-generator failed (bn does this) — fall back to fixed famous articles
        got += _fetch_titles(lang)
    return got


# ponytail: fixed fallback titles only for languages where generator=random starves; expand per-language if it recurs
FALLBACK_TITLES = {
    'bn': ['ভারত', 'বাংলাদেশ', 'কলকাতা', 'ঢাকা', 'রবীন্দ্রনাথ ঠাকুর', 'বাংলা ভাষা', 'পশ্চিমবঙ্গ',
           'ঘূর্ণিঝড়', 'বন্যা', 'ভূমিকম্প', 'গঙ্গা', 'সুন্দরবন', 'চট্টগ্রাম', 'বাংলা সাহিত্য',
           'ভারতের ইতিহাস', 'জলবায়ু পরিবর্তন', 'কাজী নজরুল ইসলাম', 'সত্যজিৎ রায়', 'মুক্তিযুদ্ধ', 'হিমালয়'],
}


def _fetch_titles(lang):
    text = []
    for title in FALLBACK_TITLES.get(lang, []):
        q = urllib.parse.urlencode({
            'action': 'query', 'format': 'json', 'prop': 'extracts',
            'explaintext': 1, 'titles': title, 'redirects': 1,
        })
        url = f'https://{WIKI[lang]}.wikipedia.org/w/api.php?{q}'
        req = urllib.request.Request(url, headers={'User-Agent': 'iTantra-SIH2026-codebook-builder/1.0'})
        try:
            data = json.load(urllib.request.urlopen(req, timeout=30))
            for page in data.get('query', {}).get('pages', {}).values():
                text.append(page.get('extract', ''))
        except Exception as e:
            print(f'  {lang}:{title}: {e}')
    return '\n'.join(text)


def corpus_for(lang, refetch=False):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f'{lang}.txt')
    if not refetch and os.path.exists(path) and os.path.getsize(path) > 50_000:
        return open(path, encoding='utf-8').read()
    print(f'fetching {lang} wikipedia corpus...')
    text = fetch_corpus(lang)
    open(path, 'w', encoding='utf-8').write(text)
    return text


def build(lang, wiki_text):
    # Wikipedia gives coverage; the embedded disaster corpus gives domain weight.
    chars = Counter(wiki_text)
    # scale wiki counts to a fixed mass so domain corpus isn't drowned
    mass = sum(chars.values())
    scale = 50_000 / max(1, mass)
    freq = {c: max(1, int(n * scale)) for c, n in chars.items()
            if not (0xD800 <= ord(c) <= 0xDFFF)}
    domain = vc.CORPUS.get(lang, '')
    for c in domain:
        freq[c] = freq.get(c, 0) + 40  # domain chars count heavily
    # top bigrams from wiki + domain (domain 40x) as multi-char symbols
    big = Counter()
    for src, w in ((wiki_text, 1), (domain, 40)):
        for a, b in zip(src, src[1:]):
            if a != '\n' and b != '\n':
                big[a + b] += w
    bigrams = {bg: n for bg, n in big.most_common(N_BIGRAMS) if n > 2}
    return {'chars': freq, 'bigrams': bigrams}


if __name__ == '__main__':
    refetch = '--refetch' in sys.argv
    books = {}
    for lang in vc.LANGS:
        wiki = corpus_for(lang, refetch)
        books[lang] = build(lang, wiki)
        print(f'{lang}: {len(wiki)} corpus chars -> {len(books[lang]["chars"])} char syms, '
              f'{len(books[lang]["bigrams"])} bigram syms')
    json.dump(books, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'wrote {OUT} ({os.path.getsize(OUT)} bytes)')
