package com.nullpointers.itantra

import org.junit.Assert.*
import org.junit.Test
import java.io.ByteArrayInputStream
import java.io.DataInputStream
import java.io.EOFException

/** The shared read loop every bearer uses: frames are self-delimiting by the header length. */
class TransportTest {
    private val vc = VarnaCode(javaClass.getResourceAsStream("/codebooks.json")!!.readBytes().decodeToString())

    @Test fun splitsBackToBackFramesAndStopsAtEof() {
        val f1 = Frame.pack(vc, "पानी बढ़ रहा है", "hi", Frame.NORMAL, 1)
        val f2 = Frame.pack(vc, "", "hi", Frame.ACK, 1)          // 9-byte ACK
        val f3 = Frame.pack(vc, "Cyclone landfall in 2 hours", "en", Frame.ALERT, 2)
        val stream = DataInputStream(ByteArrayInputStream(f1 + f2 + f3))
        val got = mutableListOf<ByteArray>()
        try { pumpFrames(stream) { got += it } } catch (_: EOFException) { }
        assertEquals(3, got.size)
        assertArrayEquals(f1, got[0]); assertArrayEquals(f2, got[1]); assertArrayEquals(f3, got[2])
        assertEquals(Frame.ACK, Arq.peek(got[1]).first)
        assertEquals(2, Arq.peek(got[2]).second)
    }

    @Test fun truncatedFrameNeverDelivered() {
        val f = Frame.pack(vc, "Send boats to ward 7", "en", Frame.NORMAL, 9)
        val got = mutableListOf<ByteArray>()
        try { pumpFrames(DataInputStream(ByteArrayInputStream(f.copyOf(f.size - 3)))) { got += it } }
        catch (_: EOFException) { }
        assertTrue("partial frame must not surface", got.isEmpty())
    }
}
