package com.nullpointers.itantra

import kotlin.math.log10
import kotlin.math.sqrt

/**
 * Kotlin port of p0/prosody.py — the urgency of a voice, in 1 byte.
 * bits 0-1 urgency · bits 2-3 pitch class · bits 4-5 rate class.
 * Keep thresholds in sync with the Python reference.
 */
object Prosody {
    data class TtsParams(val speed: Float, val gain: Float, val repeats: Int, val urgency: String)

    private const val SR = 16000
    private const val FRAME = 512
    // ponytail: thresholds calibrated on desktop synth voices; tune per-device in Evaluation Mode
    private const val RMS_DB_ELEV = -30.0
    private const val RMS_DB_URGENT = -22.0
    private const val F0_MID = 140.0
    private const val F0_HIGH = 190.0
    private const val F0_VHIGH = 240.0
    private const val RATE_NORM = 2.0
    private const val RATE_FAST = 3.5
    private const val RATE_VFAST = 5.0

    /** 16 kHz mono float PCM (the PTT recording) -> prosody byte. */
    fun encode(x: FloatArray): Int {
        val nf = x.size / FRAME
        if (nf < 4) return 0
        val rms = DoubleArray(nf)
        for (i in 0 until nf) {
            var s = 0.0
            for (j in 0 until FRAME) { val v = x[i * FRAME + j].toDouble(); s += v * v }
            rms[i] = sqrt(s / FRAME)
        }
        val thr = maxOf(rms.max() * 0.15, 1e-4)
        val voiced = BooleanArray(nf) { rms[it] > thr }
        var vSum = 0.0
        var vN = 0
        for (i in 0 until nf) if (voiced[i]) { vSum += rms[i]; vN++ }
        val rmsDb = if (vN > 0) 20 * log10(vSum / vN + 1e-9) else -60.0
        val f0s = ArrayList<Double>()
        for (i in 0 until nf) if (voiced[i]) f0Autocorr(x, i * FRAME)?.let { f0s.add(it) }
        val f0 = if (f0s.isEmpty()) 0.0 else f0s.sorted()[f0s.size / 2]
        var onsets = 0
        for (i in 1 until nf) if (!voiced[i - 1] && voiced[i]) onsets++
        val rate = onsets / (x.size.toDouble() / SR)
        val p = if (f0 < F0_MID) 0 else if (f0 < F0_HIGH) 1 else if (f0 < F0_VHIGH) 2 else 3
        val r = if (rate < RATE_NORM) 0 else if (rate < RATE_FAST) 1 else if (rate < RATE_VFAST) 2 else 3
        val loud = if (rmsDb < RMS_DB_ELEV) 0 else if (rmsDb < RMS_DB_URGENT) 1 else 2
        val u = minOf(loud + (if (p >= 2) 1 else 0) + (if (r >= 2) 1 else 0), 3)
        return u or (p shl 2) or (r shl 4)
    }

    /** Single-frame F0 via autocorrelation, 60–350 Hz band; null = unvoiced. */
    private fun f0Autocorr(x: FloatArray, off: Int): Double? {
        var mean = 0.0
        for (j in 0 until FRAME) mean += x[off + j]
        mean /= FRAME
        val f = DoubleArray(FRAME) { x[off + it] - mean }
        var ac0 = 0.0
        for (j in 0 until FRAME) ac0 += f[j] * f[j]
        if (ac0 <= 0) return null
        val lo = SR / 350
        val hi = minOf(SR / 60, FRAME)
        var best = 0.0
        var bestLag = -1
        for (lag in lo until hi) {
            var s = 0.0
            for (j in 0 until FRAME - lag) s += f[j] * f[j + lag]
            if (s > best) { best = s; bestLag = lag }
        }
        return if (bestLag < 0 || best < 0.3 * ac0) null else SR.toDouble() / bestLag
    }

    /** Receiver side: prosody byte -> TTS speed / playback gain / repeats. */
    fun ttsParams(b: Int): TtsParams = when (b and 3) {
        0 -> TtsParams(0.95f, 1.0f, 1, "CALM")
        1 -> TtsParams(1.05f, 1.2f, 1, "ELEVATED")
        2 -> TtsParams(1.12f, 1.6f, 1, "URGENT")
        else -> TtsParams(1.18f, 2.0f, 2, "PANIC")
    }
}
