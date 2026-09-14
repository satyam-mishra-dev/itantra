package com.nullpointers.itantra

import java.util.concurrent.Executors
import java.util.concurrent.ScheduledExecutorService
import java.util.concurrent.TimeUnit
import kotlin.random.Random

/**
 * Kotlin port of p0/relay.py — flood relay as a decorator around the real bearers.
 *
 * Envelope: lang = 14 marker · prio copied from the inner frame · payload = origin(2) · ttl:4|hops:4 · inner.
 * Every node rebroadcasts each new envelope once on every bearer (after a small jitter; ALERT at once)
 * until ttl hits 0. Dedup key = (origin, inner seq, inner CRC). Plain (un-enveloped) frames from
 * legacy peers are delivered as-is and never relayed. Delivery ACKs ride the flood back, so
 * ReliableSender/Receiver work end-to-end across hops without change.
 *
 * Wiring (MainActivity.onCreate):
 *     val relay = RelayTransport(myId, onFrame = ::onFrameBytes)
 *     relay.attach(listOf(NsdTransport(..., onFrame = relay::onReceive), BtTransport(..., onFrame = relay::onReceive)))
 *     transports = listOf(relay)          // everything else keeps calling transports.send(frame)
 * `myId` should be stable per install (e.g. 16 bits of a random UUID persisted in prefs).
 */
object RelayEnvelope {
    const val RELAY_LANG = 14

    fun isEnvelope(b: ByteArray) = b.size >= 9 && ((b[0].toInt() shr 2) and 0xF) == RELAY_LANG

    fun wrap(inner: ByteArray, origin: Int, ttl: Int, hops: Int): ByteArray {
        require(ttl in 0..15 && hops in 0..15 && origin in 0..0xFFFF) { "bad envelope fields" }
        val payload = byteArrayOf((origin ushr 8).toByte(), (origin and 0xFF).toByte(), ((ttl shl 4) or hops).toByte()) + inner
        val body = byteArrayOf(((RELAY_LANG shl 2) or (inner[0].toInt() and 3)).toByte(), inner[1],
            (payload.size ushr 8).toByte(), (payload.size and 0xFF).toByte()) + payload
        val crc = Frame.crc16(body)
        return body + byteArrayOf((crc ushr 8).toByte(), (crc and 0xFF).toByte())
    }

    data class Unwrapped(val inner: ByteArray, val origin: Int, val ttl: Int, val hops: Int)

    fun unwrap(b: ByteArray): Unwrapped {
        require(isEnvelope(b)) { "not an envelope" }
        val crc = ((b[b.size - 2].toInt() and 0xFF) shl 8) or (b[b.size - 1].toInt() and 0xFF)
        require(Frame.crc16(b, b.size - 2) == crc) { "CRC mismatch" }
        val plen = ((b[2].toInt() and 0xFF) shl 8) or (b[3].toInt() and 0xFF)
        require(b.size - 6 == plen && plen >= 9) { "length mismatch" }
        val origin = ((b[4].toInt() and 0xFF) shl 8) or (b[5].toInt() and 0xFF)
        val th = b[6].toInt() and 0xFF
        val inner = b.copyOfRange(7, b.size - 2)
        val icrc = ((inner[inner.size - 2].toInt() and 0xFF) shl 8) or (inner[inner.size - 1].toInt() and 0xFF)
        require(Frame.crc16(inner, inner.size - 2) == icrc) { "inner CRC mismatch" }
        return Unwrapped(inner, origin, th shr 4, th and 0xF)
    }

    fun key(inner: ByteArray, origin: Int): Long =
        (origin.toLong() shl 24) or ((inner[1].toLong() and 0xFF) shl 16) or
            (((inner[inner.size - 2].toLong() and 0xFF) shl 8) or (inner[inner.size - 1].toLong() and 0xFF))
}

class RelayTransport(
    private val myId: Int,
    private val onFrame: (ByteArray) -> Unit,
    private val ttl: Int = DEFAULT_TTL,
    private val rng: Random = Random(myId),
    private val jitterMs: IntRange = 20..120,
    /** null = schedule on an internal single thread; tests inject a fake scheduler via [rebroadcastNow]. */
    private val scheduler: ScheduledExecutorService? = Executors.newSingleThreadScheduledExecutor { r -> Thread(r, "relay").apply { isDaemon = true } },
) : Transport {
    private var bearers: List<Transport> = emptyList()
    private val seen = LinkedHashSet<Long>()
    @Volatile var relayed = 0; private set
    @Volatile var dropped = 0; private set
    /** Test hook: when non-null, rebroadcasts are handed here instead of the scheduler. */
    var rebroadcastNow: ((ByteArray) -> Unit)? = null

    fun attach(transports: List<Transport>) { bearers = transports }

    override fun start() = bearers.forEach { it.start() }
    override fun stop() { bearers.forEach { it.stop() }; scheduler?.shutdownNow() }

    @Synchronized private fun remember(k: Long) { seen += k; while (seen.size > SEEN) seen.remove(seen.first()) }

    /** Local frame out: envelope it and broadcast on every bearer. Returns #peers written (sum). */
    override fun send(frame: ByteArray): Int {
        val env = RelayEnvelope.wrap(frame, myId, ttl, 0)
        remember(RelayEnvelope.key(frame, myId))
        return bearers.sumOf { it.send(env) }
    }

    private fun broadcast(env: ByteArray) { bearers.forEach { it.send(env) } }

    /** Every bearer's onFrame points here. */
    fun onReceive(b: ByteArray) {
        if (!RelayEnvelope.isEnvelope(b)) { onFrame(b); return }          // legacy peer: deliver, never relay
        val u = try { RelayEnvelope.unwrap(b) } catch (e: IllegalArgumentException) { return }
        val k = RelayEnvelope.key(u.inner, u.origin)
        synchronized(this) {
            if (k in seen) { dropped++; return }
            remember(k)
        }
        if (u.ttl > 0) {
            val env = RelayEnvelope.wrap(u.inner, u.origin, u.ttl - 1, u.hops + 1)
            val alert = (u.inner[0].toInt() and 3) == Frame.ALERT
            val delay = if (alert) 0L else rng.nextInt(jitterMs.first, jitterMs.last + 1).toLong()
            relayed++
            rebroadcastNow?.invoke(env) ?: scheduler?.schedule({ broadcast(env) }, delay, TimeUnit.MILLISECONDS)
        }
        onFrame(u.inner)
    }

    companion object {
        const val DEFAULT_TTL = 3
        const val SEEN = 256
    }
}
