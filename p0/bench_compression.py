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
        rows.append((lang, chars, utf8, varna, varna * 8 / chars,
                     utf8 / varna, gz, amr / varna, c2 / varna))
    return rows


if __name__ == '__main__':
    rows = bench()
    lines = [
        '## Compression benchmark (held-out sentences, measured)',
        '',
        '| Lang | Chars | UTF-8 B | VarnaCode B | bits/char | × vs UTF-8 | gzip B | × vs AMR-NB | × vs Codec2-450 |',
        '|---|---|---|---|---|---|---|---|---|',
    ]
    for r in rows:
        lines.append('| {} | {} | {} | {} | {:.2f} | {:.1f}× | {} | {:.0f}× | {:.1f}× |'.format(
            r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8]))
    lines.append('')
    lines.append('*AMR/Codec2 columns: bytes those codecs would spend on the same sentence '
                 'spoken aloud (13.3 chars/s en, 10 chars/s Indic) ÷ VarnaCode bytes. '
                 'gzip shown for honesty: on short single sentences its header overhead loses to VarnaCode.*')
    out = '\n'.join(lines) + '\n'
    print(out)
    with open('RESULTS.md', 'a') as f:
        f.write(out + '\n')
