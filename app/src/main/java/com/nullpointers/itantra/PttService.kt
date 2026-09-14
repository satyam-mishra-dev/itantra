package com.nullpointers.itantra

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder

/**
 * Foreground service (microphone type) — keeps the mic + sockets alive while
 * walkie-talkie mode is on. Modern Android kills background mic access without
 * this; every stale sample app dies here (idea doc §10 risk 5).
 */
class PttService : Service() {

    override fun onCreate() {
        super.onCreate()
        val chId = "itantra_ptt"
        if (Build.VERSION.SDK_INT >= 26) {
            val nm = getSystemService(NotificationManager::class.java)
            nm.createNotificationChannel(
                NotificationChannel(chId, "iTantra walkie-talkie", NotificationManager.IMPORTANCE_LOW)
            )
        }
        val n: Notification = (if (Build.VERSION.SDK_INT >= 26)
            Notification.Builder(this, chId) else @Suppress("DEPRECATION") Notification.Builder(this))
            .setContentTitle("iTantra walkie-talkie active")
            .setContentText("Listening for push-to-talk and incoming messages")
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .build()
        try {
            if (Build.VERSION.SDK_INT >= 30) {
                startForeground(1, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE)
            } else {
                startForeground(1, n)
            }
        } catch (e: SecurityException) {   // mic permission revoked while running: degrade, never crash the app
            stopSelf()
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int = START_STICKY

    override fun onBind(intent: Intent?): IBinder? = null
}
