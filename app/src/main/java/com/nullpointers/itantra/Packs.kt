package com.nullpointers.itantra

import android.content.Context
import java.io.File
import java.io.FilterInputStream
import java.io.IOException
import java.io.InputStream
import java.net.HttpURLConnection
import java.net.URL
import java.util.zip.ZipInputStream

/**
 * In-app model-pack install — the "sideload with adb" path was the reason users had no
 * voice packs. `<PACK_BASE>/<lang>-<stt|tts>.zip` unzips into files/models/<lang>/<kind>/.
 * Extraction goes to a `.part` dir that is renamed only after a clean EOF, so a killed
 * download never leaves a half pack that SpeechEngine would try (and fail) to load.
 */
object Packs {
    val KINDS = listOf("stt", "tts")

    fun dir(ctx: Context, lang: String, kind: String) = File(ctx.getExternalFilesDir(null), "models/$lang/$kind")
    fun installed(ctx: Context, lang: String, kind: String) =
        File(dir(ctx, lang, kind), "model.onnx").exists() && File(dir(ctx, lang, kind), "tokens.txt").exists()

    /** Blocking — call off the main thread. Throws IOException on network failure; a 404 = no such pack, skipped. */
    fun install(ctx: Context, lang: String, onProgress: (String) -> Unit) {
        for (kind in KINDS) {
            if (installed(ctx, lang, kind)) continue
            val c = URL("${BuildConfig.PACK_BASE}/$lang-$kind.zip").openConnection() as HttpURLConnection
            c.connectTimeout = 15_000; c.readTimeout = 60_000
            if (c.responseCode == 404) { c.disconnect(); continue }
            if (c.responseCode != 200) throw IOException("HTTP ${c.responseCode}")
            val total = c.contentLengthLong
            val dst = dir(ctx, lang, kind)
            val part = File(dst.path + ".part").apply { deleteRecursively(); mkdirs() }
            var last = -1
            val counted = object : FilterInputStream(c.inputStream) {
                var n = 0L
                override fun read(b: ByteArray, off: Int, len: Int): Int = super.read(b, off, len).also {
                    if (it > 0) { n += it; val pct = if (total > 0) (n * 100 / total).toInt() else -1
                        if (pct != last) { last = pct; onProgress("$lang $kind ${if (pct >= 0) "$pct%" else "${n / 1_000_000} MB"}") } }
                }
            }
            ZipInputStream(counted).use { z ->
                while (true) {
                    val e = z.nextEntry ?: break
                    require(!e.name.contains("..")) { "bad zip entry ${e.name}" }   // zip-slip guard
                    val f = File(part, e.name)
                    if (e.isDirectory) { f.mkdirs(); continue }
                    f.parentFile?.mkdirs()
                    f.outputStream().use { z.copyTo(it) }
                }
            }
            c.disconnect()
            dst.deleteRecursively()
            if (!part.renameTo(dst)) throw IOException("rename failed")
        }
        onProgress("done")
    }
}
