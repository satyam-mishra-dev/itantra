package com.nullpointers.itantra

import java.io.DataInputStream

/** A bearer for iTantra frames. Impls: NsdTransport (Wi-Fi/TCP), BtTransport (RFCOMM). */
interface Transport {
    fun start()
    /** @return number of peers the frame was written to */
    fun send(frame: ByteArray): Int
    fun stop()
}

/** Shared read loop: frames are self-delimiting (len at bytes 2-3). Throws on disconnect. */
fun pumpFrames(din: DataInputStream, onFrame: (ByteArray) -> Unit): Nothing {
    val hdr = ByteArray(4)
    while (true) {
        din.readFully(hdr)
        val plen = ((hdr[2].toInt() and 0xFF) shl 8) or (hdr[3].toInt() and 0xFF)
        val rest = ByteArray(plen + 2)
        din.readFully(rest)
        onFrame(hdr + rest)
    }
}
