package com.nullpointers.itantra

import android.content.Context
import com.k2fsa.sherpa.onnx.FeatureConfig
import com.k2fsa.sherpa.onnx.OfflineModelConfig
import com.k2fsa.sherpa.onnx.OfflineNemoEncDecCtcModelConfig
import com.k2fsa.sherpa.onnx.OfflineRecognizer
import com.k2fsa.sherpa.onnx.OfflineRecognizerConfig
import com.k2fsa.sherpa.onnx.OfflineTts
import com.k2fsa.sherpa.onnx.OfflineTtsConfig
import com.k2fsa.sherpa.onnx.OfflineTtsModelConfig
import com.k2fsa.sherpa.onnx.OfflineTtsVitsModelConfig
import java.io.File

/**
 * sherpa-onnx wrapper with graceful degradation: a missing/broken model pack
 * yields null and the caller falls back (typed-text STT stub / platform TTS),
 * so the app never hard-crashes without models.
 *
 * Model pack layout (ADB sideload or in-app download, idea doc §7.3):
 *   getExternalFilesDir(null)/models/<lang>/stt/model.onnx + tokens.txt   — IndicConformer int8 (NeMo CTC export)
 *   getExternalFilesDir(null)/models/<lang>/tts/model.onnx + tokens.txt [+ espeak-ng-data/] — Piper/VITS voice
 */
class SpeechEngine(private val ctx: Context) {
    private val stt = HashMap<String, OfflineRecognizer?>()
    private val tts = HashMap<String, OfflineTts?>()

    private fun dir(lang: String, kind: String) = Packs.dir(ctx, lang, kind)

    /** After a pack install: drop the cached "no model" so the next sttFor/ttsFor actually loads it. */
    fun forget(lang: String) { stt.remove(lang); tts.remove(lang) }

    fun sttFor(lang: String): OfflineRecognizer? = stt.getOrPut(lang) {
        val d = dir(lang, "stt")
        val model = File(d, "model.onnx")
        val tokens = File(d, "tokens.txt")
        if (!model.exists() || !tokens.exists()) return@getOrPut null
        try {
            OfflineRecognizer(
                config = OfflineRecognizerConfig(
                    featConfig = FeatureConfig(sampleRate = 16000, featureDim = 80),
                    modelConfig = OfflineModelConfig(
                        nemo = OfflineNemoEncDecCtcModelConfig(model = model.absolutePath),
                        tokens = tokens.absolutePath,
                        numThreads = 2,
                    ),
                )
            )
        } catch (t: Throwable) { null }
    }

    fun ttsFor(lang: String): OfflineTts? = tts.getOrPut(lang) {
        val d = dir(lang, "tts")
        val model = File(d, "model.onnx")
        val tokens = File(d, "tokens.txt")
        if (!model.exists() || !tokens.exists()) return@getOrPut null
        val espeak = File(d, "espeak-ng-data")
        try {
            OfflineTts(
                config = OfflineTtsConfig(
                    model = OfflineTtsModelConfig(
                        vits = OfflineTtsVitsModelConfig(
                            model = model.absolutePath,
                            tokens = tokens.absolutePath,
                            dataDir = if (espeak.isDirectory) espeak.absolutePath else "",
                        ),
                        numThreads = 2,
                    ),
                )
            )
        } catch (t: Throwable) { null }
    }

    /** float PCM 16 kHz mono -> recognized text */
    fun recognize(rec: OfflineRecognizer, samples: FloatArray): String {
        val stream = rec.createStream()
        return try {
            stream.acceptWaveform(samples, 16000)
            rec.decode(stream)
            rec.getResult(stream).text.trim()
        } finally {
            stream.release()
        }
    }
}
