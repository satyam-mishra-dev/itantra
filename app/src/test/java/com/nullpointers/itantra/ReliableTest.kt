package com.nullpointers.itantra

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

/** Reliable.kt vs the Python reference (testvectors_v3.json) + state-machine behaviour with a fake clock. */
class ReliableTest {
    private val vc = VarnaCode(javaClass.getResourceAsStream("/codebooks.json")!!.readBytes().decodeToString())
    private val vectors = JSONObject(javaClass.getResourceAsStream("/testvectors_v3.json")!!.readBytes().decodeToString())
    private fun hex(b: ByteArray) = b.joinToString("") { "%02x".format(it.toInt() and 0xFF) }
    private fun unhex(s: String) = ByteArray(s.length / 2) { s.substring(it * 2, it * 2 + 2).toInt(16).toByte() }

    @Test fun ctrlFramesByteIdenticalToPython() {
        val arr = vectors.getJSONArray("ctrl")
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            val f = ReliableCtrl.make(o.getInt("seq"), o.getInt("kind"), o.getString("lang"))
            assertEquals(o.getString("hex"), hex(f))
            assertEquals(Pair(o.getInt("seq"), o.getInt("kind")), ReliableCtrl.parse(unhex(o.getString("hex"))))
        }
    }

    @Test fun ctrlDoesNotCollideWithOtherFrames() {
        val a = ReliableCtrl.make(42, ReliableCtrl.ACK_BYTE)
        assertEquals(7, a.size)
        assertNull(ReliableCtrl.parse(a.copyOf().also { it[6] = (it[6].toInt() xor 1).toByte() }))
        assertNull(ReliableCtrl.parse(Frame.pack(vc, "hi", "hi", Frame.NORMAL, 5)))
        assertNull(ReliableCtrl.parse(Frame.pack(vc, "", "hi", Frame.ACK, 5)))   // old 9-byte Arq ACK
        val ph = Phrasebook(javaClass.getResourceAsStream("/phrasebook.json")!!.readBytes().decodeToString())
        assertNull(ReliableCtrl.parse(ph.pack(2)))
    }

    @Test fun ackStopsRetransmit() {
        var clock = 0L
        val tx = ReliableSender(now = { clock })
        val f = Frame.pack(vc, "ok", "hi", Frame.NORMAL, 9)
        tx.send(f)
        assertEquals(listOf(f).map { hex(it) }, tx.tick().map { hex(it) })
        assertEquals("sent", tx.status(9))
        clock = 500; assertTrue(tx.tick().isEmpty())
        assertTrue(tx.onCtrl(ReliableCtrl.make(9, ReliableCtrl.ACK_BYTE)))
        assertEquals("acked", tx.status(9))
        clock = 5000; assertTrue(tx.tick().isEmpty())
    }

    @Test fun retryBudgetNormalVsAlert_alertJumpsQueue() {
        var clock = 0L
        val tx = ReliableSender(now = { clock })
        val fn = Frame.pack(vc, "n", "hi", Frame.NORMAL, 1)
        val fa = Frame.pack(vc, "a", "hi", Frame.ALERT, 2)
        tx.send(fn, Frame.NORMAL); tx.send(fa, Frame.ALERT)
        assertEquals(listOf(hex(fa), hex(fn)), tx.tick().map { hex(it) })
        val sends = mutableMapOf(1 to 1, 2 to 1)
        repeat(10) { clock += 800; for (f in tx.tick()) sends[f[1].toInt()] = sends[f[1].toInt()]!! + 1 }
        assertEquals(3, sends[1]); assertEquals(5, sends[2])
        assertEquals("failed", tx.status(1)); assertEquals("failed", tx.status(2))
        assertEquals(0, tx.backlog)
    }

    @Test fun nackResendsWithoutSpendingATry() {
        var clock = 0L
        val tx = ReliableSender(now = { clock })
        val f = Frame.pack(vc, "x", "hi", Frame.NORMAL, 4)
        tx.send(f); tx.tick()
        assertTrue(tx.onCtrl(ReliableCtrl.make(4, ReliableCtrl.NACK_BYTE)))
        clock = 100
        assertEquals(listOf(hex(f)), tx.tick().map { hex(it) })
        // budget untouched: still 3 real sends left in total → two more timed retransmits then failed
        var n = 0; repeat(10) { clock += 800; n += tx.tick().size }
        assertEquals(2, n)
    }

    @Test fun storeAndForwardNeverGivesUp_backoffAndFlush() {
        var clock = 0L
        val tx = ReliableSender(now = { clock }, tries = mapOf(Frame.NORMAL to null, Frame.ALERT to null))
        val f = Frame.pack(vc, "sf", "hi", Frame.NORMAL, 20)
        tx.send(f); tx.tick()
        val waits = ArrayList<Long>(); var last = 0L
        for (i in 1..4000) { clock += 100; if (tx.tick().isNotEmpty()) { waits += clock - last; last = clock } }
        assertEquals("sent", tx.status(20)); assertEquals(1, tx.backlog)
        assertEquals(listOf(800L, 1600L, 3200L, 6400L, 6400L), waits.take(5))
        tx.flush(); clock += 100
        assertEquals(listOf(hex(f)), tx.tick().map { hex(it) })
        assertTrue(tx.onCtrl(ReliableCtrl.make(20, ReliableCtrl.ACK_BYTE))); assertEquals("acked", tx.status(20))
    }

    @Test fun nextSeqSkipsInFlight() {
        val tx = ReliableSender(now = { 0L })
        val s0 = tx.nextSeq()
        tx.send(Frame.pack(vc, "a", "hi", Frame.NORMAL, s0)); tx.tick()
        val seen = HashSet<Int>()
        repeat(300) { seen += tx.nextSeq() }
        assertFalse(s0 in seen)
    }

    @Test fun receiverDedupAckAndGapNack() {
        val rx = ReliableReceiver("hi")
        val f1 = Frame.pack(vc, "एक", "hi", Frame.NORMAL, 1)
        val f2 = Frame.pack(vc, "दो", "hi", Frame.NORMAL, 2)
        val f4 = Frame.pack(vc, "चार", "hi", Frame.NORMAL, 4)
        var r = rx.ingest(f1, vc)
        assertEquals("एक", r.msg!!.text); assertEquals(listOf(Pair(1, 0)), r.ctrl.map { ReliableCtrl.parse(it) })
        r = rx.ingest(f1, vc)
        assertNull(r.msg); assertEquals(listOf(Pair(1, 0)), r.ctrl.map { ReliableCtrl.parse(it) })   // dup still acked
        r = rx.ingest(f2, vc); assertEquals(2, r.msg!!.seq); assertEquals(1, r.ctrl.size)
        r = rx.ingest(f4, vc)
        assertEquals(4, r.msg!!.seq); assertEquals(listOf(Pair(4, 0), Pair(3, 1)), r.ctrl.map { ReliableCtrl.parse(it) })
        r = rx.ingest(Frame.pack(vc, "तीन", "hi", Frame.NORMAL, 3), vc); assertEquals(3, r.msg!!.seq); assertEquals(1, r.ctrl.size)
    }

    @Test fun receiverSeqWrapAndCtrlPassThrough() {
        val rx = ReliableReceiver()
        rx.ingest(Frame.pack(vc, "a", "hi", Frame.NORMAL, 254), vc)
        val r = rx.ingest(Frame.pack(vc, "b", "hi", Frame.NORMAL, 1), vc)
        assertEquals(listOf(0, 255), r.ctrl.mapNotNull { ReliableCtrl.parse(it) }.filter { it.second == 1 }.map { it.first }.sorted())
        val c = rx.ingest(ReliableCtrl.make(1, 0), vc)
        assertNull(c.msg); assertTrue(c.ctrl.isEmpty())
    }

    @Test fun lossyLinkEndToEnd() {
        var clock = 0L
        val tx = ReliableSender(now = { clock }); val rx = ReliableReceiver("hi")
        val frames = listOf(
            Frame.pack(vc, "पानी बढ़ रहा है", "hi", Frame.ALERT, 1),
            Frame.pack(vc, "गाँव खाली करो", "hi", Frame.NORMAL, 2),
            Frame.pack(vc, "नाव भेजो", "hi", Frame.NORMAL, 3))
        for (f in frames) tx.send(f, f[0].toInt() and 3)
        val dropFirst = mutableSetOf(1, 2)
        val delivered = ArrayList<Int>()
        repeat(12) {
            for (f in tx.tick()) {
                val seq = f[1].toInt() and 0xFF
                if (dropFirst.remove(seq)) continue
                val r = rx.ingest(f, vc)
                r.msg?.let { delivered += it.seq }
                for (c in r.ctrl) tx.onCtrl(c)
            }
            clock += 500
        }
        assertEquals(listOf(1, 2, 3), delivered.sorted())
        assertEquals(3, delivered.size)
        for (s in 1..3) assertEquals("acked", tx.status(s))
    }
}
