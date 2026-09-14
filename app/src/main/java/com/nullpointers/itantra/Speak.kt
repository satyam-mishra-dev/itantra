package com.nullpointers.itantra

/**
 * Kotlin port of p0/speak.py — far-end speech policy.
 *
 * Normalise: danda/punctuation → clauses (Piper otherwise says "पूर्णविराम" aloud), Indian-grouped
 * numbers → lakh/crore words in all 10 languages, unit abbreviations, acronyms spelled out.
 * SpeakQueue: clause-level scheduler. An ALERT arriving mid-message takes over at the next clause
 * boundary, the interrupted message resumes at its clause afterwards, alerts play twice.
 *
 * Hook (MainActivity, single-thread `playback` executor): instead of speaking `text` whole,
 *     queue.enqueue(text, lang, alert = prio == Frame.ALERT)
 *     while (true) { val c = queue.next() ?: break; speak(c.clause, c.lang, c.gain) }
 * `gain >= SpeakQueue.ALERT_GAIN` ⇒ route to STREAM_ALARM at max volume, restore afterwards.
 * Pure Kotlin, no Android imports.
 */
object Normalise {
    private val UNITS = mapOf(
        "en" to Triple("thousand", "lakh", "crore"),
        "hi" to Triple("हज़ार", "लाख", "करोड़"),
        "bn" to Triple("হাজার", "লাখ", "কোটি"),
        "ta" to Triple("ஆயிரம்", "லட்சம்", "கோடி"),
        "te" to Triple("వేలు", "లక్షలు", "కోట్లు"),
        "gu" to Triple("હજાર", "લાખ", "કરોડ"),
        "mr" to Triple("हजार", "लाख", "कोटी"),
        "kn" to Triple("ಸಾವಿರ", "ಲಕ್ಷ", "ಕೋಟಿ"),
        "ml" to Triple("ആയിരം", "ലക്ഷം", "കോടി"),
        "or" to Triple("ହଜାର", "ଲକ୍ଷ", "କୋଟି"),
    )
    private val ABBR = mapOf(
        "en" to mapOf("km" to "kilometre", "kg" to "kilogram", "hrs" to "hours", "hr" to "hour", "min" to "minutes", "ft" to "feet"),
        "hi" to mapOf("km" to "किलोमीटर", "kg" to "किलो", "hrs" to "घंटे", "hr" to "घंटा", "min" to "मिनट", "ft" to "फ़ीट"),
        "mr" to mapOf("km" to "किलोमीटर", "kg" to "किलो", "hrs" to "तास", "hr" to "तास", "min" to "मिनिटे", "ft" to "फूट"),
        "bn" to mapOf("km" to "কিলোমিটার", "kg" to "কেজি", "hrs" to "ঘণ্টা", "hr" to "ঘণ্টা", "min" to "মিনিট", "ft" to "ফুট"),
    )
    private val ACRONYM = Regex("\\b([A-Z]{2,6})\\b")
    private val INDIAN_NUMBER = Regex("\\d{1,2}(?:,\\d{2})*,\\d{3}|\\d{4,}")
    private val CLAUSE_END = Regex("[।॥.!?]+\\s*|\\n+")
    private val SOFT_BREAK = Regex("[,;:،]\\s*")
    const val MAX_CLAUSE = 90

    fun indianNumberWords(n: Long, lang: String): String {
        val (thou, lakh, crore) = UNITS[lang] ?: UNITS["en"]!!
        if (n < 1000) return n.toString()
        val parts = ArrayList<String>()
        val c = n / 10_000_000; var rest = n % 10_000_000
        val l = rest / 100_000; rest %= 100_000
        val t = rest / 1000; rest %= 1000
        if (c > 0) parts += "$c $crore"
        if (l > 0) parts += "$l $lakh"
        if (t > 0) parts += "$t $thou"
        if (rest > 0) parts += rest.toString()
        return parts.joinToString(" ")
    }

    fun text(text: String, lang: String): String {
        var s = text
        ABBR[lang]?.let { abbr ->
            val re = Regex("\\b(" + abbr.keys.joinToString("|") { Regex.escape(it) } + ")\\b")
            s = re.replace(s) { abbr[it.groupValues[1]]!! }
        }
        s = INDIAN_NUMBER.replace(s) { indianNumberWords(it.value.replace(",", "").toLong(), lang) }
        s = ACRONYM.replace(s) { it.groupValues[1].toCharArray().joinToString(" ") }
        return s
    }

    fun clauses(text: String): List<String> {
        val out = ArrayList<String>()
        for (raw in CLAUSE_END.split(text)) {
            val piece = raw.trim()
            if (piece.isEmpty()) continue
            if (piece.length <= MAX_CLAUSE) { out += piece; continue }
            var buf = ""
            for (subRaw in SOFT_BREAK.split(piece)) {
                val sub = subRaw.trim()
                if (sub.isEmpty()) continue
                if (buf.isNotEmpty() && buf.length + sub.length + 1 > MAX_CLAUSE) { out += buf; buf = sub }
                else buf = if (buf.isEmpty()) sub else "$buf, $sub"
            }
            if (buf.isNotEmpty()) out += buf
        }
        return out
    }

    fun normalise(text: String, lang: String): List<String> {
        require(lang in VarnaCode.LANGS) { "unknown lang $lang" }
        return clauses(text(text, lang))
    }
}

class SpeakQueue {
    data class Item(val msgId: Any, val lang: String, val clause: String, val alert: Boolean,
                    val gain: Float, val replay: Boolean)

    private class Msg(val msgId: Any, val lang: String, var clauses: MutableList<String>, val gain: Float,
                      val alert: Boolean, var replaysLeft: Int, val full: List<String>)

    private val normal = ArrayList<Msg>()
    private val alerts = ArrayList<Msg>()
    private var n = 0

    @Synchronized
    fun enqueue(text: String, lang: String, alert: Boolean = false, gain: Float = 1f, msgId: Any? = null): Any? {
        val clauses = Normalise.normalise(text, lang)
        if (clauses.isEmpty()) return null
        n++
        val id = msgId ?: n
        val m = Msg(id, lang, clauses.toMutableList(), gain, alert, if (alert) ALERT_REPLAYS else 0, clauses)
        (if (alert) alerts else normal).add(m)
        return id
    }

    private fun pop(m: Msg): Item {
        val clause = m.clauses.removeAt(0)
        return Item(m.msgId, m.lang, clause, m.alert, if (m.alert) ALERT_GAIN else m.gain,
            m.alert && m.replaysLeft < ALERT_REPLAYS)
    }

    /** Next clause to speak, or null when idle. Alerts first; a cut NORMAL message resumes at its clause. */
    @Synchronized
    fun next(): Item? {
        if (alerts.isNotEmpty()) {
            val m = alerts[0]
            val item = pop(m)
            if (m.clauses.isEmpty()) {
                if (m.replaysLeft > 0) { m.replaysLeft--; m.clauses = m.full.toMutableList() } else alerts.removeAt(0)
            }
            return item
        }
        if (normal.isNotEmpty()) {
            val m = normal[0]
            val item = pop(m)
            if (m.clauses.isEmpty()) normal.removeAt(0)
            return item
        }
        return null
    }

    @Synchronized
    fun pending(): Int = normal.sumOf { it.clauses.size } + alerts.sumOf { it.clauses.size + it.full.size * it.replaysLeft }

    /** True if an alert is waiting — check between clauses so a long NORMAL message yields promptly. */
    @Synchronized
    fun alertPending(): Boolean = alerts.isNotEmpty()

    companion object {
        const val ALERT_REPLAYS = 1
        const val ALERT_GAIN = 1.6f
    }
}
