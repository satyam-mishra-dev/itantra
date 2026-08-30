package com.nullpointers.itantra

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.media.AudioAttributes
import android.media.AudioFocusRequest
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioTrack
import android.os.Build
import android.os.Bundle
import android.os.SystemClock
import android.speech.tts.TextToSpeech
import android.view.MotionEvent
import android.widget.*
import com.k2fsa.sherpa.onnx.SileroVadModelConfig
import com.k2fsa.sherpa.onnx.Vad
import com.k2fsa.sherpa.onnx.VadModelConfig
import java.util.Locale

/**
 * P3: Silero VAD chunks long PTT holds into sentences — sentence 1 is
 * recognized and transmitted while sentence 2 is still being spoken (the PS's
 * "detect pauses, form sentences, stream instantly"). Dual bearers: Wi-Fi
 * (NSD/TCP) + Bluetooth RFCOMM. Real STT/TTS when model packs exist,
 * typed-text / platform-TTS fallback otherwise.
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
    private lateinit var speech: SpeechEngine
    private lateinit var transports: List<Transport>
    private lateinit var transcript: TextView
    private lateinit var status: TextView
    private lateinit var langSpinner: Spinner
    private lateinit var input: EditText
    private lateinit var alertBox: CheckBox
    private var tts: TextToSpeech? = null
    private var track: AudioTrack? = null
    private var pcm: PcmRecorder? = null
    private var vad: Vad? = null
    private var vadActive = false
    private var pttT0 = 0L
    private var seq = 0

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        vc = VarnaCode(assets.open("codebooks.json").readBytes().decodeToString())
        speech = SpeechEngine(this)
        transcript = findViewById(R.id.transcript)
        status = findViewById(R.id.status)
        langSpinner = findViewById(R.id.lang)
        input = findViewById(R.id.input)
        alertBox = findViewById(R.id.alert)

        langSpinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, langNames)
        langSpinner.setSelection(1) // Hindi default

        tts = TextToSpeech(this) { }
        vad = try {
            Vad(
                assetManager = assets,
                config = VadModelConfig(
                    sileroVadModelConfig = SileroVadModelConfig(
                        model = "silero_vad.onnx",
                        minSilenceDuration = 0.5f,
                        maxSpeechDuration = 15f,
                    ),
                    sampleRate = 16000,
                )
            )
        } catch (t: Throwable) { null }

        transports = listOf(
            NsdTransport(this, ::onFrameBytes) { s -> runOnUiThread { status.text = s } },
            BtTransport(this, ::onFrameBytes) { s -> runOnUiThread { status.text = s } },
        )
        transports.forEach { it.start() }

        val wanted = mutableListOf<String>()
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED)
            wanted += Manifest.permission.RECORD_AUDIO
        if (Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED)
            wanted += Manifest.permission.POST_NOTIFICATIONS
        if (Build.VERSION.SDK_INT >= 31 &&
            checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT) != PackageManager.PERMISSION_GRANTED)
            wanted += Manifest.permission.BLUETOOTH_CONNECT
        if (wanted.isNotEmpty()) requestPermissions(wanted.toTypedArray(), 1)

        val svc = Intent(this, PttService::class.java)
        if (Build.VERSION.SDK_INT >= 26) startForegroundService(svc) else startService(svc)

        findViewById<Button>(R.id.eval).setOnClickListener {
            startActivity(Intent(this, EvalActivity::class.java))
        }

        val ptt = findViewById<Button>(R.id.ptt)
        ptt.setOnTouchListener { v, ev ->
            when (ev.action) {
                MotionEvent.ACTION_DOWN -> { pttDown(); v.isPressed = true; true }
                MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                    v.isPressed = false; v.performClick(); pttUp(); true
                }
                else -> false
            }
        }
    }

    private fun lang(): String = langCodes[langSpinner.selectedItemPosition]

    private fun pttDown() {
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) return
        val l = lang()
        pttT0 = SystemClock.elapsedRealtime()
        // VAD streaming path only makes sense with a real STT engine
        vadActive = vad != null && speech.sttFor(l) != null
        val v = vad
        if (vadActive && v != null) {
            v.reset()
            pcm = PcmRecorder { chunk ->
                synchronized(v) {
                    v.acceptWaveform(chunk)
                    drainVad(v, l)
                }
            }.also { it.start() }
        } else {
            pcm = PcmRecorder().also { it.start() }
        }
        status.text = getString(R.string.recording)
    }

    /** Emit every completed speech segment: recognize + transmit while the button is still held. */
    private fun drainVad(v: Vad, l: String) {
        while (!v.empty()) {
            val seg = v.front().samples
            v.pop()
            Thread {
                val engine = speech.sttFor(l) ?: return@Thread
                val t0 = SystemClock.elapsedRealtime()
                val text = speech.recognize(engine, seg)
                val ms = SystemClock.elapsedRealtime() - t0
                if (text.isNotBlank()) runOnUiThread { send(text, l, ms, seg.size / 16000.0) }
            }.start()
        }
    }

    private fun pttUp() {
        val rec = pcm ?: return
        pcm = null
        val samples = rec.stop()
        val l = lang()
        val v = vad
        if (vadActive && v != null) {
            synchronized(v) { v.flush(); drainVad(v, l) }
            status.text = getString(R.string.sent_vad)
            return
        }
        // fallback: whole-clip decode, or typed text when no model pack
        val t0 = SystemClock.elapsedRealtime()
        Thread {
            val engine = speech.sttFor(l)
            val sttMs: Long
            val text: String
            if (engine != null && samples.isNotEmpty()) {
                val out = speech.recognize(engine, samples)
                sttMs = SystemClock.elapsedRealtime() - t0
                text = out.ifBlank { input.text.toString() }
            } else {
                sttMs = -1
                text = input.text.toString()
            }
            runOnUiThread {
                if (text.isBlank()) { status.text = getString(R.string.nothing_to_send); return@runOnUiThread }
                input.setText("")
                send(text, l, sttMs, samples.size / 16000.0)
            }
        }.start()
    }

    private fun send(text: String, l: String, sttMs: Long, audioSec: Double) {
        val prio = if (alertBox.isChecked) Frame.ALERT else Frame.NORMAL
        val frame = Frame.pack(vc, text, l, prio, seq++)
        Thread {
            val n = transports.sumOf { it.send(frame) }
            runOnUiThread {
                val stt = if (sttMs >= 0)
                    ", stt ${sttMs}ms" + if (audioSec > 0.05) " (RTF %.2f)".format(sttMs / 1000.0 / audioSec) else ""
                else ", typed"
                append("→ [$n peer(s), ${frame.size} B$stt] $text")
                if (n == 0) status.text = getString(R.string.no_peers)
            }
        }.start()
    }

    private fun onFrameBytes(bytes: ByteArray) {
        val tRecv = SystemClock.elapsedRealtime()
        val msg = try { Frame.unpack(vc, bytes) } catch (e: Exception) {
            runOnUiThread { append("✗ bad frame: ${e.message}") }; return
        }
        runOnUiThread { speak(msg, bytes.size, tRecv) }
    }

    private fun speak(msg: Frame.Msg, size: Int, tRecv: Long) {
        val am = getSystemService(AUDIO_SERVICE) as AudioManager
        val alert = msg.prio == Frame.ALERT
        if (alert) {
            am.setStreamVolume(AudioManager.STREAM_MUSIC, am.getStreamMaxVolume(AudioManager.STREAM_MUSIC), 0)
            am.setStreamVolume(AudioManager.STREAM_ALARM, am.getStreamMaxVolume(AudioManager.STREAM_ALARM), 0)
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
        val engine = speech.ttsFor(msg.lang)
        Thread {
            val label: String
            if (engine != null) {
                val audio = engine.generate(msg.text, 0, 1.0f)
                val firstAudioMs = SystemClock.elapsedRealtime() - tRecv
                LastStats.ttsFirstAudioMs = firstAudioMs
                label = "tts-first-audio ${firstAudioMs}ms"
                repeat(if (alert) 2 else 1) { playPcm(audio.samples, audio.sampleRate, alert) }
            } else {
                label = "platform-tts"
                val parts = (ttsLocales[msg.lang] ?: "en_IN").split('_')
                runOnUiThread {
                    tts?.language = Locale(parts[0], parts[1])
                    repeat(if (alert) 2 else 1) { tts?.speak(msg.text, TextToSpeech.QUEUE_ADD, null, "m$seq-$it") }
                }
            }
            runOnUiThread { append("← [${if (alert) "ALERT/" else ""}${msg.lang}, $size B, $label] ${msg.text}") }
        }.start()
    }

    private fun playPcm(samples: FloatArray, sampleRate: Int, alert: Boolean) {
        val shorts = ShortArray(samples.size) {
            (samples[it].coerceIn(-1f, 1f) * 32767).toInt().toShort()
        }
        track?.release()
        val t = AudioTrack.Builder()
            .setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(if (alert) AudioAttributes.USAGE_ALARM else AudioAttributes.USAGE_MEDIA)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build()
            )
            .setAudioFormat(
                AudioFormat.Builder().setSampleRate(sampleRate)
                    .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                    .setChannelMask(AudioFormat.CHANNEL_OUT_MONO).build()
            )
            .setTransferMode(AudioTrack.MODE_STATIC)
            .setBufferSizeInBytes(shorts.size * 2)
            .build()
        track = t
        t.write(shorts, 0, shorts.size)
        t.play()
        Thread.sleep((samples.size * 1000L / sampleRate) + 100)
    }

    private fun append(line: String) {
        transcript.append(line + "\n")
    }

    override fun onDestroy() {
        transports.forEach { it.stop() }
        tts?.shutdown()
        track?.release()
        vad?.release()
        stopService(Intent(this, PttService::class.java))
        super.onDestroy()
    }
}
