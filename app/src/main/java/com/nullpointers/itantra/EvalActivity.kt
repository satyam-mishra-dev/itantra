package com.nullpointers.itantra

import android.Manifest
import android.app.Activity
import android.content.pm.PackageManager
import android.os.Bundle
import android.os.SystemClock
import android.view.MotionEvent
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.Spinner
import android.widget.TextView
import java.io.File

/** Cross-activity stat bridge (written by MainActivity's receive path). */
object LastStats {
    @Volatile var ttsFirstAudioMs: Long = -1
}

/**
 * Evaluation Mode — the rubric measured live on stage (idea doc §6.3):
 * reference-sentence CER/WER (CER is the honest Indic metric), per-utterance
 * RTF, receive→first-audio, model pack inventory, idle-CPU sampling.
 */
class EvalActivity : Activity() {

    private val refs = mapOf(
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
    private val langNames = listOf(
        "English", "हिन्दी", "বাংলা", "தமிழ்", "తెలుగు",
        "ગુજરાતી", "मराठी", "ಕನ್ನಡ", "മലയാളം", "ଓଡ଼ିଆ"
    )

    private lateinit var speech: SpeechEngine
    private lateinit var refText: TextView
    private lateinit var result: TextView
    private lateinit var packs: TextView
    private lateinit var cpu: TextView
    private lateinit var spinner: Spinner
    private lateinit var cerVal: TextView
    private lateinit var werVal: TextView
    private lateinit var rtfVal: TextView
    private lateinit var ttsVal: TextView
    private var pcm: PcmRecorder? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_eval)
        speech = SpeechEngine(this)
        refText = findViewById(R.id.refSentence)
        result = findViewById(R.id.evalResult)
        packs = findViewById(R.id.packStatus)
        cpu = findViewById(R.id.cpuStatus)
        spinner = findViewById(R.id.evalLang)
        cerVal = findViewById(R.id.cerVal)
        werVal = findViewById(R.id.werVal)
        rtfVal = findViewById(R.id.rtfVal)
        ttsVal = findViewById(R.id.ttsVal)
        if (LastStats.ttsFirstAudioMs >= 0) ttsVal.text = "${LastStats.ttsFirstAudioMs} ms"

        spinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, langNames)
        spinner.setSelection(1)
        spinner.onItemSelectedListener = object : android.widget.AdapterView.OnItemSelectedListener {
            override fun onItemSelected(p: android.widget.AdapterView<*>?, v: android.view.View?, pos: Int, id: Long) {
                refText.text = refs.getValue(VarnaCode.LANGS[pos])
            }
            override fun onNothingSelected(p: android.widget.AdapterView<*>?) {}
        }
        refText.text = refs.getValue("hi")

        renderPacks()

        findViewById<Button>(R.id.cpuSample).setOnClickListener { sampleIdleCpu() }

        findViewById<Button>(R.id.readPtt).setOnTouchListener { v, ev ->
            when (ev.action) {
                MotionEvent.ACTION_DOWN -> {
                    if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
                        pcm = PcmRecorder().also { it.start() }
                        result.text = getString(R.string.recording)
                    }
                    v.isPressed = true; true
                }
                MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                    v.isPressed = false; v.performClick(); score(); true
                }
                else -> false
            }
        }
    }

    private fun lang(): String = VarnaCode.LANGS[spinner.selectedItemPosition]

    private fun score() {
        val rec = pcm ?: return
        pcm = null
        val samples = rec.stop()
        val l = lang()
        val ref = refs.getValue(l)
        Thread {
            val engine = speech.sttFor(l)
            val text = if (engine != null && samples.isNotEmpty()) {
                val t0 = SystemClock.elapsedRealtime()
                val out = speech.recognize(engine, samples)
                val ms = SystemClock.elapsedRealtime() - t0
                val audioSec = samples.size / 16000.0
                runOnUiThread {
                    cerVal.text = "%.1f%%".format(Cer.cer(ref, out) * 100)
                    werVal.text = "%.1f%%".format(Cer.wer(ref, out) * 100)
                    rtfVal.text = "%.2f".format(ms / 1000.0 / audioSec)
                    if (LastStats.ttsFirstAudioMs >= 0) ttsVal.text = "${LastStats.ttsFirstAudioMs} ms"
                    result.text = "heard: $out\nSTT ${ms} ms for %.1f s of audio".format(audioSec)
                }
                out
            } else {
                runOnUiThread { result.text = getString(R.string.no_stt_pack) }
                null
            }
            text
        }.start()
    }

    private fun renderPacks() {
        val sb = StringBuilder()
        val base = File(getExternalFilesDir(null), "models")
        for ((i, l) in VarnaCode.LANGS.withIndex()) {
            val stt = File(base, "$l/stt/model.onnx")
            val tts = File(base, "$l/tts/model.onnx")
            fun mb(f: File) = if (f.exists()) "✓ %.0fMB".format(f.length() / 1e6) else "✗"
            // Indic glyph widths defeat monospace columns — keep the script name last.
            sb.append("%-3s stt %-8s tts %-8s %s\n".format(l, mb(stt), mb(tts), langNames[i]))
        }
        sb.append("\n").append(getString(R.string.sideload_hint))
        packs.text = sb.toString()
    }

    // ponytail: HZ=100 assumed (standard on Android kernels); calibrate if a device disagrees.
    private fun jiffies(): Long {
        val parts = File("/proc/self/stat").readText().substringAfterLast(") ").split(" ")
        return parts[11].toLong() + parts[12].toLong() // utime + stime (fields 14+15 of full stat)
    }

    private fun sampleIdleCpu() {
        cpu.text = getString(R.string.cpu_sampling)
        Thread {
            val j0 = jiffies(); val t0 = SystemClock.elapsedRealtime()
            Thread.sleep(5000)
            val dj = jiffies() - j0; val dt = SystemClock.elapsedRealtime() - t0
            val pct = dj * 10.0 /* jiffy=10ms */ * 100.0 / dt
            runOnUiThread { cpu.text = "idle CPU (5s sample): %.1f%%".format(pct) }
        }.start()
    }
}
