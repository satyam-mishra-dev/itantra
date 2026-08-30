"""VarnaCode v0 — Indic-aware per-language Huffman text coder.

UTF-8 spends 24 bits per Indic character (3-byte plane). VarnaCode builds a
per-language canonical Huffman codebook (corpus-trained where we have an
embedded corpus, uniform-over-script-block otherwise) and escapes anything
else as a 21-bit codepoint, so it round-trips ANY string losslessly.
Stdlib only.
"""
import heapq

# 4-bit language ids — order is the wire format, do not reorder (frame.py depends on it)
LANGS = ['en', 'hi', 'bn', 'ta', 'te', 'gu', 'mr', 'kn', 'ml', 'or']

# Disaster/alert-domain training corpora (held-out test sentences live in bench_compression.py)
CORPUS = {
    'en': (
        "Cyclone warning for the coastal districts. Move to the nearest shelter immediately. "
        "Flood water is rising near the river. Do not cross the bridge after sunset. "
        "Medical team needed at the village school. Two people are injured and need help now. "
        "The relief boat will reach the ghat at 5 in the morning. Carry drinking water and dry food. "
        "All fishermen must return to the harbour tonight. Waves are higher than 4 metres. "
        "Power lines are down on the main road. Stay away from the fallen wires. "
        "Rescue helicopter will land at the ground near the temple. Keep the area clear. "
        "Send your location and the number of people with you. Help is on the way. "
        "The dam gates will open at noon. People living downstream must leave now. "
        "Road to the district hospital is blocked by a landslide. Use the old market road instead. "
        "Please confirm you received this message. Over and out. "
        "Earthquake felt in the northern blocks. Check on the old and the sick. "
        "Drinking water tanker reaches the panchayat office at 9. Bring your own vessels."
    ),
    'hi': (
        "चक्रवात तट की ओर बढ़ रहा है। सभी लोग तुरंत सुरक्षित स्थान पर जाएँ। "
        "नदी का पानी पुल के ऊपर बह रहा है। पुल पार करना मना है। "
        "गाँव के स्कूल में राहत शिविर बनाया गया है। खाना और पानी वहाँ मिलेगा। "
        "दो लोग घायल हैं और मदद चाहिए। डॉक्टर की टीम भेजी जा रही है। "
        "बिजली के तार सड़क पर गिरे हैं। तारों से दूर रहें। "
        "बचाव नाव सुबह पाँच बजे घाट पर पहुँचेगी। सूखा खाना और पीने का पानी साथ रखें। "
        "सभी मछुआरे आज रात बंदरगाह लौट आएँ। समुद्र में ऊँची लहरें उठ रही हैं। "
        "बाँध के गेट दोपहर को खोले जाएँगे। नीचे के गाँव खाली कर दें। "
        "अस्पताल का रास्ता भूस्खलन से बंद है। पुराने बाज़ार वाले रास्ते से जाएँ। "
        "अपना स्थान और लोगों की संख्या भेजें। मदद रास्ते में है। "
        "कृपया संदेश मिलने की पुष्टि करें। "
        "भूकंप के झटके महसूस हुए हैं। बुज़ुर्गों और बीमारों का ध्यान रखें। "
        "पानी का टैंकर नौ बजे पंचायत भवन पहुँचेगा। अपने बर्तन साथ लाएँ।"
    ),
    'bn': (
        "ঘূর্ণিঝড় উপকূলের দিকে এগিয়ে আসছে। সবাই এখনই নিরাপদ আশ্রয়ে যান। "
        "নদীর জল সেতুর উপর দিয়ে বইছে। সেতু পার হওয়া নিষেধ। "
        "গ্রামের স্কুলে ত্রাণ শিবির খোলা হয়েছে। খাবার ও জল সেখানে পাওয়া যাবে। "
        "দুজন আহত হয়েছেন এবং সাহায্য দরকার। ডাক্তারের দল পাঠানো হচ্ছে। "
        "বিদ্যুতের তার রাস্তায় পড়ে আছে। তার থেকে দূরে থাকুন। "
        "উদ্ধার নৌকা ভোর পাঁচটায় ঘাটে পৌঁছাবে। শুকনো খাবার ও পানীয় জল সঙ্গে রাখুন। "
        "সব জেলে আজ রাতে বন্দরে ফিরে আসুন। সমুদ্রে বড় ঢেউ উঠছে। "
        "বাঁধের গেট দুপুরে খোলা হবে। নিচের গ্রাম খালি করে দিন। "
        "হাসপাতালের রাস্তা ধসে বন্ধ হয়ে গেছে। পুরনো বাজারের রাস্তা ব্যবহার করুন। "
        "আপনার অবস্থান ও লোকসংখ্যা পাঠান। সাহায্য আসছে। "
        "বার্তা পেয়েছেন কি না জানান। "
        "ভূমিকম্প অনুভূত হয়েছে। বয়স্ক ও অসুস্থদের খোঁজ নিন। "
        "জলের ট্যাংকার নটায় পঞ্চায়েত অফিসে পৌঁছাবে। নিজের পাত্র নিয়ে আসুন।"
    ),
    'ta': (
        "புயல் கரையை நோக்கி நகர்கிறது. அனைவரும் உடனே பாதுகாப்பான இடத்திற்கு செல்லுங்கள். "
        "ஆற்று வெள்ளம் பாலத்தின் மேல் ஓடுகிறது. பாலத்தை கடக்க வேண்டாம். "
        "கிராமப் பள்ளியில் நிவாரண முகாம் அமைக்கப்பட்டுள்ளது. உணவும் தண்ணீரும் அங்கே கிடைக்கும். "
        "இருவர் காயமடைந்துள்ளனர் உதவி தேவை. மருத்துவக் குழு அனுப்பப்படுகிறது. "
        "மின்சார கம்பிகள் சாலையில் விழுந்துள்ளன. கம்பிகளில் இருந்து விலகி இருங்கள். "
        "மீட்புப் படகு காலை ஐந்து மணிக்கு துறைக்கு வரும். உலர் உணவும் குடிநீரும் எடுத்து வாருங்கள். "
        "எல்லா மீனவர்களும் இன்று இரவு துறைமுகம் திரும்ப வேண்டும். கடலில் அலைகள் உயர்ந்துள்ளன. "
        "அணையின் மதகுகள் மதியம் திறக்கப்படும். கீழ்ப்பகுதி கிராமங்களை காலி செய்யுங்கள். "
        "மருத்துவமனை செல்லும் சாலை நிலச்சரிவால் அடைபட்டுள்ளது. பழைய சந்தை சாலையை பயன்படுத்துங்கள். "
        "உங்கள் இடத்தையும் ஆட்களின் எண்ணிக்கையையும் அனுப்புங்கள். உதவி வந்து கொண்டிருக்கிறது. "
        "செய்தி கிடைத்ததை உறுதி செய்யுங்கள். "
        "நில அதிர்வு உணரப்பட்டது. முதியவர்களையும் நோயாளிகளையும் கவனியுங்கள். "
        "தண்ணீர் லாரி ஒன்பது மணிக்கு பஞ்சாயத்து அலுவலகம் வரும். பாத்திரங்களை கொண்டு வாருங்கள்."
    ),
    'te': (
        "తుఫాను తీరం వైపు కదులుతోంది. అందరూ వెంటనే సురక్షిత ప్రాంతానికి వెళ్లండి. "
        "నది వరద వంతెన మీదుగా ప్రవహిస్తోంది. వంతెన దాటవద్దు. "
        "గ్రామ పాఠశాలలో సహాయ శిబిరం ఏర్పాటు చేశారు. ఆహారం నీరు అక్కడ దొరుకుతాయి. "
        "ఇద్దరు గాయపడ్డారు సహాయం కావాలి. వైద్య బృందం పంపబడుతోంది. "
        "కరెంటు తీగలు రోడ్డుపై పడ్డాయి. తీగలకు దూరంగా ఉండండి. "
        "రక్షణ పడవ ఉదయం ఐదు గంటలకు రేవుకు చేరుతుంది. పొడి ఆహారం తాగునీరు తీసుకురండి. "
        "మత్స్యకారులందరూ ఈ రాత్రి ఓడరేవుకు తిరిగి రావాలి. సముద్రంలో అలలు ఎత్తుగా ఉన్నాయి. "
        "ఆనకట్ట గేట్లు మధ్యాహ్నం తెరుస్తారు. దిగువ గ్రామాలు ఖాళీ చేయండి. "
        "ఆసుపత్రి రహదారి కొండచరియతో మూసుకుపోయింది. పాత మార్కెట్ దారిని వాడండి. "
        "మీ స్థానం మనుషుల సంఖ్య పంపండి. సహాయం వస్తోంది. "
        "సందేశం అందిందని ధృవీకరించండి. "
        "భూకంపం సంభవించింది. వృద్ధులను రోగులను చూసుకోండి. "
        "నీటి ట్యాంకర్ తొమ్మిదికి పంచాయతీ కార్యాలయానికి వస్తుంది. పాత్రలు తీసుకురండి."
    ),
}

# Script blocks for languages without an embedded corpus: uniform codebook,
# ~8 bits/char — still 3x tighter than UTF-8's 24.
# ponytail: uniform freqs for gu/mr/kn/ml/or tonight; swap in IndicCorp frequency tables when we harvest them.
BLOCKS = {
    'gu': (0x0A80, 0x0AFF),
    'mr': (0x0900, 0x097F),  # Devanagari
    'kn': (0x0C80, 0x0CFF),
    'ml': (0x0D00, 0x0D7F),
    'or': (0x0B00, 0x0B7F),
}
ASCII_COMMON = ' 0123456789.,!?-:()।'

ESC, EOF = object(), object()


def _freqs(lang):
    f = {}
    if lang in CORPUS:
        for c in CORPUS[lang]:
            f[c] = f.get(c, 0) + 1
    else:
        lo, hi = BLOCKS[lang]
        for cp in range(lo, hi + 1):
            f[chr(cp)] = 1
    for c in ASCII_COMMON:
        f[c] = f.get(c, 0) + 2
    f[ESC] = 1
    f[EOF] = 1
    return f


def _codes(freq):
    """{symbol: count} -> {symbol: bitstring}, canonical Huffman via heapq."""
    heap = [(n, i, [sym]) for i, (sym, n) in enumerate(freq.items())]
    heapq.heapify(heap)
    code = {sym: '' for sym in freq}
    i = len(heap)
    while len(heap) > 1:
        n1, _, s1 = heapq.heappop(heap)
        n2, _, s2 = heapq.heappop(heap)
        for s in s1:
            code[s] = '0' + code[s]
        for s in s2:
            code[s] = '1' + code[s]
        heapq.heappush(heap, (n1 + n2, i, s1 + s2))
        i += 1
    return code


_tables = {}


def _table(lang):
    if lang not in _tables:
        enc = _codes(_freqs(lang))
        _tables[lang] = (enc, {v: k for k, v in enc.items()})
    return _tables[lang]


def encode(text, lang):
    enc, _ = _table(lang)
    bits = []
    for ch in text:
        if ch in enc:
            bits.append(enc[ch])
        else:
            bits.append(enc[ESC])
            bits.append(format(ord(ch), '021b'))  # 21 bits covers all of Unicode
    bits.append(enc[EOF])
    s = ''.join(bits)
    s += '0' * (-len(s) % 8)
    return bytes(int(s[i:i + 8], 2) for i in range(0, len(s), 8))


def decode(data, lang):
    _, dec = _table(lang)
    bits = ''.join(format(b, '08b') for b in data)
    out, buf, i = [], '', 0
    while i < len(bits):
        buf += bits[i]
        i += 1
        sym = dec.get(buf)
        if sym is None:
            continue
        buf = ''
        if sym is EOF:
            break
        if sym is ESC:
            out.append(chr(int(bits[i:i + 21], 2)))
            i += 21
        else:
            out.append(sym)
    return ''.join(out)


def bits_per_char(text, lang):
    return len(encode(text, lang)) * 8 / max(1, len(text))
