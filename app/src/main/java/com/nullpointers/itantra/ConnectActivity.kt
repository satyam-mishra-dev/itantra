package com.nullpointers.itantra

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView

/**
 * "Connect by IP" dialog shared by both screens. Shows this phone's own address — the other
 * side has to type it, and users had no way to see it — and prefills the hotspot host (.1).
 */
fun Activity.askIp(onOk: (String) -> Unit) {
    val me = NsdTransport.myIp()
    val guess = me?.substringBeforeLast('.')?.let { "$it.1" }?.takeIf { it != me } ?: "192.168.43.1"
    val box = EditText(this).apply {
        hint = getString(R.string.connect_hint)
        setText("$guess:${NsdTransport.FIXED_PORT}")
    }
    AlertDialog.Builder(this)
        .setTitle(R.string.connect_button)
        .setMessage(getString(R.string.this_phone, me ?: "no Wi-Fi"))
        .setView(box)
        .setPositiveButton(android.R.string.ok) { _, _ -> onOk(box.text.toString()) }
        .setNegativeButton(android.R.string.cancel, null)
        .show()
}

/** Entry hero: pick a language, then find peers (NSD) or connect by IP. The talk screen owns the transports. */
class ConnectActivity : Activity() {

    private var sel = 1 // Hindi
    private val chips = ArrayList<TextView>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_connect)
        val row = findViewById<LinearLayout>(R.id.langRow)
        val d = resources.displayMetrics.density
        for ((i, name) in MainActivity.LANG_NAMES.withIndex()) {
            val c = TextView(this).apply {
                text = name
                textSize = 15f
                typeface = resources.getFont(R.font.outfit_semibold)
                setBackgroundResource(R.drawable.lang_chip)
                setPadding((18 * d).toInt(), (10 * d).toInt(), (18 * d).toInt(), (10 * d).toInt())
                layoutParams = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT
                ).apply { marginEnd = (8 * d).toInt() }
                setOnClickListener { select(i) }
            }
            chips += c
            row.addView(c)
        }
        select(sel)
        findViewById<View>(R.id.findPeers).setOnClickListener { launch(null) }
        findViewById<View>(R.id.connectIpLink).setOnClickListener { askIp { launch(it) } }
    }

    private fun select(i: Int) {
        sel = i
        for ((j, c) in chips.withIndex()) {
            c.isSelected = j == i
            c.setTextColor(getColor(if (j == i) R.color.navy else R.color.onHero))
        }
    }

    private fun launch(ip: String?) {
        startActivity(Intent(this, MainActivity::class.java).putExtra("lang", sel).putExtra("ip", ip))
        finish()
    }
}
