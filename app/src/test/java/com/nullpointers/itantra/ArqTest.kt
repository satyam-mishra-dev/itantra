package com.nullpointers.itantra

import org.junit.Assert.*
import org.junit.Test
import kotlin.random.Random

/** ARQ state machine under simulated loss / no-peer, with a fake clock — no Android, no sockets. */
class ArqTest {

    private val vc = VarnaCode(javaClass.getResourceAsStream("/codebooks.json")!!.readBytes().decodeToString())

    /** Two Arq endpoints joined by a lossy pipe. Frames from A go to B's receive path; B ACKs back. */
    private class Link(val loss: Double, seed: Int, val vc: VarnaCode) {
        val rng = Random(seed)
        var clock = 0L
        var peers = 1
        val received = mutableListOf<Int>()          // seqs B saw (after dedupe)
        val seenHashes = HashSet<Int>()
        var sentFrames = 0
        lateinit var a: Arq
        lateinit var b: Arq
        val ackOf = { seq: Int -> Frame.pack(vc, "", "hi", Frame.ACK, seq) }

        init {
            // B side: receive data → ACK (ACK may be lost on the way back)
            b = Arq(tx = { f -> if (rng.nextDouble() >= loss) deliverToA(f); 1 }, makeAck = ackOf, now = { clock })
            a = Arq(tx = { f -> sentFrames++; if (peers > 0 && rng.nextDouble() >= loss) deliverToB(f); peers },
                makeAck = ackOf, now = { clock })
        }

        fun deliverToB(f: ByteArray) {
            val (prio, seq) = Arq.peek(f)
            b.ackFor(prio, seq)                                   // ACK even duplicates
            if (seenHashes.add(f.contentHashCode())) received += seq  // then dedupe for delivery
        }

        fun deliverToA(f: ByteArray) {
            val (prio, seq) = Arq.peek(f)
            if (prio == Frame.ACK) a.onAck(seq)
        }

        fun run(ms: Long) { repeat((ms / 500).toInt()) { clock += 500; a.tick() } }
    }

    private fun frames(n: Int) = (0 until n).map { it to Frame.pack(vc, "sentence $it", "hi", Frame.NORMAL, it) }

    @Test fun losslessUnder30PercentLoss() {
        val l = Link(0.30, 7, vc)
        for ((seq, f) in frames(20)) l.a.send(seq, f)
        l.run(180_000)
        assertEquals("every frame delivered exactly once", (0 until 20).toList(), l.received.sorted())
        assertEquals(20, l.received.size)
        assertEquals(0, l.a.backlog)
        assertTrue("retransmits happened", l.a.retransmits > 0)
    }

    @Test fun noRetransmitsWithoutLoss() {
        val l = Link(0.0, 1, vc)
        for ((seq, f) in frames(5)) l.a.send(seq, f)
        l.run(10_000)
        assertEquals(5, l.sentFrames)
        assertEquals(0, l.a.retransmits)
        assertEquals(0, l.a.backlog)
    }

    @Test fun storeAndForwardUntilPeerAppears() {
        val l = Link(0.0, 2, vc)
        l.peers = 0
        for ((seq, f) in frames(3)) assertEquals(0, l.a.send(seq, f))
        l.run(20_000)
        assertEquals("nothing delivered without a peer", 0, l.received.size)
        assertEquals(3, l.a.backlog)
        l.peers = 1
        l.a.flush()
        l.run(2_000)
        assertEquals(listOf(0, 1, 2), l.received.sorted())
        assertEquals(0, l.a.backlog)
    }

    @Test fun ackedCallbackAndDuplicateAckHarmless() {
        val l = Link(0.0, 3, vc)
        val ticks = mutableListOf<Int>()
        l.a.acked = { ticks += it }
        val (seq, f) = frames(1)[0]
        l.a.send(seq, f)
        l.a.onAck(seq)  // duplicate
        assertEquals(listOf(0), ticks)
    }

    /** The wire seq is one byte. Wrapping onto an unacked frame would drop it silently. */
    @Test fun seqAllocationSkipsFramesStillInFlight() {
        val l = Link(0.0, 8, vc)
        l.peers = 0                                   // nothing gets ACKed: everything stays pending
        val held = (0 until 3).map { l.a.nextSeq() }
        for (s in held) l.a.send(s, Frame.pack(vc, "held $s", "hi", Frame.NORMAL, s))
        assertEquals(listOf(0, 1, 2), held)
        // walk past the 8-bit wrap; the three in flight must never come round again
        val reissued = (0 until 400).map { l.a.nextSeq() }
        assertTrue("wrapped seq collided with a queued frame", reissued.none { it in held })
        assertEquals("every other seq stays available", (3..255).toList(), reissued.toSortedSet().toList())
        assertEquals(0, l.a.saturatedDrops)
        // and the held frames are still there to be flushed
        assertEquals(3, l.a.backlog)
        l.peers = 1
        l.a.flush()
        l.run(2_000)
        assertEquals(listOf(0, 1, 2), l.received.sorted())
    }

    @Test fun backoffCapsRetryRateButNeverGivesUp() {
        val l = Link(1.0, 4, vc) // 100% loss: never ACKed
        l.a.send(0, frames(1)[0].second)
        l.run(120_000)
        // 1.5 + 3 + 6 + 12·k s: ~11 attempts in 120 s, not 240 — and still queued, never dropped
        assertTrue("back-off caps the retry rate: ${l.sentFrames}", l.sentFrames in 8..13)
        assertEquals("still queued, not dropped", 1, l.a.backlog)
    }
}
