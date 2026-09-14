package com.nullpointers.itantra

import org.json.JSONArray
import org.json.JSONObject

/**
 * Kotlin port of p0/phrasebook.py — a whole spoken sentence as a 9–10 byte, language-neutral frame.
 *
 * Header is the unchanged iTantra header with lang = 15 (phrase marker). Payload:
 *     fp8 · idx_hi:4|flags:4 · idx_lo:8 · [n:8]
 * The receiver renders the phrase in ITS OWN language: no MT model, ~2.5× fewer bytes than text.
 * Sender policy: match() ranks candidates; the UI shows the best one and the user confirms — never
 * auto-send a snapped phrase. Load with the same phrasebook.json as p0 (assets + test resources).
 */
class Phrasebook(json: String) {
    val phrases: List<Map<String, String>>
    val fingerprint: Int

    init {
        val arr = JSONObject(json).getJSONArray("phrases")
        phrases = (0 until arr.length()).map { i ->
            val o = arr.getJSONObject(i)
            VarnaCode.LANGS.associateWith { o.getString(it) }
        }
        fingerprint = Frame.crc16(canonical(arr).toByteArray(Charsets.UTF_8))
    }

    /** Same canonical form as Python: json.dumps(phrases, ensure_ascii=False, sort_keys=True, separators=(',',':')). */
    private fun canonical(arr: JSONArray): String = buildString {
        append('[')
        for (i in 0 until arr.length()) {
            if (i > 0) append(',')
            val o = arr.getJSONObject(i)
            append('{')
            o.keys().asSequence().sorted().forEachIndexed { j, k ->
                if (j > 0) append(',')
                append('"').append(k).append("\":").append(jsonString(o.getString(k)))
            }
            append('}')
        }
        append(']')
    }

    private fun jsonString(s: String): String = buildString {
        append('"')
        for (ch in s) when (ch) {
            '"' -> append("\\\""); '\\' -> append("\\\\"); '\n' -> append("\\n"); '\r' -> append("\\r"); '\t' -> append("\\t")
            else -> if (ch < ' ') append(String.format("\\u%04x", ch.code)) else append(ch)
        }
        append('"')
    }

    fun hasSlot(idx: Int) = phrases[idx]["en"]!!.contains(SLOT)

    fun render(idx: Int, lang: String, n: Int? = null): String {
        val t = phrases[idx][lang] ?: throw IllegalArgumentException("unknown lang $lang")
        return if (t.contains(SLOT)) t.replace(SLOT, (n ?: 0).toString()) else t
    }

    fun pack(idx: Int, prio: Int = Frame.NORMAL, seq: Int = 0, n: Int? = null): ByteArray {
        require(idx in phrases.indices && idx <= 0xFFF) { "bad phrase index" }
        var payload = byteArrayOf((fingerprint and 0xFF).toByte(), (((idx shr 8) and 0xF) shl 4).toByte(), (idx and 0xFF).toByte())
        if (hasSlot(idx)) {
            require(n != null && n in 0..255) { "slot value 0..255 required" }
            payload = byteArrayOf(payload[0], (payload[1].toInt() or FLAG_SLOT).toByte(), payload[2], n.toByte())
        }
        val body = byteArrayOf(((PHRASE_LANG shl 2) or (prio and 3)).toByte(), (seq and 0xFF).toByte(), 0, payload.size.toByte()) + payload
        val crc = Frame.crc16(body)
        return body + byteArrayOf((crc ushr 8).toByte(), (crc and 0xFF).toByte())
    }

    data class Decoded(val idx: Int, val n: Int?, val prio: Int, val seq: Int, val fpOk: Boolean)

    fun unpack(f: ByteArray): Decoded {
        require(isPhraseFrame(f)) { "not a phrase frame" }
        val crc = ((f[f.size - 2].toInt() and 0xFF) shl 8) or (f[f.size - 1].toInt() and 0xFF)
        require(Frame.crc16(f, f.size - 2) == crc) { "CRC mismatch" }
        val plen = ((f[2].toInt() and 0xFF) shl 8) or (f[3].toInt() and 0xFF)
        require(f.size - 6 == plen && (plen == 3 || plen == 4)) { "length mismatch" }
        val fp8 = f[4].toInt() and 0xFF
        val b = f[5].toInt() and 0xFF
        val idx = ((b shr 4) shl 8) or (f[6].toInt() and 0xFF)
        val slot = (b and FLAG_SLOT) != 0
        require(slot == (plen == 4)) { "slot flag / length mismatch" }
        require(idx < phrases.size) { "phrase index out of range" }
        return Decoded(idx, if (slot) f[7].toInt() and 0xFF else null, f[0].toInt() and 3, f[1].toInt() and 0xFF,
            fp8 == (fingerprint and 0xFF))
    }

    // ------------------------------------------------------------ matching (sender side)

    data class Candidate(val idx: Int, val score: Double, val n: Int?)

    private fun norm(s: String): List<String> {
        val t = java.text.Normalizer.normalize(s, java.text.Normalizer.Form.NFC).lowercase().replace(DIGITS, " ")
        return PUNCT.split(t).filter { it.isNotEmpty() }
    }

    private fun grams(tokens: List<String>, n: Int = 3): Set<String> {
        val g = HashSet<String>()
        for (tok in tokens) {
            val t = " $tok "
            for (i in 0 until maxOf(1, t.length - n + 1)) g += t.substring(i, minOf(i + n, t.length))
        }
        return g
    }

    fun spokenNumber(text: String, lang: String): Int? {
        DIGITS.find(text)?.let { return it.value.toIntOrNull() ?: Int.MAX_VALUE }
        val words = NUMWORDS[lang] ?: return null
        for (tok in norm(text)) words[tok]?.let { return it }
        return null
    }

    fun match(text: String, lang: String, top: Int = 3, threshold: Double = 0.55): List<Candidate> {
        var toks = norm(text)
        if (toks.isEmpty()) return emptyList()
        val n = spokenNumber(text, lang)
        val numwords = NUMWORDS[lang]?.keys ?: emptySet()
        toks = toks.filter { it !in numwords }.ifEmpty { toks }
        val tset = toks.toSet(); val tgr = grams(toks)
        val out = ArrayList<Candidate>()
        phrases.forEachIndexed { idx, entry ->
            val ptoks = norm(entry[lang]!!.replace(SLOT, ""))
            val pset = ptoks.toSet(); val pgr = grams(ptoks)
            val jTok = (tset intersect pset).size.toDouble() / (tset union pset).size
            val jGr = (tgr intersect pgr).size.toDouble() / maxOf(1, (tgr union pgr).size)
            val score = 0.5 * jTok + 0.5 * jGr
            if (score >= threshold) {
                val needsSlot = entry["en"]!!.contains(SLOT)
                if (needsSlot && (n == null || n > 255)) return@forEachIndexed
                out += Candidate(idx, Math.round(score * 1000) / 1000.0, if (needsSlot) n else null)
            }
        }
        return out.sortedByDescending { it.score }.take(top)
    }

    companion object {
        const val PHRASE_LANG = 15
        const val FLAG_SLOT = 1
        const val SLOT = "{n}"
        private val DIGITS = Regex("\\d+")
        private val PUNCT = Regex("[\\s.,!?।॥;:\\-'\"()]+")

        fun isPhraseFrame(f: ByteArray) = f.size >= 6 && ((f[0].toInt() shr 2) and 0xF) == PHRASE_LANG

        private fun w(vararg p: Pair<String, Int>) = mapOf(*p)
        val NUMWORDS: Map<String, Map<String, Int>> = mapOf(
            "en" to w("zero" to 0, "one" to 1, "two" to 2, "three" to 3, "four" to 4, "five" to 5, "six" to 6, "seven" to 7, "eight" to 8, "nine" to 9, "ten" to 10, "twenty" to 20, "fifty" to 50, "hundred" to 100),
            "hi" to w("शून्य" to 0, "एक" to 1, "दो" to 2, "तीन" to 3, "चार" to 4, "पाँच" to 5, "पांच" to 5, "छह" to 6, "छः" to 6, "सात" to 7, "आठ" to 8, "नौ" to 9, "दस" to 10, "बीस" to 20, "पचास" to 50, "सौ" to 100),
            "bn" to w("শূন্য" to 0, "এক" to 1, "দুই" to 2, "তিন" to 3, "চার" to 4, "পাঁচ" to 5, "ছয়" to 6, "সাত" to 7, "আট" to 8, "নয়" to 9, "দশ" to 10, "বিশ" to 20, "পঞ্চাশ" to 50, "একশো" to 100),
            "ta" to w("பூஜ்யம்" to 0, "ஒன்று" to 1, "இரண்டு" to 2, "மூன்று" to 3, "நான்கு" to 4, "ஐந்து" to 5, "ஆறு" to 6, "ஏழு" to 7, "எட்டு" to 8, "ஒன்பது" to 9, "பத்து" to 10, "இருபது" to 20, "ஐம்பது" to 50, "நூறு" to 100),
            "te" to w("సున్నా" to 0, "ఒకటి" to 1, "రెండు" to 2, "మూడు" to 3, "నాలుగు" to 4, "ఐదు" to 5, "ఆరు" to 6, "ఏడు" to 7, "ఎనిమిది" to 8, "తొమ్మిది" to 9, "పది" to 10, "ఇరవై" to 20, "యాభై" to 50, "వంద" to 100),
            "gu" to w("શૂન્ય" to 0, "એક" to 1, "બે" to 2, "ત્રણ" to 3, "ચાર" to 4, "પાંચ" to 5, "છ" to 6, "સાત" to 7, "આઠ" to 8, "નવ" to 9, "દસ" to 10, "વીસ" to 20, "પચાસ" to 50, "સો" to 100),
            "mr" to w("शून्य" to 0, "एक" to 1, "दोन" to 2, "तीन" to 3, "चार" to 4, "पाच" to 5, "सहा" to 6, "सात" to 7, "आठ" to 8, "नऊ" to 9, "दहा" to 10, "वीस" to 20, "पन्नास" to 50, "शंभर" to 100),
            "kn" to w("ಸೊನ್ನೆ" to 0, "ಒಂದು" to 1, "ಎರಡು" to 2, "ಮೂರು" to 3, "ನಾಲ್ಕು" to 4, "ಐದು" to 5, "ಆರು" to 6, "ಏಳು" to 7, "ಎಂಟು" to 8, "ಒಂಬತ್ತು" to 9, "ಹತ್ತು" to 10, "ಇಪ್ಪತ್ತು" to 20, "ಐವತ್ತು" to 50, "ನೂರು" to 100),
            "ml" to w("പൂജ്യം" to 0, "ഒന്ന്" to 1, "രണ്ട്" to 2, "മൂന്ന്" to 3, "നാല്" to 4, "അഞ്ച്" to 5, "ആറ്" to 6, "ഏഴ്" to 7, "എട്ട്" to 8, "ഒമ്പത്" to 9, "പത്ത്" to 10, "ഇരുപത്" to 20, "അമ്പത്" to 50, "നൂറ്" to 100),
            "or" to w("ଶୂନ୍ୟ" to 0, "ଏକ" to 1, "ଦୁଇ" to 2, "ତିନି" to 3, "ଚାରି" to 4, "ପାଞ୍ଚ" to 5, "ଛଅ" to 6, "ସାତ" to 7, "ଆଠ" to 8, "ନଅ" to 9, "ଦଶ" to 10, "କୋଡ଼ିଏ" to 20, "ପଚାଶ" to 50, "ଶହେ" to 100),
        )
    }
}
