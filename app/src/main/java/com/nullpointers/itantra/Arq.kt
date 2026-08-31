package com.nullpointers.itantra

/**
 * Stop-and-wait-per-frame ARQ + store-and-forward, bearer-agnostic.
 * TCP/RFCOMM are reliable streams, but LoRa / AFSK / any future datagram bearer is not —
 * and every bearer loses the peer sometimes. Frames stay queued until a peer ACKs their seq;
 * with no peer connected they wait (store-and-forward) and are flushed on reconnect.
 * Pure Kotlin: no Android imports, tested on the JVM with simulated loss.
 *
 * ponytail: first-ACK-wins across peers — a peer that was down when another peer ACKed never gets the frame; per-peer windows when a
 * real multi-peer mesh shows up.
 */
class Arq(
    private val tx: (ByteArray) -> Int,          // write to all bearers; returns #peers written
    private val makeAck: (seq: Int) -> ByteArray,
    private val now: () -> Long = System::currentTimeMillis,
    private val timeoutMs: Long = 1500,          // back-off ×2 per try, capped at 8× — never gives up
) {
    private class Pending(val frame: ByteArray, var lastSent: Long, var tries: Int)

    private val pending = LinkedHashMap<Int, Pending>()
    private val delivered = HashSet<Int>()      // seqs ACKed (for the UI tick)
    var acked: (seq: Int) -> Unit = {}
    var retransmits = 0; private set

    val backlog: Int @Synchronized get() = pending.size

    /** Queue + first attempt. Returns #peers the frame was written to (0 ⇒ queued, not lost). */
    @Synchronized
    fun send(seq: Int, frame: ByteArray): Int {
        val p = Pending(frame, 0, 0)
        pending[seq] = p
        return attempt(seq, p)
    }

    private fun attempt(seq: Int, p: Pending): Int {
        val n = tx(p.frame)
        if (n > 0) { p.lastSent = now(); p.tries++ }
        return n
    }

    @Synchronized
    fun onAck(seq: Int) {
        if (pending.remove(seq) != null) { delivered += seq; acked(seq) }
    }

    /** Receiver side: ACK every non-ACK frame — including duplicates, or a lost ACK loops forever. */
    fun ackFor(prio: Int, seq: Int) {
        if (prio != Frame.ACK) tx(makeAck(seq))
    }

    /** Retransmit due frames. Exponential back-off, capped at 8× timeout; a frame is never dropped. */
    @Synchronized
    fun tick(force: Boolean = false): Int {
        var n = 0
        val t = now()
        for ((seq, p) in pending.entries.toList()) {   // snapshot: an ACK may re-enter onAck() mid-loop
            val due = force || p.tries == 0 || t - p.lastSent >= timeoutMs shl minOf(p.tries, 3)
            if (due && attempt(seq, p) > 0) { n++; if (p.tries > 1) retransmits++ }
        }
        return n
    }

    /** Peer (re)connected: push everything that is waiting. */
    fun flush() = tick(force = true)

    companion object {
        /** Cheap header peek without full decode: (prio, seq). */
        fun peek(frame: ByteArray): Pair<Int, Int> =
            Pair(frame[0].toInt() and 3, frame[1].toInt() and 0xFF)
    }
}
