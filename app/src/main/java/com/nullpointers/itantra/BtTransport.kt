package com.nullpointers.itantra

import android.Manifest
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothSocket
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import java.io.DataInputStream
import java.util.UUID
import java.util.concurrent.CopyOnWriteArrayList

/**
 * Bluetooth Classic RFCOMM bearer — zero Wi-Fi infra needed; fits the PS's
 * "low bitrate links" framing. Peers must be bonded (paired in Settings) first.
 * ponytail: connects to bonded devices only, no in-app discovery UI — pairing
 * is a one-time Settings step; add discovery when field feedback demands it.
 */
class BtTransport(
    private val ctx: Context,
    private val onFrame: (ByteArray) -> Unit,
    private val onStatus: (String) -> Unit,
) : Transport {
    private val uuid: UUID = UUID.fromString("6a746e74-7261-4001-8000-00805f9b34fb") // "itantra" v1
    private val sockets = CopyOnWriteArrayList<BluetoothSocket>()
    @Volatile private var running = false

    private fun allowed(): Boolean =
        Build.VERSION.SDK_INT < 31 ||
            ctx.checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT) == PackageManager.PERMISSION_GRANTED

    private fun adapter(): BluetoothAdapter? =
        (ctx.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager)?.adapter

    override fun start() {
        val ad = adapter() ?: return
        if (!allowed()) { onStatus("BT: no permission"); return }
        if (!ad.isEnabled) { onStatus("BT off — Wi-Fi only"); return }
        running = true
        Thread { // server
            try {
                val srv = ad.listenUsingRfcommWithServiceRecord("iTantra", uuid)
                while (running) attach(srv.accept())
            } catch (_: Exception) { }
        }.start()
        Thread { // client: try every bonded device once per start
            for (d in try { ad.bondedDevices } catch (_: SecurityException) { emptySet() }) {
                if (!running) break
                try {
                    val s = d.createRfcommSocketToServiceRecord(uuid)
                    s.connect()
                    attach(s)
                } catch (_: Exception) { }
            }
        }.start()
    }

    private fun attach(s: BluetoothSocket) {
        sockets.add(s)
        onStatus("BT connected: " + (try { s.remoteDevice.name } catch (_: SecurityException) { null } ?: s.remoteDevice.address))
        Thread {
            try {
                pumpFrames(DataInputStream(s.inputStream), onFrame)
            } catch (_: Exception) {
                sockets.remove(s)
                onStatus("BT peer disconnected")
            }
        }.start()
    }

    override fun send(frame: ByteArray): Int {
        var sent = 0
        for (s in sockets) {
            try { s.outputStream.apply { write(frame); flush() }; sent++ }
            catch (_: Exception) { sockets.remove(s) }
        }
        return sent
    }

    override fun stop() {
        running = false
        for (s in sockets) try { s.close() } catch (_: Exception) {}
        sockets.clear()
    }
}
