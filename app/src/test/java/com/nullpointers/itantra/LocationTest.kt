package com.nullpointers.itantra

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

/** Frame.kt location trailer vs the Python reference (testvectors_v3.json). */
class LocationTest {
    private val vc = VarnaCode(javaClass.getResourceAsStream("/codebooks.json")!!.readBytes().decodeToString())
    private val vectors = JSONObject(javaClass.getResourceAsStream("/testvectors_v3.json")!!.readBytes().decodeToString())
    private fun hex(b: ByteArray) = b.joinToString("") { "%02x".format(it.toInt() and 0xFF) }
    private fun unhex(s: String) = ByteArray(s.length / 2) { s.substring(it * 2, it * 2 + 2).toInt(16).toByte() }

    @Test fun locationFramesByteIdenticalToPython() {
        val arr = vectors.getJSONArray("location")
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            val key = if (o.isNull("key_hex")) null else unhex(o.getString("key_hex"))
            val f = Frame.pack(vc, o.getString("text"), o.getString("lang"), o.getInt("prio"), o.getInt("seq"),
                key = key, nonce = if (key != null) ByteArray(12) else null,
                prosody = if (o.isNull("prosody")) null else o.getInt("prosody"),
                location = Pair(o.getDouble("lat"), o.getDouble("lon")))
            assertEquals("case $i", o.getString("hex"), hex(f))
            val m = Frame.unpack(vc, unhex(o.getString("hex")), key)
            assertEquals(o.getString("text"), m.text)
            assertEquals(o.getInt("dec_prosody"), m.prosody)
            assertEquals(o.getDouble("dec_lat"), m.location!!.first, 1e-9)
            assertEquals(o.getDouble("dec_lon"), m.location!!.second, 1e-9)
            assertEquals(o.getDouble("lat"), m.location!!.first, 2e-5)   // ~1.3 m quantisation
        }
    }

    @Test fun plainFramesUnchangedAndNoLocation() {
        val f = Frame.pack(vc, "नाव भेजो", "hi", Frame.NORMAL, 3)
        assertNull(Frame.unpack(vc, f).location)
        val p = Frame.pack(vc, "नाव भेजो", "hi", Frame.NORMAL, 3, prosody = 0x26)
        assertNull(Frame.unpack(vc, p).location)
        assertEquals(f.size + 7, Frame.pack(vc, "नाव भेजो", "hi", Frame.NORMAL, 3, location = Pair(1.0, 2.0)).size)
        try { Frame.packLocation(91.0, 0.0); fail() } catch (e: IllegalArgumentException) { }
    }
}
