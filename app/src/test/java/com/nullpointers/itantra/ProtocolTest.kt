package com.nullpointers.itantra

import org.json.JSONArray
import org.junit.Assert.*
import org.junit.Test

/** Mirrors p0/test_p0.py + python-interop vectors (wire compatibility). */
class ProtocolTest {

    private val vc = VarnaCode(res("/codebooks.json"))

    private fun res(path: String): String =
        javaClass.getResourceAsStream(path)!!.readBytes().decodeToString()

    private val samples = mapOf(
        "en" to "Cyclone alert: move to shelter 12 now!",
        "hi" to "बाढ़ का पानी बढ़ रहा है, तुरंत निकलें।",
        "bn" to "নদীর জল বাড়ছে, এখনই সরে যান।",
        "ta" to "வெள்ளம் உயர்கிறது, உடனே வெளியேறுங்கள்.",
        "te" to "వరద పెరుగుతోంది, వెంటనే బయలుదేరండి.",
        "gu" to "પૂરનું પાણી વધી રહ્યું છે, તરત નીકળો.",
        "mr" to "पुराचे पाणी वाढत आहे, लगेच निघा.",
        "kn" to "ಪ್ರವಾಹದ ನೀರು ಏರುತ್ತಿದೆ, ಕೂಡಲೇ ಹೊರಡಿ.",
        "ml" to "വെള്ളപ്പൊക്കം ഉയരുന്നു, ഉടനെ പുറപ്പെടുക.",
        "or" to "ବନ୍ୟା ପାଣି ବଢୁଛି, ତୁରନ୍ତ ବାହାରନ୍ତୁ।",
    )

    private val edge = listOf("", "🚨🆘", "SOS मदद 108 !!", "mixed মিশ্র கலப்பு", "a".repeat(500), "\n\t  ")

    @Test fun roundTripSamples() {
        for ((lang, text) in samples)
            assertEquals(lang, text, vc.decode(vc.encode(text, lang), lang))
    }

    @Test fun roundTripEdgeCasesAllLangs() {
        for (lang in VarnaCode.LANGS) for (text in edge)
            assertEquals("$lang/$text", text, vc.decode(vc.encode(text, lang), lang))
    }

    @Test fun compressesVsUtf8() {
        for ((lang, text) in samples) {
            val utf8 = text.encodeToByteArray().size
            assertTrue(lang, vc.encode(text, lang).size < utf8)
        }
    }

    @Test fun frameRoundTripAllLangsAndPriorities() {
        var i = 0
        for ((lang, text) in samples) {
            for (prio in listOf(Frame.NORMAL, Frame.ALERT, Frame.ACK)) {
                val m = Frame.unpack(vc, Frame.pack(vc, text, lang, prio, i))
                assertEquals(text, m.text)
                assertEquals(lang, m.lang)
                assertEquals(prio, m.prio)
                assertEquals(i, m.seq)
            }
            i++
        }
    }

    @Test fun everySingleByteCorruptionDetected() {
        val f = Frame.pack(vc, samples.getValue("hi"), "hi", Frame.ALERT, 7)
        for (i in f.indices) {
            val bad = f.copyOf()
            bad[i] = (bad[i].toInt() xor 0xFF).toByte()
            try {
                Frame.unpack(vc, bad)
                fail("corruption at byte $i not detected")
            } catch (_: IllegalArgumentException) { }
        }
    }

    @Test fun shortFrameRejected() {
        try {
            Frame.unpack(vc, byteArrayOf(0, 1))
            fail("short frame accepted")
        } catch (_: IllegalArgumentException) { }
    }

    @Test fun pythonInteropVectors() {
        val arr = JSONArray(res("/testvectors.json"))
        for (i in 0 until arr.length()) {
            val v = arr.getJSONObject(i)
            val bytes = v.getString("hex").chunked(2).map { it.toInt(16).toByte() }.toByteArray()
            val m = Frame.unpack(vc, bytes)
            assertEquals(v.getString("text"), m.text)
            assertEquals(v.getString("lang"), m.lang)
            assertEquals(v.getInt("prio"), m.prio)
            assertEquals(v.getInt("seq"), m.seq)
            // and our own pack must be byte-identical to python's
            val ours = Frame.pack(vc, v.getString("text"), v.getString("lang"), v.getInt("prio"), v.getInt("seq"))
            assertEquals(v.getString("hex"), ours.joinToString("") { "%02x".format(it) })
        }
    }
}
