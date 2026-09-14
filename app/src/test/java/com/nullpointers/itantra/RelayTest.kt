package com.nullpointers.itantra

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import kotlin.random.Random

/** RelayTransport vs the Python reference (testvectors_v3.json) + A—B—C flood behaviour with fake bearers. */
class RelayTest {
    private val vc = VarnaCode(javaClass.getResourceAsStream("/codebooks.json")!!.readBytes().decodeToString())
    private val vectors = JSONObject(javaClass.getResourceAsStream("/testvectors_v3.json")!!.readBytes().decodeToString())
    private fun hex(b: ByteArray) = b.joinToString("") { "%02x".format(it.toInt() and 0xFF) }
    private fun unhex(s: String) = ByteArray(s.length / 2) { s.substring(it * 2, it * 2 + 2).toInt(16).toByte() }

    @Test fun envelopeByteIdenticalToPython() {
        val arr = vectors.getJSONArray("relay")
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            val inner = unhex(o.getString("inner_hex"))
            val env = RelayEnvelope.wrap(inner, o.getInt("origin"), o.getInt("ttl"), o.getInt("hops"))
            assertEquals(o.getString("env_hex"), hex(env))
            val u = RelayEnvelope.unwrap(unhex(o.getString("env_hex")))
            assertArrayEquals(inner, u.inner); assertEquals(o.getInt("origin"), u.origin)
            assertEquals(o.getInt("ttl"), u.ttl); assertEquals(o.getInt("hops"), u.hops)
            assertEquals(inner[0].toInt() and 3, env[0].toInt() and 3)   // prio peekable
        }
    }

    @Test fun envelopeValidation() {
        val inner = Frame.pack(vc, "x", "hi", Frame.NORMAL, 1)
        try { RelayEnvelope.wrap(inner, 70000, 3, 0); fail() } catch (e: IllegalArgumentException) { }
        try { RelayEnvelope.wrap(inner, 1, 16, 0); fail() } catch (e: IllegalArgumentException) { }
        val env = RelayEnvelope.wrap(inner, 1, 3, 0); env[env.size - 1] = (env[env.size - 1].toInt() xor 1).toByte()
        try { RelayEnvelope.unwrap(env); fail() } catch (e: IllegalArgumentException) { }
        assertFalse(RelayEnvelope.isEnvelope(inner))
        assertFalse(RelayEnvelope.isEnvelope(ReliableCtrl.make(1, 0)))
    }

    /** A fake bearer: send() appends to a shared wire tagged with the sending node; the harness delivers. */
    private class Wire { val q = ArrayDeque<Pair<String, ByteArray>>() }
    private class FakeBearer(val node: String, val wire: Wire) : Transport {
        override fun start() {}; override fun stop() {}
        override fun send(frame: ByteArray): Int { wire.q.addLast(node to frame); return 1 }
    }

    private fun chain(names: List<String>, ttl: Int = 3): Triple<Map<String, RelayTransport>, Map<String, MutableList<ByteArray>>, Wire> {
        val wire = Wire()
        val inbox = names.associateWith { mutableListOf<ByteArray>() }
        val relays = names.mapIndexed { i, n ->
            n to RelayTransport(i + 1, onFrame = { inbox[n]!! += it }, ttl = ttl, rng = Random(i + 1), scheduler = null)
        }.toMap()
        relays.forEach { (n, r) -> r.attach(listOf(FakeBearer(n, wire))); r.rebroadcastNow = { env -> r.attachedSend(env) } }
        return Triple(relays, inbox, wire)
    }

    private fun RelayTransport.attachedSend(env: ByteArray) {
        // rebroadcast goes out on the node's bearers, same as the scheduler path would do
        val f = RelayTransport::class.java.getDeclaredField("bearers").apply { isAccessible = true }
        @Suppress("UNCHECKED_CAST") (f.get(this) as List<Transport>).forEach { it.send(env) }
    }

    private fun pump(names: List<String>, relays: Map<String, RelayTransport>, wire: Wire) {
        while (wire.q.isNotEmpty()) {
            val (src, env) = wire.q.removeFirst()
            val i = names.indexOf(src)
            for (j in listOf(i - 1, i + 1)) if (j in names.indices) relays[names[j]]!!.onReceive(env)
        }
    }

    @Test fun chainDeliversOnceAndTtlStops() {
        val names = listOf("A", "B", "C", "D", "E", "F")
        val (relays, inbox, wire) = chain(names, ttl = 3)
        relays["A"]!!.send(Frame.pack(vc, "एक", "hi", Frame.NORMAL, 1))
        pump(names, relays, wire)
        for (n in listOf("B", "C", "D", "E")) assertEquals(n, listOf("एक"), inbox[n]!!.map { Frame.unpack(vc, it).text })
        assertTrue(inbox["F"]!!.isEmpty()); assertTrue(inbox["A"]!!.isEmpty())
        assertEquals(0, relays["E"]!!.relayed); for (n in listOf("B", "C", "D")) assertEquals(1, relays[n]!!.relayed)
    }

    @Test fun dedupRestartSafeAndLegacyPassthrough() {
        val names = listOf("A", "B")
        val (relays, inbox, wire) = chain(names)
        val old = RelayEnvelope.wrap(Frame.pack(vc, "पुराना", "hi", Frame.NORMAL, 0), 3, 3, 0)
        relays["B"]!!.onReceive(old); relays["B"]!!.onReceive(old)
        assertEquals(1, inbox["B"]!!.size); assertEquals(1, relays["B"]!!.dropped)
        relays["B"]!!.onReceive(RelayEnvelope.wrap(Frame.pack(vc, "नया", "hi", Frame.NORMAL, 0), 3, 3, 0))
        assertEquals(2, inbox["B"]!!.size)
        val relayedBefore = relays["B"]!!.relayed
        val plain = Frame.pack(vc, "legacy", "hi", Frame.NORMAL, 4)
        relays["B"]!!.onReceive(plain)
        assertArrayEquals(plain, inbox["B"]!!.last()); assertEquals(relayedBefore, relays["B"]!!.relayed)
    }

    @Test fun reliableEndToEndAcrossAHop() {
        val names = listOf("A", "B", "C")
        val (relays, inbox, wire) = chain(names)
        var clock = 0L
        val tx = ReliableSender(now = { clock }); val rx = ReliableReceiver("hi")
        val delivered = ArrayList<String>()
        tx.send(Frame.pack(vc, "एक", "hi", Frame.NORMAL, 1)); tx.send(Frame.pack(vc, "दो", "hi", Frame.ALERT, 2), Frame.ALERT)
        repeat(6) {
            for (f in tx.tick()) relays["A"]!!.send(f)
            pump(names, relays, wire)
            for (inner in inbox["C"]!!) { val r = rx.ingest(inner, vc); r.msg?.let { delivered += it.text }; for (c in r.ctrl) relays["C"]!!.send(c) }
            inbox["C"]!!.clear()
            pump(names, relays, wire)
            for (inner in inbox["A"]!!) tx.onCtrl(inner)
            inbox["A"]!!.clear()
            clock += 500
        }
        assertEquals(listOf("एक", "दो"), delivered.sorted())
        assertEquals("acked", tx.status(1)); assertEquals("acked", tx.status(2)); assertEquals(0, tx.retransmits)
    }
}
