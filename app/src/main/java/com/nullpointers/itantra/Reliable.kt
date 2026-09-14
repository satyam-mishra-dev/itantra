package com.nullpointers.itantra

/**
 * Kotlin port of p0/reliable.py — reliable delivery on top of iTantra frames. Replaces Arq.kt.
 *
 * Delivery control frames reuse the ACK priority class with a 1-byte payload, so they can never be
 * mistaken for a roll-call answer (3-byte payload) or the old empty-VarnaCode ACK:
 *     ACK  : [lang<<2|ACK, seq, 0x00, 0x01, 0x00, crc16]   (7 bytes)
 *     NACK : [lang<<2|ACK, seq, 0x00, 0x01, 0x01, crc16]   (7 bytes)
 *
 * Sender: NORMAL 3 tries / ALERT 5 (bounded) or tries=null = never give up with ×2 backoff capped at
 * 8×RTO (store-and-forward; frames wait while no peer is connected and flush() on reconnect).
 * ALERT jumps the queue. A NACK resends immediately without spending a try.
 * Receiver: ACKs every data frame (duplicates too — the first ACK may have been lost), dedups by
 * (seq, frame CRC) in a 64-entry window — seq alone would drop a restarted peer's first message,
 * which reuses seq 0 — and NACKs forward gaps ≤ 8.
 *
 * Pure Kotlin, clock-injected, no Android imports; byte-identical to the Python reference.
 */
object ReliableCtrl {
    const val ACK_BYTE = 0
    const val NACK_BYTE = 1

    fun make(seq: Int, kind: Int, lang: String = "hi"): ByteArray {
        val body = byteArrayOf(
            ((VarnaCode.LANGS.indexOf(lang) shl 2) or Frame.ACK).toByte(),
            (seq and 0xFF).toByte(), 0, 1, kind.toByte()
        )
        val crc = Frame.crc16(body)
        return body + byteArrayOf((crc ushr 8).toByte(), (crc and 0xFF).toByte())
    }

    /** (seq, kind) for a delivery ACK/NACK, else null — other ACK-class frames are legitimate. */
    fun parse(f: ByteArray): Pair<Int, Int>? {
        if (f.size != 7) return null
        val crc = ((f[5].toInt() and 0xFF) shl 8) or (f[6].toInt() and 0xFF)
        if (Frame.crc16(f, 5) != crc) return null
        val b0 = f[0].toInt() and 0xFF
        val plen = ((f[2].toInt() and 0xFF) shl 8) or (f[3].toInt() and 0xFF)
        val kind = f[4].toInt() and 0xFF
        if ((b0 and 3) != Frame.ACK || plen != 1 || kind > NACK_BYTE) return null
        return Pair(f[1].toInt() and 0xFF, kind)
    }
}

class ReliableSender(
    private val now: () -> Long = System::currentTimeMillis,
    private val rtoMs: Long = 800,
    /** tries per priority; null = never give up (store-and-forward). */
    private val tries: Map<Int, Int?> = mapOf(Frame.NORMAL to 3, Frame.ALERT to 5),
) {
    private class Flight(val frame: ByteArray, val prio: Int, var sent: Long, var tries: Int,
                         var left: Int?, var nack: Boolean = false, var flush: Boolean = false)

    private val queue = ArrayList<Triple<Int, ByteArray, Int>>()   // (seq, frame, prio)
    private val inflight = LinkedHashMap<Int, Flight>()
    private val state = HashMap<Int, String>()
    private var seqCounter = 0
    var retransmits = 0; private set
    var acked: (seq: Int) -> Unit = {}
    var failed: (seq: Int) -> Unit = {}

    val backlog: Int @Synchronized get() = inflight.size + queue.size

    /** Next wire seq, skipping any still in flight or queued — the 1-byte wrap must not clobber a frame. */
    @Synchronized
    fun nextSeq(): Int {
        val busy = inflight.keys + queue.map { it.first }
        repeat(256) {
            val s = seqCounter++ and 0xFF
            if (s !in busy) return s
        }
        return seqCounter++ and 0xFF   // 256 unacked: the peer has been gone half a conversation
    }

    @Synchronized
    fun send(frame: ByteArray, prio: Int = Frame.NORMAL) {
        val seq = frame[1].toInt() and 0xFF
        val item = Triple(seq, frame, prio)
        if (prio == Frame.ALERT) queue.add(0, item) else queue.add(item)
        state[seq] = "queued"
    }

    /** Feed every received frame; true if it was a delivery ACK/NACK (consumed). */
    @Synchronized
    fun onCtrl(frame: ByteArray): Boolean {
        val (seq, kind) = ReliableCtrl.parse(frame) ?: return false
        val f = inflight[seq] ?: return true
        if (kind == ReliableCtrl.ACK_BYTE) {
            inflight.remove(seq); state[seq] = "acked"; acked(seq)
        } else f.nack = true
        return true
    }

    /** Frames to put on the wire right now (retransmits first, oldest first, then fresh sends). */
    @Synchronized
    fun tick(): List<ByteArray> {
        val t = now()
        val out = ArrayList<ByteArray>()
        for ((seq, f) in inflight.entries.sortedBy { it.value.sent }.toList()) {
            if (f.nack || f.flush) {
                f.nack = false; f.flush = false; f.sent = t; out += f.frame; continue
            }
            val wait = if (f.left == null) rtoMs shl minOf(f.tries - 1, 3) else rtoMs
            if (t - f.sent < wait) continue
            val left = f.left
            if (left != null) {
                if (left <= 0) { inflight.remove(seq); state[seq] = "failed"; failed(seq); continue }
                f.left = left - 1
            }
            f.tries++; f.sent = t; retransmits++; out += f.frame
        }
        while (queue.isNotEmpty()) {
            val (seq, frame, prio) = queue.removeAt(0)
            val budget: Int? = if (tries.containsKey(prio)) tries[prio] else 3   // null = unbounded
            inflight[seq] = Flight(frame, prio, t, 1, budget?.minus(1))
            state[seq] = "sent"
            out += frame
        }
        return out
    }

    /** Peer (re)connected: resend everything in flight on the next tick, no backoff wait. */
    @Synchronized
    fun flush() { for (f in inflight.values) f.flush = true }

    @Synchronized
    fun status(seq: Int): String? = state[seq]
}

class ReliableReceiver(private val lang: String = "hi", private val window: Int = 64) {
    data class Result(val msg: Frame.Msg?, val ctrl: List<ByteArray>)

    private val seen = LinkedHashSet<Int>()   // (seq shl 16) or crc16
    private var last: Int? = null

    private fun key(f: ByteArray) = ((f[1].toInt() and 0xFF) shl 16) or
        (((f[f.size - 2].toInt() and 0xFF) shl 8) or (f[f.size - 1].toInt() and 0xFF))

    private fun remember(k: Int) {
        seen += k
        while (seen.size > window) seen.remove(seen.first())
    }

    /** Data frames only — the caller routes delivery-ctrl and phrase frames first (see MainActivity hook). */
    @Synchronized
    fun ingest(frame: ByteArray, vc: VarnaCode, key: ByteArray? = null): Result {
        if (ReliableCtrl.parse(frame) != null) return Result(null, emptyList())
        val msg = Frame.unpack(vc, frame, key)
        if (msg.prio == Frame.ACK) return Result(msg, emptyList())   // roll-call etc.: not ours to ack
        val ctrl = ArrayList<ByteArray>()
        ctrl += ReliableCtrl.make(msg.seq, ReliableCtrl.ACK_BYTE, lang)
        val k = key(frame)
        if (k in seen) return Result(null, ctrl)
        last?.let { l ->
            val gap = (msg.seq - l - 1) and 0xFF
            if (gap in 1..8) for (k in 1..gap) {
                val missing = (l + k) and 0xFF
                if (seen.none { it shr 16 == missing }) ctrl += ReliableCtrl.make(missing, ReliableCtrl.NACK_BYTE, lang)
            }
        }
        remember(k)
        last = msg.seq
        return Result(msg, ctrl)
    }
}
