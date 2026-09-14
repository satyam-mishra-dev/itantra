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
import android.util.Log
import android.view.MotionEvent
import android.widget.*
import com.k2fsa.sherpa.onnx.SileroVadModelConfig
import com.k2fsa.sherpa.onnx.Vad
import com.k2fsa.sherpa.onnx.VadModelConfig
import java.util.Locale
import java.util.concurrent.CountDownLatch
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

/**
 * P3: Silero VAD chunks long PTT holds into sentences — sentence 1 is
 * recognized and transmitted while sentence 2 is still being spoken (the PS's
 * "detect pauses, form sentences, stream instantly"). Dual bearers: Wi-Fi
 * (NSD/TCP) + Bluetooth RFCOMM. Real STT/TTS when model packs exist,
 * typed-text / platform-TTS fallback otherwise.
 */
class MainActivity : Activity() {

    private val langCodes = VarnaCode.LANGS
    private val langNames = LANG_NAMES
    private val ttsLocales = mapOf(
        "en" to "en_IN", "hi" to "hi_IN", "bn" to "bn_IN", "ta" to "ta_IN", "te" to "te_IN",
        "gu" to "gu_IN", "mr" to "mr_IN", "kn" to "kn_IN", "ml" to "ml_IN", "or" to "or_IN"
    )

    private lateinit var vc: VarnaCode
    @Volatile private var speech: SpeechEngine? = null
    private lateinit var transports: List<Transport>
    private lateinit var transcriptBox: LinearLayout
    private lateinit var scroll: ScrollView
    private lateinit var emptyHint: View
    private lateinit var pttHint: TextView
    private lateinit var status: TextView
    private lateinit var langSpinner: Spinner
    private lateinit var input: EditText
    private lateinit var download: TextView
    @Volatile private var downloading = false
    private val autoTried = HashSet<String>()
    private lateinit var alertPill: TextView
    private lateinit var pttRing: View
    private var pulse: android.animation.ValueAnimator? = null
    private var tts: TextToSpeech? = null
    private var track: AudioTrack? = null
    private var pcm: PcmRecorder? = null
    private var vad: Vad? = null
    private var vadActive = false
    private var pttT0 = 0L
    // One consumer for synthesis + playback: two frames landing together used to cut each other off.
    private val playback: ExecutorService = Executors.newSingleThreadExecutor()
    private var savedMusicVol = -1                  // -1 = no ALERT is holding the volume up right now
    private var savedAlarmVol = -1
    private var focusReq: AudioFocusRequest? = null
    // Mutual NSD discovery gives two sockets to the same peer; NSD+BT gives two bearers.
    // De-dup received frames by content hash. ponytail: 64-deep LRU, plenty for a walkie-talkie.
    private val seen = ArrayDeque<Int>()
    private lateinit var arq: Arq
    private val metaOf = HashMap<Int, TextView>()   // seq → byte chip, gets a ✓ on ACK
    private val LINK = "iTantraLink"                // logcat tag: tx/rx/ack with epoch ms for latency measurement

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
        download = findViewById(R.id.download)
        download.setOnClickListener { downloadPack(lang()) }
        NsdTransport.myIp()?.let { findViewById<TextView>(R.id.emptySub).append("\n" + getString(R.string.this_phone, it)) }
        alertPill = findViewById(R.id.alert)
        pttRing = findViewById(R.id.pttRing)
        alertPill.setOnClickListener { setAlert(!alertPill.isSelected) }

        langSpinner.adapter = ArrayAdapter(this, R.layout.spinner_pill_item, langNames).apply {
            setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        }
        langSpinner.setSelection(intent.getIntExtra("lang", 1))
        langSpinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(p: AdapterView<*>?, v: View?, pos: Int, id: Long) = refreshInput()
            override fun onNothingSelected(p: AdapterView<*>?) {}
        }

        tts = TextToSpeech(this) { }
        // Heavy natives (sherpa-onnx JNI + VAD model) load off the main thread —
        // blocking here starved PttService.startForeground() past its ANR deadline.
        Thread {
            speech = SpeechEngine(this)
            refreshInput()
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
        arq = Arq(
            tx = { f -> transports.sumOf { it.send(f) } },
            makeAck = { s -> Frame.pack(vc, "", "hi", Frame.ACK, s) },
        )
        arq.acked = { s ->
            Log.i(LINK, "ack seq=$s t=${System.currentTimeMillis()}")
            runOnUiThread { metaOf[s]?.let { if (!it.text.endsWith("✓")) it.append(" ✓") } }
        }
        Thread { while (true) { Thread.sleep(500); arq.tick() } }.apply { isDaemon = true }.start()
        intent.getStringExtra("ip")?.let { ip ->
            status.postDelayed({ (transports.first() as NsdTransport).manualConnect(ip) }, 600)
        }

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

        findViewById<View>(R.id.eval).setOnClickListener {
            startActivity(Intent(this, EvalActivity::class.java))
        }
        findViewById<View>(R.id.connectIp).setOnClickListener {
            askIp { (transports.first() as NsdTransport).manualConnect(it) }
        }

        val ptt = findViewById<Button>(R.id.ptt)
        ptt.setOnTouchListener { v, ev ->
            when (ev.action) {
                MotionEvent.ACTION_DOWN -> {
                    pttDown(); v.isPressed = true
                    v.animate().scaleX(1.06f).scaleY(1.06f).setDuration(120).start()
                    startPulse()
                    pttHint.text = getString(R.string.ptt_listening)
                    pttHint.setTextColor(getColor(R.color.orange))
                    true
                }
                MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                    v.isPressed = false; v.performClick()
                    v.animate().scaleX(1f).scaleY(1f).setDuration(120).start()
                    stopPulse()
                    pttHint.text = getString(R.string.ptt_hint)
                    pttHint.setTextColor(getColor(R.color.textSecondary))
                    pttUp(); true
                }
                else -> false
            }
        }
    }

    private fun lang(): String = langCodes[langSpinner.selectedItemPosition]

    /**
     * Typed fallback only shows when the selected language has no STT pack (checked off-thread: sttFor loads lazily).
     * A missing pack offers a one-tap download and starts it by itself on an unmetered network.
     */
    private fun refreshInput() {
        val l = lang()
        Thread {
            val has = try { speech?.sttFor(l) != null } catch (t: Throwable) { false }
            val missing = Packs.KINDS.any { !Packs.installed(this, l, it) }
            runOnUiThread {
                input.visibility = if (has) View.GONE else View.VISIBLE
                download.text = getString(R.string.download_pack, langNames[langCodes.indexOf(l)])
                download.visibility = if (missing && !downloading) View.VISIBLE else View.GONE
                val cm = getSystemService(CONNECTIVITY_SERVICE) as android.net.ConnectivityManager
                if (missing && autoTried.add(l) && cm.activeNetwork != null && !cm.isActiveNetworkMetered) downloadPack(l)
            }
        }.start()
    }

    private fun downloadPack(l: String) {
        if (downloading) return
        downloading = true
        download.visibility = View.GONE
        Thread {
            val msg = try {
                Packs.install(this, l) { p -> Log.i(LINK, "pack $p"); runOnUiThread { setStatus("downloading $p") } }
                speech?.forget(l)
                getString(R.string.pack_ready)
            } catch (e: Exception) {
                Log.w(LINK, "pack install failed", e)
                getString(R.string.pack_failed, e.message ?: e.javaClass.simpleName)
            }
            downloading = false
            runOnUiThread {
                Toast.makeText(this, msg, Toast.LENGTH_LONG).show()
                refreshInput()
                setStatus(if (peer != null) "connected" else getString(R.string.starting))
            }
        }.start()
    }

    private fun setAlert(on: Boolean) {
        alertPill.isSelected = on
        alertPill.text = getString(if (on) R.string.alert_pill_on else R.string.alert_pill)
        alertPill.setTextColor(if (on) 0xFFFFFFFF.toInt() else getColor(R.color.red))
    }

    /** Expanding orange ring while the button is held — the "I'm live" affordance. */
    private fun startPulse() {
        pulse?.cancel()
        pulse = android.animation.ValueAnimator.ofFloat(0f, 1f).apply {
            duration = 1100; repeatCount = android.animation.ValueAnimator.INFINITE
            addUpdateListener {
                val f = it.animatedValue as Float
                pttRing.scaleX = 0.88f + 0.3f * f; pttRing.scaleY = pttRing.scaleX
                pttRing.alpha = 1f - f
            }
            start()
        }
    }

    private fun stopPulse() {
        pulse?.cancel(); pulse = null
        pttRing.animate().alpha(0f).setDuration(150).start()
    }

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
        val prio = if (alertPill.isSelected) Frame.ALERT else Frame.NORMAL
        setAlert(false) // one-shot: never let the next casual message inherit max-volume
        val s = arq.nextSeq()   // skips seqs still awaiting an ACK, so a wrap never clobbers a queued frame
        val frame = Frame.pack(vc, text, l, prio, s, prosody = prosody)
        Thread {
            Log.i(LINK, "tx seq=$s bytes=${frame.size} t=${System.currentTimeMillis()}")
            val n = arq.send(s, frame)
            runOnUiThread {
                val stt = if (sttMs >= 0)
                    " · STT ${sttMs} ms" + if (audioSec > 0.05) " · RTF %.2f".format(sttMs / 1000.0 / audioSec) else ""
                else " · typed"
                metaOf[s] = bubble(text, "${frame.size} B" + (if (prio == Frame.ALERT) " · ALERT" else "") + stt +
                    (if (n == 0) " · queued" else ""), prio == Frame.ALERT, incoming = false)
                setStatus(if (n == 0) getString(R.string.no_peers) else "connected")
            }
        }.start()
    }

    private fun onFrameBytes(bytes: ByteArray) {
        if (bytes.size < 2) return
        val (prio, s) = Arq.peek(bytes)
        if (prio == Frame.ACK) { arq.onAck(s); return }
        Log.i(LINK, "rx seq=$s bytes=${bytes.size} t=${System.currentTimeMillis()}")
        arq.ackFor(prio, s)   // before dedupe: a retransmit whose first ACK was lost still gets ACKed
        val h = bytes.contentHashCode()
        synchronized(seen) {
            if (h in seen) return
            seen.addLast(h)
            if (seen.size > 64) seen.removeFirst()
        }
        val tRecv = SystemClock.elapsedRealtime()
        val msg = try { Frame.unpack(vc, bytes) } catch (e: Exception) {
            runOnUiThread { bubble("corrupt frame dropped", "${bytes.size} B · CRC/decode failed", alert = false, incoming = true) }; return
        }
        runOnUiThread { speak(msg, bytes.size, tRecv) }
    }

    private fun speak(msg: Frame.Msg, size: Int, tRecv: Long) {
        val alert = msg.prio == Frame.ALERT
        val engine = speech?.ttsFor(msg.lang)
        val pp = msg.prosody?.let { Prosody.ttsParams(it) }
        val repeats = maxOf(if (alert) 2 else 1, pp?.repeats ?: 1)
        // Serialized: each message is spoken to the end. "first audio ms" now includes queue wait — the honest receive→ear number.
        playback.execute {
            if (alert) raiseForAlert()
            try {
                val label: String
                if (engine != null) {
                    val audio = engine.generate(msg.text, 0, pp?.speed ?: 1.0f)
                    val firstAudioMs = SystemClock.elapsedRealtime() - tRecv
                    LastStats.ttsFirstAudioMs = firstAudioMs
                    label = "first audio ${firstAudioMs} ms" + (pp?.let { " · ${it.urgency}" } ?: "")
                    repeat(repeats) { playPcm(audio.samples, audio.sampleRate, alert, pp?.gain ?: 1.0f) }
                } else {
                    label = if (speakPlatform(msg, repeats)) "platform TTS"
                            else getString(R.string.no_voice, msg.lang)
                }
                runOnUiThread {
                    bubble(msg.text, "$size B" + (if (alert) " · ALERT" else "") + " · ${msg.lang} · $label",
                        alert, incoming = true)
                }
            } finally {
                if (alert) restoreAfterAlert()   // runs even if synthesis threw or the queue was shut down
            }
        }
    }

    /** ALERT takes the room: max volume + exclusive focus. Always paired with [restoreAfterAlert] — we used to raise and never give back. */
    private fun raiseForAlert() {
        val am = getSystemService(AUDIO_SERVICE) as AudioManager
        if (savedMusicVol < 0) {   // first alert of a burst remembers what the user actually had set
            savedMusicVol = am.getStreamVolume(AudioManager.STREAM_MUSIC)
            savedAlarmVol = am.getStreamVolume(AudioManager.STREAM_ALARM)
        }
        try {
            am.setStreamVolume(AudioManager.STREAM_MUSIC, am.getStreamMaxVolume(AudioManager.STREAM_MUSIC), 0)
            am.setStreamVolume(AudioManager.STREAM_ALARM, am.getStreamMaxVolume(AudioManager.STREAM_ALARM), 0)
        } catch (_: SecurityException) { }   // DND can refuse the alarm stream; the alert still plays
        if (Build.VERSION.SDK_INT >= 26 && focusReq == null) {
            val r = AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_EXCLUSIVE)
                .setAudioAttributes(
                    AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_ALARM)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build()
                ).build()
            focusReq = r
            am.requestAudioFocus(r)
        }
    }

    private fun restoreAfterAlert() {
        val am = getSystemService(AUDIO_SERVICE) as AudioManager
        try {
            if (savedMusicVol >= 0) am.setStreamVolume(AudioManager.STREAM_MUSIC, savedMusicVol, 0)
            if (savedAlarmVol >= 0) am.setStreamVolume(AudioManager.STREAM_ALARM, savedAlarmVol, 0)
        } catch (_: SecurityException) { }
        savedMusicVol = -1; savedAlarmVol = -1
        if (Build.VERSION.SDK_INT >= 26) focusReq?.let { am.abandonAudioFocusRequest(it); focusReq = null }
    }

    /**
     * Fallback voice. Blocks until it finishes speaking, or an ALERT loses its volume mid-sentence.
     * Returns false when the engine has no voice for the language (or is not ready yet): the old code
     * waited the full 30 s for a speak that never started, stalling every later message behind it.
     */
    private fun speakPlatform(msg: Frame.Msg, repeats: Int): Boolean {
        val t = tts ?: return false
        val parts = (ttsLocales[msg.lang] ?: "en_IN").split('_')
        if (t.setLanguage(Locale(parts[0], parts[1])) < 0) return false   // LANG_MISSING_DATA / LANG_NOT_SUPPORTED
        val done = CountDownLatch(repeats)
        t.setOnUtteranceProgressListener(object : android.speech.tts.UtteranceProgressListener() {
            override fun onStart(id: String?) {}
            override fun onDone(id: String?) { done.countDown() }
            @Suppress("OverridingDeprecatedMember", "DEPRECATION")
            override fun onError(id: String?) { done.countDown() }
        })
        repeat(repeats) {
            if (t.speak(msg.text, TextToSpeech.QUEUE_ADD, null, "m${msg.seq}-$it") != TextToSpeech.SUCCESS) done.countDown()
        }
        done.await(30, TimeUnit.SECONDS)   // bounded: a broken engine must not wedge the queue
        return true
    }

    private fun playPcm(samples: FloatArray, sampleRate: Int, alert: Boolean, gain: Float = 1.0f) {
        // ponytail: gain >1 hard-clips — acceptable siren effect for urgent frames
        val shorts = ShortArray(samples.size) {
            ((samples[it] * gain).coerceIn(-1f, 1f) * 32767).toInt().toShort()
        }
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
        try {
            t.write(shorts, 0, shorts.size)
            t.play()
            Thread.sleep((samples.size * 1000L / sampleRate) + 100)
        } finally {
            // Released on the thread that owns it — we used to release the previous track from the next receive thread, cutting off a live alert.
            try { t.release() } catch (_: Exception) { }
            track = null
        }
    }

    private var peer: String? = null

    /** Chip shows connection state; a live peer is never overwritten by late advertise/discovery events. */
    private fun setStatus(s: String) {
        when {
            s.startsWith("connected to ") -> { peer = shortPeer(s.removePrefix("connected to ")); Thread { arq.flush() }.start() }
            s.startsWith("BT connected: ") -> { peer = shortPeer(s.removePrefix("BT connected: ")); Thread { arq.flush() }.start() }
            s.startsWith("peer ") || s.startsWith("BT peer") -> peer = null
            s == "connected" && peer == null -> peer = "peer" // a frame just went out on a live socket
        }
        val link = s.startsWith("connected") || s.startsWith("advertising") || s.startsWith("BT connected") ||
            s.startsWith("peer ") || s.startsWith("BT peer") || s.startsWith("discovery")
        val p = peer
        val up = link && p != null
        status.text = when {
            !link -> s
            up -> "● connected · $p"
            else -> getString(R.string.starting)
        }
        status.setBackgroundResource(if (up) R.drawable.hero_chip_green else R.drawable.hero_chip)
        status.setTextColor(getColor(if (up) R.color.onHero else R.color.onHeroMuted))
    }

    /** "iTantra-sdk_gphone64_arm64-4269" → "sdk gphone64"; "192.168.43.1:47474" → "192.168.43.1". Whole words only. */
    private fun shortPeer(name: String): String {
        val n = name.removePrefix("iTantra-")
        if (n.count { it == '.' } == 3) return n.substringBefore(':')
        return n.replace('_', ' ').split(' ', '-').filter { it.isNotBlank() && it.toIntOrNull() == null }
            .take(2).joinToString(" ")
    }

    private fun dp(x: Int) = (x * resources.displayMetrics.density).toInt()

    /** Chat bubble + muted byte chip — the chip is the on-stage wow moment (45 B per sentence). */
    private fun bubble(text: String, meta: String, alert: Boolean, incoming: Boolean): TextView {
        emptyHint.visibility = View.GONE
        // side keys on direction only; ALERT changes colour, never alignment
        val side = if (incoming) Gravity.START else Gravity.END
        val kind = if (alert) ALERTK else if (incoming) RECV else SENT
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
        val chip = TextView(this).apply {
            this.text = meta
            textSize = 12f
            typeface = resources.getFont(R.font.outfit_medium)
            setTextColor(getColor(if (kind == ALERTK) R.color.orange else R.color.textSecondary))
            setBackgroundResource(if (kind == ALERTK) R.drawable.chip_orange else R.drawable.chip_bg)
            setPadding(dp(9), dp(3), dp(9), dp(3))
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { gravity = side; topMargin = dp(4) }
        }
        col.addView(chip)
        col.alpha = 0f; col.translationY = dp(6).toFloat()
        transcriptBox.addView(col)
        col.animate().alpha(1f).translationY(0f).setDuration(150).start()
        scroll.post { scroll.fullScroll(View.FOCUS_DOWN) }
        return chip
    }

    companion object {
        private const val SENT = 0; private const val RECV = 1; private const val ALERTK = 2
        val LANG_NAMES = listOf(
            "English", "हिन्दी", "বাংলা", "தமிழ்", "తెలుగు",
            "ગુજરાતી", "मराठी", "ಕನ್ನಡ", "മലയാളം", "ଓଡ଼ିଆ"
        )
    }

    /** BtTransport bails without BLUETOOTH_CONNECT; on first launch the grant lands after start(), so start it again. */
    override fun onRequestPermissionsResult(code: Int, perms: Array<out String>, res: IntArray) {
        super.onRequestPermissionsResult(code, perms, res)
        transports.forEach { if (it is BtTransport) it.start() }
    }

    override fun onDestroy() {
        transports.forEach { it.stop() }
        playback.shutdownNow()          // interrupts playPcm's sleep; its finally releases the track
        restoreAfterAlert()             // killing the app mid-ALERT must not leave the phone at max volume
        tts?.shutdown()
        try { track?.release() } catch (_: Exception) { }
        vad?.release()
        stopService(Intent(this, PttService::class.java))
        super.onDestroy()
    }
}
