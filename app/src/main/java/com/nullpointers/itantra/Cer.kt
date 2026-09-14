package com.nullpointers.itantra

/**
 * CER/WER via Levenshtein (jiwer-equivalent). CER is the headline metric for
 * Indic — WER over-punishes agglutinative languages (arXiv 2203.16601).
 */
object Cer {
    fun <T> dist(a: List<T>, b: List<T>): Int {
        var prev = IntArray(b.size + 1) { it }
        for (i in 1..a.size) {
            val cur = IntArray(b.size + 1)
            cur[0] = i
            for (j in 1..b.size) {
                cur[j] = minOf(
                    prev[j] + 1,                                  // deletion
                    cur[j - 1] + 1,                               // insertion
                    prev[j - 1] + if (a[i - 1] == b[j - 1]) 0 else 1 // substitution
                )
            }
            prev = cur
        }
        return prev[b.size]
    }

    /** Same normalisation as p0 norm_dev: punctuation is not a recognition error (STT emits none; the on-phone number was 2× the deck's without this). */
    fun norm(s: String) = s.replace(Regex("[।.,!?\\s]+"), " ").trim()

    fun cer(refRaw: String, hypRaw: String): Double {
        val ref = norm(refRaw); val hyp = norm(hypRaw)
        return if (ref.isEmpty()) if (hyp.isEmpty()) 0.0 else 1.0
        else dist(ref.toList(), hyp.toList()).toDouble() / ref.length
    }

    fun wer(ref: String, hyp: String): Double {
        val r = norm(ref).split(" ").filter { it.isNotEmpty() }
        val h = norm(hyp).split(" ").filter { it.isNotEmpty() }
        return if (r.isEmpty()) if (h.isEmpty()) 0.0 else 1.0
        else dist(r, h).toDouble() / r.size
    }
}
