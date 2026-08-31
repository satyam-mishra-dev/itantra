package com.nullpointers.itantra

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Typeface
import android.view.Gravity
import android.view.View
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
    @Volatile private var speech: SpeechEngine? = null
    private lateinit var transports: List<Transport>
    private lateinit var transcriptBox: LinearLayout
    private lateinit var scroll: ScrollView
    private lateinit var emptyHint: TextView
    private lateinit var pttHint: TextView
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
    // Mutual NSD discovery gives two sockets to the same peer; NSD+BT gives two bearers.
    // De-dup received frames by content hash. ponytail: 64-deep LRU, plenty for a walkie-talkie.
    private val seen = ArrayDeque<Int>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        vc = VarnaCode(assets.open("codebooks.json").readBytes().decodeToString())
        transcriptBox = findViewById(R.id.transcriptBox)
        scroll = findViewById(R.id.scroll)
        emptyHint = findViewById(R.id.emptyHint)
        pttHint = findViewById(R.id.pttHint)
        status = findViewById(R.id.status)
        langSpinner = findViewById(R.id.lang)
        input = findViewById(R.id.input)
        alertBox = findViewById(R.id.alert)

        langSpinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, langNames)
        langSpinner.setSelection(1) // Hindi default

        tts = TextToSpeech(this) { }
        // Heavy natives (sherpa-onnx JNI + VAD model) load off the main thread —
        // blocking here starved PttService.startForeground() past its ANR deadline.
        Thread {
            speech = SpeechEngine(this)
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
        }.start()

        transports = listOf(
            NsdTransport(this, ::onFrameBytes) { s -> runOnUiThread { setStatus(s) } },
            BtTransport(this, ::onFrameBytes) { s -> runOnUiThread { setStatus(s) } },
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
        findViewById<Button>(R.id.connectIp).setOnClickListener {
            val box = EditText(this).apply {
                hint = getString(R.string.connect_hint)
                setText("192.168.43.1:${NsdTransport.FIXED_PORT}")
            }
            android.app.AlertDialog.Builder(this)
                .setTitle(R.string.connect_button)
                .setView(box)
                .setPositiveButton(android.R.string.ok) { _, _ ->
                    (transports.first() as NsdTransport).manualConnect(box.text.toString())
                }
                .setNegativeButton(android.R.string.cancel, null)
                .show()
        }

        val ptt = findViewById<Button>(R.id.ptt)
        ptt.setOnTouchListener { v, ev ->
            when (ev.action) {
                MotionEvent.ACTION_DOWN -> {
                    pttDown(); v.isPressed = true
                    v.animate().scaleX(1.08f).scaleY(1.08f).setDuration(120).start()
                    pttHint.text = getString(R.string.ptt_listening)
                    pttHint.setTextColor(getColor(R.color.orange))
                    true
                }
                MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                    v.isPressed = false; v.performClick()
                    v.animate().scaleX(1f).scaleY(1f).setDuration(120).start()
                    pttHint.text = getString(R.string.ptt_hint)
                    pttHint.setTextColor(getColor(R.color.textSecondary))
                    pttUp(); true
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
        vadActive = vad != null && speech?.sttFor(l) != null
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
        setStatus(getString(R.string.recording))
    }

    /** Emit every completed speech segment: recognize + transmit while the button is still held. */
    private fun drainVad(v: Vad, l: String) {
        while (!v.empty()) {
            val seg = v.front().samples
            v.pop()
            Thread {
                val sp = speech ?: return@Thread
                val engine = sp.sttFor(l) ?: return@Thread
                val t0 = SystemClock.elapsedRealtime()
                val text = sp.recognize(engine, seg)
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
            setStatus(getString(R.string.sent_vad))
            return
        }
        // fallback: whole-clip decode, or typed text when no model pack
        val t0 = SystemClock.elapsedRealtime()
        Thread {
            val sp = speech
            val engine = sp?.sttFor(l)
            val sttMs: Long
            val text: String
            if (sp != null && engine != null && samples.isNotEmpty()) {
                val out = sp.recognize(engine, samples)
                sttMs = SystemClock.elapsedRealtime() - t0
                text = out.ifBlank { input.text.toString() }
            } else {
                sttMs = -1
                text = input.text.toString()
            }
            val prosody = if (samples.isNotEmpty()) Prosody.encode(samples) else null
            runOnUiThread {
                if (text.isBlank()) { setStatus(getString(R.string.nothing_to_send)); return@runOnUiThread }
                input.setText("")
                send(text, l, sttMs, samples.size / 16000.0, prosody)
            }
        }.start()
    }

    private fun send(text: String, l: String, sttMs: Long, audioSec: Double, prosody: Int? = null) {
        val prio = if (alertBox.isChecked) Frame.ALERT else Frame.NORMAL
        val frame = Frame.pack(vc, text, l, prio, seq++, prosody = prosody)
        Thread {
            val n = transports.sumOf { it.send(frame) }
            runOnUiThread {
                val stt = if (sttMs >= 0)
                    " · STT ${sttMs} ms" + if (audioSec > 0.05) " · RTF %.2f".format(sttMs / 1000.0 / audioSec) else ""
                else " · typed"
                bubble(text, "${frame.size} B" + (if (prio == Frame.ALERT) " · ALERT" else "") + stt +
                    (if (n == 0) " · no peer" else ""), if (prio == Frame.ALERT) ALERTK else SENT)
                setStatus(if (n == 0) getString(R.string.no_peers) else "connected")
            }
        }.start()
    }

    private fun onFrameBytes(bytes: ByteArray) {
        val h = bytes.contentHashCode()
        synchronized(seen) {
            if (h in seen) return
            seen.addLast(h)
            if (seen.size > 64) seen.removeFirst()
        }
        val tRecv = SystemClock.elapsedRealtime()
        val msg = try { Frame.unpack(vc, bytes) } catch (e: Exception) {
            runOnUiThread { bubble("corrupt frame dropped", "${bytes.size} B · CRC/decode failed", RECV) }; return
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
        val engine = speech?.ttsFor(msg.lang)
        val pp = msg.prosody?.let { Prosody.ttsParams(it) }
        Thread {
            val label: String
            if (engine != null) {
                val audio = engine.generate(msg.text, 0, pp?.speed ?: 1.0f)
                val firstAudioMs = SystemClock.elapsedRealtime() - tRecv
                LastStats.ttsFirstAudioMs = firstAudioMs
                label = "first audio ${firstAudioMs} ms" + (pp?.let { " · ${it.urgency}" } ?: "")
                repeat(maxOf(if (alert) 2 else 1, pp?.repeats ?: 1)) {
                    playPcm(audio.samples, audio.sampleRate, alert, pp?.gain ?: 1.0f)
                }
            } else {
                label = "platform TTS"
                val parts = (ttsLocales[msg.lang] ?: "en_IN").split('_')
                runOnUiThread {
                    tts?.language = Locale(parts[0], parts[1])
                    repeat(if (alert) 2 else 1) { tts?.speak(msg.text, TextToSpeech.QUEUE_ADD, null, "m$seq-$it") }
                }
            }
            runOnUiThread {
                bubble(msg.text, "$size B" + (if (alert) " · ALERT" else "") + " · ${msg.lang} · $label",
                    if (alert) ALERTK else RECV)
            }
        }.start()
    }

    private fun playPcm(samples: FloatArray, sampleRate: Int, alert: Boolean, gain: Float = 1.0f) {
        // ponytail: gain >1 hard-clips — acceptable siren effect for urgent frames
        val shorts = ShortArray(samples.size) {
            ((samples[it] * gain).coerceIn(-1f, 1f) * 32767).toInt().toShort()
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

    private fun setStatus(s: String) {
        val connected = s.startsWith("connected")
        status.text = when {
            connected -> "● connected"
            s.startsWith("advertising") -> getString(R.string.starting)
            else -> s
        }
        status.setTextColor(getColor(if (connected) R.color.green else R.color.textSecondary))
    }

    private fun dp(x: Int) = (x * resources.displayMetrics.density).toInt()

    /** Chat bubble + muted byte chip — the chip is the on-stage wow moment (45 B per sentence). */
    private fun bubble(text: String, meta: String, kind: Int) {
        emptyHint.visibility = View.GONE
        val side = if (kind == RECV) Gravity.START else Gravity.END
        val col = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { gravity = side; topMargin = dp(8) }
        }
        col.addView(TextView(this).apply {
            this.text = text
            textSize = 18f
            setTextColor(getColor(if (kind == ALERTK) R.color.red else R.color.textPrimary))
            if (kind == ALERTK) setTypeface(null, Typeface.BOLD)
            setBackgroundResource(when (kind) {
                SENT -> R.drawable.bubble_sent; ALERTK -> R.drawable.bubble_alert; else -> R.drawable.bubble_recv
            })
            setPadding(dp(14), dp(10), dp(14), dp(10))
            maxWidth = (resources.displayMetrics.widthPixels * 0.8).toInt()
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { gravity = side }
        })
        col.addView(TextView(this).apply {
            this.text = meta
            textSize = 12f
            setTextColor(getColor(if (kind == ALERTK) R.color.red else R.color.textSecondary))
            setBackgroundResource(R.drawable.chip_bg)
            setPadding(dp(8), dp(3), dp(8), dp(3))
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { gravity = side; topMargin = dp(3) }
        })
        transcriptBox.addView(col)
        scroll.post { scroll.fullScroll(View.FOCUS_DOWN) }
    }

    private companion object { const val SENT = 0; const val RECV = 1; const val ALERTK = 2 }

    override fun onDestroy() {
        transports.forEach { it.stop() }
        tts?.shutdown()
        track?.release()
        vad?.release()
        stopService(Intent(this, PttService::class.java))
        super.onDestroy()
    }
}
