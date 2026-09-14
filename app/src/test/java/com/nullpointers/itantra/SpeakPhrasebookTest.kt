package com.nullpointers.itantra

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

/** Speak.kt and Phrasebook.kt vs the Python reference vectors (testvectors_v3.json). */
class SpeakPhrasebookTest {
    private val vc = VarnaCode(javaClass.getResourceAsStream("/codebooks.json")!!.readBytes().decodeToString())
    private val vectors = JSONObject(javaClass.getResourceAsStream("/testvectors_v3.json")!!.readBytes().decodeToString())
    private val pb = Phrasebook(javaClass.getResourceAsStream("/phrasebook.json")!!.readBytes().decodeToString())
    private fun hex(b: ByteArray) = b.joinToString("") { "%02x".format(it.toInt() and 0xFF) }
    private fun unhex(s: String) = ByteArray(s.length / 2) { s.substring(it * 2, it * 2 + 2).toInt(16).toByte() }
    private fun optInt(o: JSONObject, k: String): Int? = if (o.isNull(k)) null else o.getInt(k)

    // ---------------------------------------------------------------- Normalise

    @Test fun indianNumberWordsMatchPython() {
        val arr = vectors.getJSONArray("numbers")
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            assertEquals(o.getString("text"), Normalise.indianNumberWords(o.getLong("n"), o.getString("lang")))
        }
    }

    @Test fun normaliseClausesMatchPython() {
        val arr = vectors.getJSONArray("normalise")
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            val exp = o.getJSONArray("clauses").let { a -> (0 until a.length()).map { a.getString(it) } }
            assertEquals("case $i", exp, Normalise.normalise(o.getString("text"), o.getString("lang")))
        }
    }

    @Test fun normaliseRejectsUnknownLang() {
        try { Normalise.normalise("x", "xx"); fail() } catch (e: IllegalArgumentException) { }
    }

    // ---------------------------------------------------------------- SpeakQueue

    @Test fun queueTraceMatchesPython() {
        val q = SpeakQueue()
        q.enqueue("एक। दो। तीन।", "hi", msgId = "n")
        val first = q.next()!!
        q.enqueue("सावधान। भागो।", "hi", alert = true, msgId = "a")
        val trace = mutableListOf(listOf(first.msgId.toString(), first.clause, first.alert, first.replay))
        while (true) { val it = q.next() ?: break; trace += listOf(it.msgId.toString(), it.clause, it.alert, it.replay) }
        val exp = vectors.getJSONArray("queue_trace").let { a ->
            (0 until a.length()).map { i -> a.getJSONArray(i).let { r -> listOf(r.getString(0), r.getString(1), r.getBoolean(2), r.getBoolean(3)) } }
        }
        assertEquals(exp, trace)
        assertEquals(0, q.pending()); assertNull(q.next())
    }

    @Test fun alertGainPendingAndFifo() {
        val q = SpeakQueue()
        assertNull(q.enqueue("   ", "hi"))
        q.enqueue("normal", "en", gain = 0.7f)
        q.enqueue("A", "en", alert = true, msgId = 1)
        q.enqueue("B", "en", alert = true, msgId = 2)
        assertTrue(q.alertPending())
        assertEquals(5, q.pending())
        val ids = (1..4).map { q.next()!!.also { assertEquals(SpeakQueue.ALERT_GAIN, it.gain) }.msgId }
        assertEquals(listOf(1, 1, 2, 2), ids)
        assertFalse(q.alertPending())
        val n = q.next()!!; assertFalse(n.alert); assertEquals(0.7f, n.gain)
    }

    // ---------------------------------------------------------------- Phrasebook

    @Test fun fingerprintAndFramesByteIdenticalToPython() {
        assertEquals(vectors.getInt("fingerprint"), pb.fingerprint)
        assertEquals(32, pb.phrases.size)
        val arr = vectors.getJSONArray("phrase")
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            val f = pb.pack(o.getInt("idx"), o.getInt("prio"), o.getInt("seq"), optInt(o, "n"))
            assertEquals(o.getString("hex"), hex(f))
            val d = pb.unpack(unhex(o.getString("hex")))
            assertEquals(o.getInt("idx"), d.idx); assertEquals(optInt(o, "n"), d.n)
            assertEquals(o.getInt("prio"), d.prio); assertEquals(o.getInt("seq"), d.seq); assertTrue(d.fpOk)
        }
    }

    @Test fun renderMatchesPython() {
        val arr = vectors.getJSONArray("render")
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            assertEquals(o.getString("text"), pb.render(o.getInt("idx"), o.getString("lang"), optInt(o, "n")))
        }
    }

    @Test fun phraseFrameValidationAndNoCollision() {
        try { pb.pack(4); fail() } catch (e: IllegalArgumentException) { }
        try { pb.pack(4, n = 300); fail() } catch (e: IllegalArgumentException) { }
        try { pb.pack(999); fail() } catch (e: IllegalArgumentException) { }
        val f = pb.pack(2); f[5] = (f[5].toInt() xor 1).toByte()
        try { pb.unpack(f); fail() } catch (e: IllegalArgumentException) { }
        val g = pb.pack(2); g[4] = (g[4].toInt() xor 0xFF).toByte()
        val crc = Frame.crc16(g, g.size - 2); g[g.size - 2] = (crc ushr 8).toByte(); g[g.size - 1] = (crc and 0xFF).toByte()
        assertFalse(pb.unpack(g).fpOk)
        assertFalse(Phrasebook.isPhraseFrame(Frame.pack(vc, "नाव भेजो", "hi", Frame.NORMAL, 3)))
        assertFalse(Phrasebook.isPhraseFrame(ReliableCtrl.make(1, 0)))
        assertTrue(Phrasebook.isPhraseFrame(pb.pack(2)))
        try { Frame.unpack(vc, pb.pack(2)); fail("frame.unpack must not decode a phrase frame") } catch (e: Exception) { }
    }

    @Test fun matchMatchesPython() {
        val arr = vectors.getJSONArray("match")
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            val exp = o.getJSONArray("cands").let { a ->
                (0 until a.length()).map { j -> a.getJSONArray(j).let { c -> Triple(c.getInt(0), c.getDouble(1), if (c.isNull(2)) null else c.getInt(2)) } }
            }
            val got = pb.match(o.getString("text"), o.getString("lang")).map { Triple(it.idx, it.score, it.n) }
            assertEquals("case ${o.getString("text")}", exp, got)
        }
    }

    @Test fun everyPhraseMatchesItselfInEveryLanguage() {
        for ((idx, p) in pb.phrases.withIndex()) for (l in VarnaCode.LANGS) {
            val m = pb.match(p[l]!!.replace(Phrasebook.SLOT, "3"), l)
            assertTrue("$idx/$l -> $m", m.isNotEmpty() && m[0].idx == idx)
        }
    }

    @Test fun phraseFrameAlwaysSmallerThanText() {
        for (l in VarnaCode.LANGS) for ((idx, p) in pb.phrases.withIndex()) {
            val said = p[l]!!.replace(Phrasebook.SLOT, "7")
            val t = Frame.pack(vc, said, l, Frame.NORMAL, 1).size
            val q = pb.pack(idx, Frame.NORMAL, 1, if (pb.hasSlot(idx)) 7 else null).size
            assertTrue("$l/$idx phrase $q >= text $t", q < t)
        }
    }
}
