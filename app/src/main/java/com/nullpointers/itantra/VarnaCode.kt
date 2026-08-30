package com.nullpointers.itantra

import org.json.JSONObject

/**
 * Kotlin port of p0/varnacode.py — per-language Huffman coder with bigram
 * symbols and a 21-bit codepoint escape. Codebooks come from
 * assets/codebooks.json, exported by tools/export_codebooks.py so the wire
 * format is bit-identical to the Python reference.
 */
class VarnaCode(json: String) {

    private class Book(val enc: Map<String, String>, val esc: String, val eof: String) {
        val dec: Map<String, String> = enc.entries.associate { (sym, bits) -> bits to sym }
    }

    private val books = HashMap<String, Book>()

    init {
        val root = JSONObject(json)
        val bk = root.getJSONObject("books")
        for (lang in bk.keys()) {
            val b = bk.getJSONObject(lang)
            val sym = b.getJSONObject("sym")
            val enc = HashMap<String, String>()
            for (k in sym.keys()) enc[k] = sym.getString(k)
            books[lang] = Book(enc, b.getString("esc"), b.getString("eof"))
        }
    }

    companion object {
        // Wire order — must match p0/varnacode.py LANGS
        val LANGS = listOf("en", "hi", "bn", "ta", "te", "gu", "mr", "kn", "ml", "or")
    }

    private fun book(lang: String): Book =
        books[lang] ?: throw IllegalArgumentException("no codebook for $lang")

    fun encode(text: String, lang: String): ByteArray {
        val b = book(lang)
        val bits = StringBuilder()
        var i = 0
        while (i < text.length) {
            // ponytail: mirrors python's greedy bigram check exactly, incl. the 99-penalty for missing singles
            if (i + 1 < text.length) {
                val pair = text.substring(i, i + 2)
                val pc = b.enc[pair]
                if (pc != null) {
                    val c1 = b.enc[text[i].toString()]?.length ?: 99
                    val c2 = b.enc[text[i + 1].toString()]?.length ?: 99
                    if (pc.length < c1 + c2) {
                        bits.append(pc); i += 2; continue
                    }
                }
            }
            val ch = text[i].toString()
            val c = b.enc[ch]
            if (c != null) bits.append(c)
            else {
                bits.append(b.esc)
                bits.append(text[i].code.toString(2).padStart(21, '0'))
            }
            i += 1
        }
        bits.append(b.eof)
        while (bits.length % 8 != 0) bits.append('0')
        val out = ByteArray(bits.length / 8)
        for (j in out.indices) out[j] = bits.substring(j * 8, j * 8 + 8).toInt(2).toByte()
        return out
    }

    fun decode(data: ByteArray, lang: String): String {
        val b = book(lang)
        val bits = StringBuilder(data.size * 8)
        for (byte in data) bits.append(Integer.toBinaryString((byte.toInt() and 0xFF) or 0x100).substring(1))
        val out = StringBuilder()
        val buf = StringBuilder()
        var i = 0
        while (i < bits.length) {
            buf.append(bits[i]); i += 1
            val s = buf.toString()
            if (s == b.eof) break
            if (s == b.esc) {
                out.append(bits.substring(i, i + 21).toInt(2).toChar())
                i += 21; buf.setLength(0); continue
            }
            val sym = b.dec[s] ?: continue
            out.append(sym); buf.setLength(0)
        }
        return out.toString()
    }
}
