"""Compression benchmark on HELD-OUT sentences (not in the training corpus —
honest numbers). Compares VarnaCode vs UTF-8 vs gzip vs what AMR-NB (12200 bps)
and Codec2-450 would spend on the same utterance spoken aloud.
Run: python bench_compression.py   (writes/updates RESULTS.md)
"""
import gzip

import varnacode as vc

# Held-out test sentences — deliberately NOT in varnacode.CORPUS
TEST = {
    'en': ["Bring the injured woman to the school shelter before dark.",
           "The second boat leaves from the north ghat at 7 tonight.",
           "Tell the sarpanch the tanker is delayed by two hours."],
    'hi': ["घायल महिला को अंधेरा होने से पहले स्कूल शिविर लाएँ।",
           "दूसरी नाव रात सात बजे उत्तर घाट से निकलेगी।",
           "सरपंच को बताएँ कि टैंकर दो घंटे देरी से आएगा।"],
    'bn': ["আহত মহিলাকে অন্ধকারের আগে স্কুল শিবিরে নিয়ে আসুন।",
           "দ্বিতীয় নৌকা রাত সাতটায় উত্তর ঘাট থেকে ছাড়বে।",
           "সরপঞ্চকে বলুন ট্যাংকার দুই ঘণ্টা দেরিতে আসবে।"],
    'ta': ["காயமடைந்த பெண்ணை இருட்டுவதற்கு முன் பள்ளி முகாமுக்கு கொண்டு வாருங்கள்.",
           "இரண்டாவது படகு இரவு ஏழு மணிக்கு வடக்கு துறையில் இருந்து புறப்படும்.",
           "தலைவரிடம் லாரி இரண்டு மணி நேரம் தாமதம் என்று சொல்லுங்கள்."],
    'te': ["గాయపడిన మహిళను చీకటి పడకముందే పాఠశాల శిబిరానికి తీసుకురండి.",
           "రెండవ పడవ రాత్రి ఏడు గంటలకు ఉత్తర రేవు నుండి బయలుదేరుతుంది.",
           "సర్పంచ్‌కు ట్యాంకర్ రెండు గంటలు ఆలస్యం అని చెప్పండి."],
    'gu': ["ઘાયલ મહિલાને અંધારું થાય તે પહેલાં શાળા શિબિરમાં લાવો.",
           "બીજી હોડી રાત્રે સાત વાગ્યે ઉત્તર ઘાટથી નીકળશે."],
    'mr': ["जखमी महिलेला अंधार पडण्यापूर्वी शाळेच्या शिबिरात आणा.",
           "दुसरी होडी रात्री सात वाजता उत्तर घाटावरून निघेल."],
    'kn': ["ಗಾಯಗೊಂಡ ಮಹಿಳೆಯನ್ನು ಕತ್ತಲಾಗುವ ಮೊದಲು ಶಾಲಾ ಶಿಬಿರಕ್ಕೆ ಕರೆತನ್ನಿ.",
           "ಎರಡನೇ ದೋಣಿ ರಾತ್ರಿ ಏಳು ಗಂಟೆಗೆ ಉತ್ತರ ಘಟ್ಟದಿಂದ ಹೊರಡುತ್ತದೆ."],
    'ml': ["പരിക്കേറ്റ സ്ത്രീയെ ഇരുട്ടുന്നതിന് മുമ്പ് സ്കൂൾ ക്യാമ്പിൽ എത്തിക്കുക.",
           "രണ്ടാമത്തെ ബോട്ട് രാത്രി ഏഴിന് വടക്കേ കടവിൽ നിന്ന് പുറപ്പെടും."],
    'or': ["ଆହତ ମହିଳାଙ୍କୁ ଅନ୍ଧାର ହେବା ପୂର୍ବରୁ ବିଦ୍ୟାଳୟ ଶିବିରକୁ ଆଣନ୍ତୁ।",
           "ଦ୍ୱିତୀୟ ଡଙ୍ଗା ରାତି ସାତଟାରେ ଉତ୍ତର ଘାଟରୁ ବାହାରିବ।"],
}

CHARS_PER_SEC = {'en': 13.3}  # Indic scripts pack more per char; ~10 chars/sec spoken


def bench():
    rows = []
    for lang, sents in TEST.items():
        text = ' '.join(sents)
        chars = len(text)
        utf8 = len(text.encode('utf-8'))
        varna = sum(len(vc.encode(s, lang)) for s in sents)
        gz = len(gzip.compress(text.encode('utf-8')))
        secs = chars / CHARS_PER_SEC.get(lang, 10.0)
        amr = secs * 12200 / 8
        c2 = secs * 450 / 8
        bpc = varna * 8 / chars
        # chars fitting a 51-byte LoRa SF12 payload (worst-case frame): UTF-8 vs VarnaCode
        lora_utf8 = int(51 / (utf8 / chars))
        lora_vc = int(51 * 8 / bpc)
        rows.append((lang, chars, utf8, varna, bpc,
                     utf8 / varna, gz, amr / varna, c2 / varna, lora_utf8, lora_vc))
    return rows


def rivals():
    """Measured rivals on the same held-out sentences: SCSU + Unishox2 (real
    encoders, not cited numbers) + the v2 arithmetic-coding experiment.
    Needs the scratchpad venv (scsu, unishox2 pips); prints skip note otherwise."""
    import codecs
    try:
        import scsu  # noqa: F401  (registers the codec)
        import unishox2
    except ImportError as e:
        return f'(rivals skipped: {e})'
    import varnacode2 as v2
    rows = []
    for lang, sents in TEST.items():
        chars = sum(len(s) for s in sents)
        utf8 = sum(len(s.encode('utf-8')) for s in sents)
        sc = sum(len(codecs.encode(s, 'SCSU')) for s in sents)
        un = sum(len(unishox2.compress(s)[0]) for s in sents)
        v1 = sum(len(vc.encode(s, lang)) for s in sents)
        ar = sum(len(v2.encode(s, lang)) for s in sents)
        for s in sents:  # losslessness of the experiment, per sentence
            assert v2.decode(v2.encode(s, lang), lang) == s, (lang, s)
        rows.append((lang, chars, utf8 * 8 / chars, sc * 8 / chars, un * 8 / chars,
                     v1 * 8 / chars, ar * 8 / chars))
    lines = [
        '| Lang | Chars | UTF-8 b/c | SCSU b/c | Unishox2 b/c | VarnaCode v1 b/c | v2 arith b/c |',
        '|---|---|---|---|---|---|---|',
    ]
    for r in rows:
        lines.append('| {} | {} | {:.2f} | {:.2f} | {:.2f} | **{:.2f}** | {:.2f} |'.format(*r))
    avg1 = sum(r[5] for r in rows) / len(rows)
    avg2 = sum(r[6] for r in rows) / len(rows)
    lines.append(f'\navg v1 {avg1:.2f} vs v2-arith {avg2:.2f} bits/char (v2 wins by {avg1 - avg2:.2f})')
    return '\n'.join(lines)


if __name__ == '__main__':
    rows = bench()
    lines = [
        '| Lang | Chars | UTF-8 B | VarnaCode B | bits/char | × vs UTF-8 | gzip B | × vs AMR-NB | × vs Codec2-450 | chars/LoRa-51B UTF-8 | chars/LoRa-51B VarnaCode |',
        '|---|---|---|---|---|---|---|---|---|---|---|',
    ]
    for r in rows:
        lines.append('| {} | {} | {} | {} | {:.2f} | {:.1f}× | {} | {:.0f}× | {:.1f}× | {} | {} |'.format(*r))
    print('\n'.join(lines))
    print()
    print(rivals())
    # RESULTS.md is hand-curated; paste these tables in under the v1 heading.
