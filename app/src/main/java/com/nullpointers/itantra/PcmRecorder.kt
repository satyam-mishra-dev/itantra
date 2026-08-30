package com.nullpointers.itantra

import android.annotation.SuppressLint
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder

/** 16 kHz mono PCM capture while PTT is held; optional live chunk callback (VAD feed). */
class PcmRecorder(private val onChunk: ((FloatArray) -> Unit)? = null) {
    private val chunks = ArrayList<ShortArray>()
    @Volatile private var running = false
    private var record: AudioRecord? = null
    private var worker: Thread? = null

    @SuppressLint("MissingPermission")
    fun start() {
        val minBuf = AudioRecord.getMinBufferSize(
            16000, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT
        )
        val r = AudioRecord(
            MediaRecorder.AudioSource.VOICE_RECOGNITION, 16000,
            AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, minBuf * 4
        )
        record = r
        if (r.state != AudioRecord.STATE_INITIALIZED) return
        running = true
        r.startRecording()
        worker = Thread {
            val buf = ShortArray(1600)
            while (running) {
                val n = r.read(buf, 0, buf.size)
                if (n > 0) {
                    val copy = buf.copyOf(n)
                    synchronized(chunks) { chunks.add(copy) }
                    onChunk?.invoke(FloatArray(n) { copy[it] / 32768f })
                }
            }
        }.also { it.start() }
    }

    fun stop(): FloatArray {
        running = false
        worker?.join(300)
        try { record?.stop() } catch (_: Exception) {}
        record?.release()
        synchronized(chunks) {
            val total = chunks.sumOf { it.size }
            val out = FloatArray(total)
            var i = 0
            for (c in chunks) for (s in c) out[i++] = s / 32768f
            return out
        }
    }
}
