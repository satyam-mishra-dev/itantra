package com.nullpointers.itantra

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.media.AudioAttributes
import android.media.AudioFocusRequest
import android.media.AudioManager
import android.media.MediaRecorder
import android.os.Build
import android.os.Bundle
import android.speech.tts.TextToSpeech
import android.view.MotionEvent
import android.widget.*
import java.io.File
import java.util.Locale

/**
 * P1 spine: PTT screen. STT is stubbed (mic records while button held — proves
 * the audio path; the typed text is what travels). Received frames are spoken
 * via the platform TextToSpeech as a placeholder until sherpa-onnx lands (P2).
 */
class MainActivity : Activity() {

    private val langCodes = VarnaCode.LANGS
    private val langNames = listOf(
        "English", "हिन्दी", "বাংলা", "தமிழ்", "తెలుగు",
        "ગુજરાતી", "मराठी", "ಕನ್ನಡ", "മലയാളം", "ଓଡ଼ିଆ"
    )
    private val ttsLocales = mapOf(
        "en" to "en_IN", "hi" to "hi_IN", "bn" to "bn_IN", "ta" to "ta_IN", "te" to "te_IN",
        "gu" to "gu_IN", "mr" to "mr_IN", "kn" to "kn_IN", "ml" to "ml_IN", "or" to "or_IN"
    )

    private lateinit var vc: VarnaCode
    private lateinit var transport: NsdTransport
    private lateinit var transcript: TextView
    private lateinit var status: TextView
    private lateinit var langSpinner: Spinner
    private lateinit var input: EditText
    private lateinit var alertBox: CheckBox
    private var tts: TextToSpeech? = null
    private var recorder: MediaRecorder? = null
    private var seq = 0

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        vc = VarnaCode(assets.open("codebooks.json").readBytes().decodeToString())
        transcript = findViewById(R.id.transcript)
        status = findViewById(R.id.status)
        langSpinner = findViewById(R.id.lang)
        input = findViewById(R.id.input)
        alertBox = findViewById(R.id.alert)

        langSpinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, langNames)
        langSpinner.setSelection(1) // Hindi default

        tts = TextToSpeech(this) { if (it == TextToSpeech.SUCCESS) applyTtsLocale() }

        transport = NsdTransport(this, ::onFrameBytes) { s -> runOnUiThread { status.text = s } }
        transport.start()

        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), 1)
        }
        if (Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 2)
        }
        startForegroundService()

        val ptt = findViewById<Button>(R.id.ptt)
        ptt.setOnTouchListener { v, ev ->
            when (ev.action) {
                MotionEvent.ACTION_DOWN -> { startRecording(); v.isPressed = true; true }
                MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                    stopRecording(); v.isPressed = false; v.performClick(); sendCurrentText(); true
                }
                else -> false
            }
        }
    }

    private fun startForegroundService() {
        val i = Intent(this, PttService::class.java)
        if (Build.VERSION.SDK_INT >= 26) startForegroundService(i) else startService(i)
    }

    private fun lang(): String = langCodes[langSpinner.selectedItemPosition]

    private fun applyTtsLocale() {
        val parts = (ttsLocales[lang()] ?: "en_IN").split('_')
        tts?.language = Locale(parts[0], parts[1])
    }

    // P1 stub: record while held (proves mic + service path), payload is the typed text.
    private fun startRecording() {
        try {
            recorder = (if (Build.VERSION.SDK_INT >= 31) MediaRecorder(this) else @Suppress("DEPRECATION") MediaRecorder()).apply {
                setAudioSource(MediaRecorder.AudioSource.MIC)
                setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
                setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
                setOutputFile(File(cacheDir, "ptt.m4a").absolutePath)
                prepare(); start()
            }
            status.text = getString(R.string.recording)
        } catch (e: Exception) {
            status.text = "mic error: ${e.message}"
        }
    }

    private fun stopRecording() {
        try { recorder?.stop() } catch (_: Exception) {}
        try { recorder?.release() } catch (_: Exception) {}
        recorder = null
    }

    private fun sendCurrentText() {
        val text = input.text.toString().ifBlank { return }
        val prio = if (alertBox.isChecked) Frame.ALERT else Frame.NORMAL
        val frame = Frame.pack(vc, text, lang(), prio, seq++)
        Thread {
            val n = transport.send(frame)
            runOnUiThread {
                append("→ [$n peer(s), ${frame.size} B] $text")
                if (n == 0) status.text = getString(R.string.no_peers)
            }
        }.start()
        input.setText("")
    }

    private fun onFrameBytes(bytes: ByteArray) {
        val msg = try { Frame.unpack(vc, bytes) } catch (e: Exception) {
            runOnUiThread { append("✗ bad frame: ${e.message}") }; return
        }
        runOnUiThread {
            append("← [${if (msg.prio == Frame.ALERT) "ALERT" else msg.lang}, ${bytes.size} B] ${msg.text}")
            speak(msg)
        }
    }

    private fun speak(msg: Frame.Msg) {
        val am = getSystemService(AUDIO_SERVICE) as AudioManager
        if (msg.prio == Frame.ALERT) {
            // PS requirement: alerts play at highest volume, non-interruptible.
            am.setStreamVolume(AudioManager.STREAM_MUSIC, am.getStreamMaxVolume(AudioManager.STREAM_MUSIC), 0)
            if (Build.VERSION.SDK_INT >= 26) {
                am.requestAudioFocus(
                    AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_EXCLUSIVE)
                        .setAudioAttributes(
                            AudioAttributes.Builder()
                                .setUsage(AudioAttributes.USAGE_ALARM)
                                .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build()
                        ).build()
                )
            }
        }
        val parts = (ttsLocales[msg.lang] ?: "en_IN").split('_')
        tts?.language = Locale(parts[0], parts[1])
        val repeats = if (msg.prio == Frame.ALERT) 2 else 1
        repeat(repeats) { tts?.speak(msg.text, TextToSpeech.QUEUE_ADD, null, "msg$seq-$it") }
    }

    private fun append(line: String) {
        transcript.append(line + "\n")
    }

    override fun onDestroy() {
        transport.stop()
        tts?.shutdown()
        stopService(Intent(this, PttService::class.java))
        super.onDestroy()
    }
}
