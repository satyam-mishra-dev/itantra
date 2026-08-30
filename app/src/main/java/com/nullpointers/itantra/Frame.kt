package com.nullpointers.itantra

/**
 * Kotlin port of p0/frame.py — bearer-agnostic iTantra frame.
 * byte0: ver(2)|lang(4)|prio(2) · byte1: seq · bytes2-3: payload len (BE)
 * payload: VarnaCode bits · last 2: CRC-16/CCITT-FALSE over header+payload.
 */
object Frame {
    const val VER = 0
    const val NORMAL = 0
    const val ALERT = 1
    const val ACK = 2

    data class Msg(val ver: Int, val lang: String, val prio: Int, val seq: Int, val text: String)

    fun crc16(data: ByteArray, len: Int = data.size): Int {
        var crc = 0xFFFF
        for (idx in 0 until len) {
            crc = crc xor ((data[idx].toInt() and 0xFF) shl 8)
            repeat(8) {
                crc = if (crc and 0x8000 != 0) ((crc shl 1) xor 0x1021) and 0xFFFF
                else (crc shl 1) and 0xFFFF
            }
        }
        return crc
    }

    fun pack(vc: VarnaCode, text: String, lang: String, prio: Int = NORMAL, seq: Int = 0): ByteArray {
        val payload = vc.encode(text, lang)
        require(payload.size <= 0xFFFF) { "payload too large" }
        val body = ByteArray(4 + payload.size)
        body[0] = ((VER shl 6) or (VarnaCode.LANGS.indexOf(lang) shl 2) or prio).toByte()
        body[1] = (seq and 0xFF).toByte()
        body[2] = (payload.size ushr 8).toByte()
        body[3] = (payload.size and 0xFF).toByte()
        payload.copyInto(body, 4)
        val crc = crc16(body)
        return body + byteArrayOf((crc ushr 8).toByte(), (crc and 0xFF).toByte())
    }

    fun unpack(vc: VarnaCode, frame: ByteArray): Msg {
        require(frame.size >= 6) { "short frame" }
        val crc = ((frame[frame.size - 2].toInt() and 0xFF) shl 8) or (frame[frame.size - 1].toInt() and 0xFF)
        require(crc16(frame, frame.size - 2) == crc) { "CRC mismatch" }
        val b0 = frame[0].toInt() and 0xFF
        val plen = ((frame[2].toInt() and 0xFF) shl 8) or (frame[3].toInt() and 0xFF)
        require(frame.size - 6 == plen) { "length mismatch" }
        val lang = VarnaCode.LANGS[(b0 shr 2) and 0xF]
        val payload = frame.copyOfRange(4, frame.size - 2)
        return Msg(b0 shr 6, lang, b0 and 3, frame[1].toInt() and 0xFF, vc.decode(payload, lang))
    }
}
