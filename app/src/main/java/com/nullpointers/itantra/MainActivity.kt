package com.nullpointers.itantra

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
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
    private lateinit var transports: List<Transport>   // [relay] — the bearers live inside it
    private lateinit var nsd: NsdTransport
    private lateinit var bt: BtTransport
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
    @Volatile private var vadSegments = 0            // sentences VAD cut out of the current hold
    private val stt: ExecutorService = Executors.newSingleThreadExecutor()   // segments recognized in order — a fast short sentence must not overtake a long one
    private var pttT0 = 0L
    // One consumer for synthesis + playback: two frames landing together used to cut each other off.
    private val playback: ExecutorService = Executors.newSingleThreadExecutor()
    private var savedMusicVol = -1                  // -1 = no ALERT is holding the volume up right now
    private var savedAlarmVol = -1
    private var focusReq: AudioFocusRequest? = null
    // Reliable delivery (p0/reliable.py port): 7-byte ACK/NACK ctrl frames, seq-window dedupe, NACK on gaps,
    // never-give-up store-and-forward (tries=null) with ×2 backoff — flush() on reconnect.
    private val sender = ReliableSender(tries = mapOf(Frame.NORMAL to null, Frame.ALERT to null))
    private val receiver = ReliableReceiver("hi")
    private val seenPhrase = ArrayDeque<Int>()      // phrase frames bypass the receiver (lang=15): dedupe by content, LRU 64
    private val metaOf = HashMap<Int, TextView>()   // seq → byte chip, gets a ✓ on ACK
    private lateinit var pb: Phrasebook
    private val speakQueue = SpeakQueue()           // clause scheduler: ALERT preempts at a clause boundary, cut message resumes
    private val chipOf = HashMap<Any, TextView>()   // received msgId → chip, gets "first audio N ms"
    private var msgIds = 0
    // Team key (AES-GCM, +28 B/frame) and location sharing (+7 B) live in prefs; the settings tile edits them.
    private lateinit var prefs: android.content.SharedPreferences
    @Volatile private var key: ByteArray? = null
    private lateinit var stats: TextView
    private var nSent = 0; private var bytesSent = 0L; private var voiceSec = 0.0   // the on-stage number: text bytes vs a voice call
    private val LINK = "iTantraLink"                // logcat tag: tx/rx/ack with epoch ms for latency measurement

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        vc = VarnaCode(assets.open("codebooks.json").readBytes().decodeToString())
        pb = Phrasebook(assets.open("phrasebook.json").readBytes().decodeToString())
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

        // Flood relay wraps both bearers: A→B→C when A and C can't hear each other (+9 B envelope, TTL 3).
        // myId = 16 bits, stable per install, so a relay node can dedupe our frames across our restarts.
        prefs = getSharedPreferences("itantra", MODE_PRIVATE)
        key = keyFrom(prefs.getString("teamKey", "") ?: "")
        stats = findViewById(R.id.stats)
        findViewById<View>(R.id.settings).setOnClickListener { showSettings() }
        val myId = prefs.getInt("relayId", -1).takeIf { it >= 0 }
            ?: (1..0xFFFF).random().also { prefs.edit().putInt("relayId", it).apply() }
        val relay = RelayTransport(myId, onFrame = ::onFrameBytes)
        nsd = NsdTransport(this, relay::onReceive) { s -> runOnUiThread { setStatus(s) } }
        bt = BtTransport(this, relay::onReceive) { s -> runOnUiThread { setStatus(s) } }
        relay.attach(listOf(nsd, bt))
        transports = listOf(relay)
        transports.forEach { it.start() }
        sender.acked = { s ->
            Log.i(LINK, "ack seq=$s t=${System.currentTimeMillis()}")
            runOnUiThread {
                metaOf[s]?.let { if (!it.text.endsWith("✓")) { it.append(" ✓"); buzz() } }
            }
        }
        Thread { while (true) { Thread.sleep(500); pump() } }.apply { isDaemon = true }.start()
        intent.getStringExtra("ip")?.let { ip ->
            status.postDelayed({ nsd.manualConnect(ip) }, 600)
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
        if (wanted.isNotEmpty()) requestPermissions(wanted.toTypedArray(), 1) else startPtt()

        findViewById<View>(R.id.eval).setOnClickListener {
            startActivity(Intent(this, EvalActivity::class.java))
        }
        findViewById<View>(R.id.connectIp).setOnClickListener {
            askIp { nsd.manualConnect(it) }
        }

        val ptt = findViewById<Button>(R.id.ptt)
        ptt.setOnTouchListener { v, ev ->
            when (ev.action) {
                MotionEvent.ACTION_DOWN -> {
                    pttDown(); v.isPressed = true
                    v.animate().scaleX(1.06f).scaleY(1.06f).setDuration(120).start()
                    startPulse()
                    pttHint.text = getString(R.string.ptt_listening)
                    pttHint.setTextColor(getColor(R.color.live))
                    true
                }
                MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                    v.isPressed = false; v.performClick()
                    v.animate().scaleX(1f).scaleY(1f).setDuration(120).start()
                    stopPulse()
                    pttHint.text = getString(R.string.ptt_hint)
                    pttHint.setTextColor(getColor(R.color.inkMuted))
                    pttUp(); true
                }
                else -> false
            }
        }
    }

    private fun lang(): String = langCodes[langSpinner.selectedItemPosition]

    /** Test hook (singleTop): `am start … --es say <text>` sends text as if typed — `adb shell input text` cannot type Devanagari. */
    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        intent.getStringExtra("say")?.let { send(it, lang(), -1, 0.0) }
    }

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
                val n = Packs.install(this, l) { p -> Log.i(LINK, "pack $p"); runOnUiThread { setStatus("downloading $p") } }
                speech?.forget(l)
                if (n > 0) getString(R.string.pack_ready) else getString(R.string.no_pack_yet, langNames[langCodes.indexOf(l)])
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
        alertPill.setTextColor(if (on) 0xFFFFFFFF.toInt() else getColor(R.color.alert))
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
        vadSegments = 0
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
            vadSegments++
            stt.execute {
                val sp = speech ?: return@execute
                val engine = sp.sttFor(l) ?: return@execute
                val t0 = SystemClock.elapsedRealtime()
                val text = sp.recognize(engine, seg)
                val ms = SystemClock.elapsedRealtime() - t0
                if (text.isNotBlank()) runOnUiThread { send(text, l, ms, seg.size / 16000.0) }
            }
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
            if (vadSegments > 0) { setStatus(getString(R.string.sent_vad)); return }
            // VAD heard no sentence (soft voice, noisy mic): decode the whole clip anyway — it used to vanish silently
            // while the status still said "streamed as you spoke".
        }
        // fallback: whole-clip decode, or typed text when no model pack
        val t0 = SystemClock.elapsedRealtime()
        Thread {
            val sp = speech
            val engine = sp?.sttFor(l)
            val sttMs: Long
            val text: String
            // ponytail: RMS gate 0.004 (≈ -48 dBFS) — a Conformer decodes pure silence as "आ"; retune if a phone mic idles louder.
            val rms = if (samples.isEmpty()) 0.0 else Math.sqrt(samples.sumOf { (it * it).toDouble() } / samples.size)
            if (sp != null && engine != null && rms > SILENCE_RMS) {
                val out = sp.recognize(engine, samples)
                sttMs = SystemClock.elapsedRealtime() - t0
                text = out.ifBlank { input.text.toString() }
            } else {
                sttMs = -1
                text = input.text.toString()
            }
            val prosody = if (samples.isNotEmpty()) Prosody.encode(samples) else null
            runOnUiThread {
                if (text.isBlank()) {
                    setStatus(getString(if (engine != null && samples.isNotEmpty()) R.string.nothing_heard else R.string.nothing_to_send))
                    return@runOnUiThread
                }
                input.setText("")
                send(text, l, sttMs, samples.size / 16000.0, prosody)
            }
        }.start()
    }

    private fun tx(f: ByteArray): Int = transports.sumOf { it.send(f) }
    private val written = HashMap<Int, Int>()   // seq → peers the last attempt reached (0 ⇒ "queued" chip)

    /** Put everything the sender wants on the wire: fresh frames now, retransmits/NACK resends when due. */
    private fun pump() {
        for (f in sender.tick()) {
            val seq = f[1].toInt() and 0xFF
            Log.i(LINK, "tx seq=$seq bytes=${f.size} t=${System.currentTimeMillis()}")
            synchronized(written) { written[seq] = tx(f) }
        }
    }

    private fun send(text: String, l: String, sttMs: Long, audioSec: Double, prosody: Int? = null) {
        val prio = if (alertPill.isSelected) Frame.ALERT else Frame.NORMAL
        setAlert(false) // one-shot: never let the next casual message inherit max-volume
        val s = sender.nextSeq()   // skips seqs still in flight, so a wrap never clobbers a queued frame
        val frame = Frame.pack(vc, text, l, prio, s, key = key, prosody = prosody, location = myLocation())
        val best = pb.match(text, l).firstOrNull()   // phrase snap is offered, never auto-sent
        countSentence(frame.size, if (audioSec > 0.05) audioSec else text.length / 12.0)
        Thread {
            sender.send(frame, prio)
            pump()
            val n = synchronized(written) { written[s] ?: 0 }
            runOnUiThread {
                val stt = if (sttMs >= 0)
                    " · STT ${sttMs} ms" + if (audioSec > 0.05) " · RTF %.2f".format(sttMs / 1000.0 / audioSec) else ""
                else " · typed"
                metaOf[s] = bubble(text, "${frame.size} B" + (if (prio == Frame.ALERT) " · ALERT" else "") + stt +
                    (if (n == 0) " · queued" else ""), prio == Frame.ALERT, incoming = false)
                best?.let { offerPhrase(it, prio) }
                setStatus(if (n == 0) getString(R.string.no_peers) else "connected")
            }
        }.start()
    }

    /** One-tap chip under the sent bubble: the same sentence as a 9–10 B language-neutral phrase frame. */
    private fun offerPhrase(c: Phrasebook.Candidate, prio: Int) {
        val chip = bubbleChip(getString(R.string.phrase_offer, pb.render(c.idx, lang(), c.n)), incoming = false)
        chip.setOnClickListener {
            chip.setOnClickListener(null)
            val s = sender.nextSeq()
            val f = pb.pack(c.idx, prio, s, c.n)
            chip.text = getString(R.string.phrase_sent, f.size)
            metaOf[s] = chip
            Thread { sender.send(f, prio); pump() }.start()
        }
    }

    private fun onFrameBytes(bytes: ByteArray) {
        if (bytes.size < 6) return
        if (sender.onCtrl(bytes)) return                       // 7-byte delivery ACK/NACK for one of ours
        val seq = bytes[1].toInt() and 0xFF
        Log.i(LINK, "rx seq=$seq bytes=${bytes.size} t=${System.currentTimeMillis()}")
        val tRecv = SystemClock.elapsedRealtime()
        if (Phrasebook.isPhraseFrame(bytes)) {                 // lang=15: Frame.unpack would throw, so route first
            tx(ReliableCtrl.make(seq, ReliableCtrl.ACK_BYTE))  // ACK before dedupe — a retransmit whose first ACK was lost still gets one
            val h = bytes.contentHashCode()
            synchronized(seenPhrase) { if (h in seenPhrase) return; seenPhrase.addLast(h); if (seenPhrase.size > 64) seenPhrase.removeFirst() }
            val d = try { pb.unpack(bytes) } catch (e: Exception) {
                runOnUiThread { bubble("corrupt frame dropped", "${bytes.size} B · CRC/decode failed", alert = false, incoming = true) }; return
            }
            runOnUiThread {
                val l = lang()   // rendered in THIS phone's language — that is the point of a phrase frame
                speak(Frame.Msg(0, l, d.prio, d.seq, pb.render(d.idx, l, d.n)), bytes.size, tRecv,
                    extra = " · phrase" + if (!d.fpOk) " · book mismatch" else "")
            }
            return
        }
        val r = try { receiver.ingest(bytes, vc, key) } catch (e: Exception) {
            val why = if (e.message?.contains("key") == true || e.message == "auth failed") getString(R.string.encrypted_no_key) else "CRC/decode failed"
            runOnUiThread { bubble("corrupt frame dropped", "${bytes.size} B · $why", alert = false, incoming = true) }; return
        }
        r.ctrl.forEach { tx(it) }                              // ACK (duplicates too) + NACKs for gaps
        val msg = r.msg ?: return                              // duplicate: ACKed above, not shown again
        if (msg.prio == Frame.ACK) return                      // roll-call class, not for the transcript
        runOnUiThread { speak(msg, bytes.size, tRecv) }
    }

    private fun speak(msg: Frame.Msg, size: Int, tRecv: Long, extra: String = "") {
        val alert = msg.prio == Frame.ALERT
        val pp = msg.prosody?.let { Prosody.ttsParams(it) }
        val id = ++msgIds
        val where = msg.location?.let { " · 📍 " + describe(it) } ?: ""
        countSentence(size, msg.text.length / 12.0)
        // Bubble lands the moment the frame does; the chip gets "first audio N ms" when its first clause plays.
        chipOf[id] = bubble(msg.text, "$size B" + (if (alert) " · ALERT" else "") + " · ${msg.lang}" + extra + where, alert, incoming = true)
        speakQueue.enqueue(msg.text, msg.lang, alert, pp?.gain ?: 1f, msgId = id)
        firstAudioAt[id] = tRecv
        speedOf[id] = pp?.speed ?: 1f
        playback.execute { drain() }
    }

    private val firstAudioAt = HashMap<Any, Long>()   // msgId → receive time until its first clause is voiced
    private val speedOf = HashMap<Any, Float>()

    /** Runs on the single `playback` thread: one clause at a time, alerts first (a long message yields between clauses). */
    private fun drain() {
        var raised = false
        try {
            while (true) {
                val c = speakQueue.next() ?: break
                Log.i(LINK, "speak msg=${c.msgId} alert=${c.alert} replay=${c.replay} clause=${c.clause}")
                if (c.alert && !raised) { raiseForAlert(); raised = true }
                val engine = speech?.ttsFor(c.lang)
                var label: String? = null
                if (engine != null) {
                    val audio = engine.generate(c.clause, 0, speedOf[c.msgId] ?: 1f)
                    firstAudioAt.remove(c.msgId)?.let { t0 ->
                        val ms = SystemClock.elapsedRealtime() - t0
                        LastStats.ttsFirstAudioMs = ms
                        label = "first audio $ms ms"
                    }
                    playPcm(audio.samples, audio.sampleRate, c.alert, c.gain)
                } else if (firstAudioAt.remove(c.msgId) != null) {
                    label = if (speakPlatform(c.clause, c.lang)) "platform TTS" else getString(R.string.no_voice, c.lang)
                } else speakPlatform(c.clause, c.lang)
                label?.let { l -> runOnUiThread { chipOf[c.msgId]?.append(" · $l") } }
            }
        } finally {
            if (raised) restoreAfterAlert()   // runs even if synthesis threw or the queue was shut down
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
    private fun speakPlatform(clause: String, lang: String): Boolean {
        val t = tts ?: return false
        val parts = (ttsLocales[lang] ?: "en_IN").split('_')
        if (t.setLanguage(Locale(parts[0], parts[1])) < 0) return false   // LANG_MISSING_DATA / LANG_NOT_SUPPORTED
        val done = CountDownLatch(1)
        t.setOnUtteranceProgressListener(object : android.speech.tts.UtteranceProgressListener() {
            override fun onStart(id: String?) {}
            override fun onDone(id: String?) { done.countDown() }
            @Suppress("OverridingDeprecatedMember", "DEPRECATION")
            override fun onError(id: String?) { done.countDown() }
        })
        if (t.speak(clause, TextToSpeech.QUEUE_ADD, null, "c${++utt}") != TextToSpeech.SUCCESS) done.countDown()
        done.await(30, TimeUnit.SECONDS)   // bounded: a broken engine must not wedge the queue
        return true
    }

    private var utt = 0

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
            s.startsWith("connected to ") -> { peer = shortPeer(s.removePrefix("connected to ")); Thread { sender.flush(); pump() }.start() }
            s.startsWith("BT connected: ") -> { peer = shortPeer(s.removePrefix("BT connected: ")); Thread { sender.flush(); pump() }.start() }
            s.startsWith("peer ") || s.startsWith("BT peer") -> peer = null
            s == "connected" && peer == null -> peer = "peer" // a frame just went out on a live socket
        }
        val link = s.startsWith("connected") || s.startsWith("advertising") || s.startsWith("BT connected") ||
            s.startsWith("peer ") || s.startsWith("BT peer") || s.startsWith("discovery")
        val p = peer
        val up = link && p != null
        val text = when {
            !link -> s
            up -> "connected · $p"
            else -> getString(R.string.starting)
        }
        // chip colour = link state: mint connected / amber downloading / red no peer / translucent searching
        val (bg, glyph, fg) = when {
            up -> Triple(R.drawable.chip_status_ok, "●  ", R.color.pillInk)
            text.startsWith("downloading") -> Triple(R.drawable.chip_status_warn, "↓  ", R.color.pillInk)
            text == getString(R.string.no_peers) -> Triple(R.drawable.chip_status_bad, "○  ", R.color.onHero)
            else -> Triple(R.drawable.hero_chip, "", R.color.onHero)
        }
        status.text = glyph + text
        status.setBackgroundResource(bg)
        status.setTextColor(getColor(fg))
    }

    /** "iTantra-sdk_gphone64_arm64-4269" → "sdk gphone64"; "192.168.43.1:47474" → "192.168.43.1". Whole words only. */
    private fun shortPeer(name: String): String {
        val n = name.removePrefix("iTantra-")
        if (n.count { it == '.' } == 3) return n.substringBefore(':')
        return n.replace('_', ' ').split(' ', '-').filter { it.isNotBlank() && it.toIntOrNull() == null }
            .take(2).joinToString(" ")
    }

    private fun dp(x: Int) = (x * resources.displayMetrics.density).toInt()

    /**
     * Chat bubble + byte chip — the chip is the on-stage wow moment (45 B per sentence), so it is a
     * two-segment pill: solid "45 B" block, then the muted meta (lang · timing · ✓ on ACK).
     */
    private fun bubble(text: String, meta: String, alert: Boolean, incoming: Boolean): TextView {
        emptyHint.visibility = View.GONE
        // side keys on direction only; ALERT changes colour, never alignment
        val side = if (incoming) Gravity.START else Gravity.END
        val kind = if (alert) ALERTK else if (incoming) RECV else SENT
        val wrap = LinearLayout.LayoutParams.WRAP_CONTENT
        val col = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            layoutParams = LinearLayout.LayoutParams(wrap, wrap).apply { gravity = side; topMargin = dp(10) }
        }
        val onDark = kind != RECV
        col.addView(LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundResource(when (kind) {
                SENT -> R.drawable.bubble_sent; ALERTK -> R.drawable.bubble_alert; else -> R.drawable.bubble_recv
            })
            elevation = dp(if (kind == RECV) 1 else 3).toFloat()
            setPadding(dp(16), dp(if (kind == ALERTK) 10 else 12), dp(16), dp(12))
            layoutParams = LinearLayout.LayoutParams(wrap, wrap).apply { gravity = side }
            if (kind == ALERTK) addView(TextView(context).apply {
                this.text = getString(R.string.alert_pill)
                textSize = 11f; letterSpacing = 0.14f
                typeface = resources.getFont(R.font.outfit_bold)
                setTextColor(0xCCFFFFFF.toInt())
                setPadding(0, 0, 0, dp(2))
            })
            addView(TextView(context).apply {
                this.text = text
                textSize = 18f
                typeface = resources.getFont(if (kind == ALERTK) R.font.outfit_semibold else R.font.outfit_medium)
                setLineSpacing(0f, 1.15f)
                setTextColor(if (onDark) 0xFFFFFFFF.toInt() else getColor(R.color.ink))
                maxWidth = (resources.displayMetrics.widthPixels * 0.78).toInt() - dp(32)
            })
        })
        // "45 B · hi · first audio 320 ms" → bytes segment | meta segment
        val bytes = meta.substringBefore(" · ")
        val rest = meta.substringAfter(" · ", "")
        val row = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setBackgroundResource(if (kind == ALERTK) R.drawable.chip_alert else R.drawable.chip_bg)
            clipToOutline = true
            layoutParams = LinearLayout.LayoutParams(wrap, wrap).apply { gravity = side; topMargin = dp(5) }
        }
        val byteChip = TextView(this).apply {
            this.text = bytes
            textSize = 13f
            typeface = resources.getFont(R.font.outfit_bold)
            setTextColor(if (kind == ALERTK) 0xFFFFFFFF.toInt() else getColor(R.color.onSignal))
            setBackgroundColor(getColor(if (kind == ALERTK) R.color.alert else R.color.signal))
            setPadding(dp(10), dp(5), dp(10), dp(5))
        }
        val metaChip = TextView(this).apply {
            this.text = rest
            textSize = 12f
            typeface = resources.getFont(R.font.outfit_medium)
            setTextColor(getColor(if (kind == ALERTK) R.color.alert else R.color.inkMuted))
            setPadding(dp(9), dp(5), dp(10), dp(5))
            maxWidth = (resources.displayMetrics.widthPixels * 0.78).toInt() - dp(70)
            visibility = if (rest.isEmpty()) View.GONE else View.VISIBLE
        }
        row.addView(byteChip); row.addView(metaChip)
        col.addView(row)
        col.alpha = 0f; col.translationY = dp(6).toFloat()
        transcriptBox.addView(col)
        col.animate().alpha(1f).translationY(0f).setDuration(150).start()
        scroll.post { scroll.fullScroll(View.FOCUS_DOWN) }
        return if (rest.isEmpty()) byteChip else metaChip
    }

    private fun buzz() {
        val v = getSystemService(VIBRATOR_SERVICE) as? android.os.Vibrator ?: return
        if (Build.VERSION.SDK_INT >= 26) v.vibrate(android.os.VibrationEffect.createOneShot(25, android.os.VibrationEffect.DEFAULT_AMPLITUDE))
    }

    /** SHA-256 of the passphrase, first 16 bytes = AES-128 key; empty passphrase = plaintext frames. */
    private fun keyFrom(pass: String): ByteArray? =
        if (pass.isBlank()) null else java.security.MessageDigest.getInstance("SHA-256").digest(pass.trim().toByteArray()).copyOf(16)

    private fun lastFix(): android.location.Location? {
        if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) return null
        val lm = getSystemService(LOCATION_SERVICE) as android.location.LocationManager
        return try {
            lm.getLastKnownLocation(android.location.LocationManager.GPS_PROVIDER)
                ?: lm.getLastKnownLocation(android.location.LocationManager.NETWORK_PROVIDER)
        } catch (_: SecurityException) { null }
    }

    /** lat/lon to attach, or null (sharing off / no fix yet). ponytail: last known fix — no GPS wake-up, zero battery cost. */
    private fun myLocation(): Pair<Double, Double>? =
        if (!prefs.getBoolean("shareLoc", false)) null else lastFix()?.let { Pair(it.latitude, it.longitude) }

    /** "1.2 km NE" from our own fix, else the raw coordinates. */
    private fun describe(p: Pair<Double, Double>): String {
        val me = lastFix() ?: return "%.4f, %.4f".format(p.first, p.second)
        val out = FloatArray(2)
        android.location.Location.distanceBetween(me.latitude, me.longitude, p.first, p.second, out)
        val dirs = listOf("N", "NE", "E", "SE", "S", "SW", "W", "NW")
        val dir = dirs[(((out[1] + 360) % 360 + 22.5) / 45).toInt() % 8]
        return if (out[0] < 1000) "%.0f m %s".format(out[0], dir) else "%.1f km %s".format(out[0] / 1000, dir)
    }

    /** Text bytes on the wire vs what a voice call would have cost (AMR-NB 12.2 kbps = 1525 B/s) — the number the jury remembers. */
    private fun countSentence(bytes: Int, sec: Double) {
        nSent++; bytesSent += bytes; voiceSec += sec
        val voice = voiceSec * 1525
        stats.visibility = View.VISIBLE
        // "169×" as the hero figure, then the caption and the raw numbers underneath
        val ratio = (if (bytesSent > 0) "%,d".format((voice / bytesSent).toLong()) else "–") + "×"
        val caption = getString(R.string.stats_caption)
        val detail = getString(R.string.stats_strip, nSent, fmtBytes(bytesSent), fmtBytes(voice.toLong()))
        stats.text = android.text.SpannableStringBuilder("$ratio $caption\n$detail").apply {
            setSpan(android.text.style.RelativeSizeSpan(2.6f), 0, ratio.length, 0)
            setSpan(android.text.style.ForegroundColorSpan(getColor(R.color.signal)), 0, ratio.length, 0)
            setSpan(if (Build.VERSION.SDK_INT >= 28) android.text.style.TypefaceSpan(resources.getFont(R.font.outfit_bold))
                    else android.text.style.StyleSpan(android.graphics.Typeface.BOLD), 0, ratio.length, 0)
            setSpan(android.text.style.RelativeSizeSpan(1.25f), ratio.length + 1, ratio.length + 1 + caption.length, 0)
            setSpan(android.text.style.ForegroundColorSpan(0xFFFFFFFF.toInt()), ratio.length + 1, ratio.length + 1 + caption.length, 0)
        }
    }

    private fun fmtBytes(b: Long) = when {
        b < 1000 -> "$b B"; b < 1_000_000 -> "%.1f KB".format(b / 1000.0); else -> "%.2f MB".format(b / 1e6)
    }

    private fun showSettings() {
        val d = resources.displayMetrics.density
        val box = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding((24 * d).toInt(), (12 * d).toInt(), (24 * d).toInt(), (4 * d).toInt()) }
        val label = { s: String -> TextView(this).apply {
            text = s.uppercase(); textSize = 11f; letterSpacing = 0.12f
            typeface = resources.getFont(R.font.outfit_semibold); setTextColor(getColor(R.color.label))
            setPadding(0, (18 * d).toInt(), 0, (6 * d).toInt())
        } }
        val keyBox = EditText(this).apply {
            hint = getString(R.string.team_key_hint); setText(prefs.getString("teamKey", ""))
            textSize = 16f; typeface = resources.getFont(R.font.outfit_medium)
            setBackgroundResource(R.drawable.input_bg); setHintTextColor(getColor(R.color.label))
            setPadding((16 * d).toInt(), (13 * d).toInt(), (16 * d).toInt(), (13 * d).toInt())
        }
        val note = TextView(this).apply {
            text = getString(R.string.team_key_note); textSize = 12f; setTextColor(getColor(R.color.inkMuted))
            setPadding((4 * d).toInt(), (8 * d).toInt(), 0, 0)
        }
        val loc = android.widget.Switch(this).apply {
            text = getString(R.string.share_location); isChecked = prefs.getBoolean("shareLoc", false)
            textSize = 15f; typeface = resources.getFont(R.font.outfit_medium); setTextColor(getColor(R.color.ink))
            setPadding((4 * d).toInt(), (10 * d).toInt(), (4 * d).toInt(), (6 * d).toInt())
        }
        val peers = (nsd.peers() + bt.peers()).ifEmpty { listOf(getString(R.string.no_peers_yet)) }
        val peersView = TextView(this).apply {
            text = peers.joinToString("\n") { "●  " + shortPeer(it) }
            textSize = 14f; typeface = resources.getFont(R.font.outfit_medium); setTextColor(getColor(R.color.ink))
            setLineSpacing(0f, 1.3f)
            setBackgroundResource(R.drawable.chip_bg)
            setPadding((14 * d).toInt(), (10 * d).toInt(), (14 * d).toInt(), (10 * d).toInt())
        }
        box.addView(label(getString(R.string.settings_sub))); box.addView(keyBox); box.addView(note)
        box.addView(loc); box.addView(label(getString(R.string.peers_title))); box.addView(peersView)
        android.app.AlertDialog.Builder(this)
            .setTitle(R.string.settings_title)
            .setView(box)
            .setPositiveButton(android.R.string.ok) { _, _ ->
                prefs.edit().putString("teamKey", keyBox.text.toString()).putBoolean("shareLoc", loc.isChecked).apply()
                key = keyFrom(keyBox.text.toString())
                if (loc.isChecked && checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED)
                    requestPermissions(arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION), 2)
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    /** A lone chip row (no bubble) under the last message — used for the phrase-snap offer. */
    private fun bubbleChip(text: String, incoming: Boolean): TextView {
        val side = if (incoming) Gravity.START else Gravity.END
        val chip = TextView(this).apply {
            this.text = text
            textSize = 12f
            typeface = resources.getFont(R.font.outfit_medium)
            setTextColor(getColor(R.color.warnText))
            setBackgroundResource(R.drawable.chip_status_warn)
            setPadding(dp(9), dp(4), dp(9), dp(4))
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { gravity = side; topMargin = dp(4) }
        }
        transcriptBox.addView(chip)
        scroll.post { scroll.fullScroll(View.FOCUS_DOWN) }
        return chip
    }

    companion object {
        private const val SILENCE_RMS = 0.004
        private const val SENT = 0; private const val RECV = 1; private const val ALERTK = 2
        val LANG_NAMES = listOf(
            "English", "हिन्दी", "বাংলা", "தமிழ்", "తెలుగు",
            "ગુજરાતી", "मराठी", "ಕನ್ನಡ", "മലയാളം", "ଓଡ଼ିଆ"
        )
    }

    /**
     * The microphone-type foreground service may only start once RECORD_AUDIO is granted — on Android 14 a fresh
     * install crashed with SecurityException the first time the talk screen opened (every earlier test pre-granted).
     */
    private fun startPtt() {
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) return
        val svc = Intent(this, PttService::class.java)
        if (Build.VERSION.SDK_INT >= 26) startForegroundService(svc) else startService(svc)
    }

    /** Grants land after start(): BtTransport bails without BLUETOOTH_CONNECT, PttService needs RECORD_AUDIO. */
    override fun onRequestPermissionsResult(code: Int, perms: Array<out String>, res: IntArray) {
        super.onRequestPermissionsResult(code, perms, res)
        startPtt()
        bt.start()
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
