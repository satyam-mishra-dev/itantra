package com.nullpointers.itantra

import android.content.Context
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.util.Log
import java.io.DataInputStream
import java.net.ServerSocket
import java.net.Socket
import java.util.concurrent.CopyOnWriteArrayList

/**
 * Peer discovery via NSD/mDNS (_itantra._tcp) + plain TCP sockets.
 * Frames are self-delimiting (length in header), so the read loop needs no
 * extra framing. ponytail: last-peer-wins single mesh hop; multi-hop relay is P5.
 */
class NsdTransport(
    private val ctx: Context,
    private val onFrame: (ByteArray) -> Unit,
    private val onStatus: (String) -> Unit,
) {
    private val tag = "iTantraNsd"
    private val serviceType = "_itantra._tcp."
    private val myName = "iTantra-" + android.os.Build.MODEL.replace(' ', '_') + "-" + (1000..9999).random()
    private val sockets = CopyOnWriteArrayList<Socket>()
    private var server: ServerSocket? = null
    private var nsd: NsdManager? = null
    private var regListener: NsdManager.RegistrationListener? = null
    private var discListener: NsdManager.DiscoveryListener? = null

    fun start() {
        val srv = ServerSocket(0)
        server = srv
        Thread {
            try {
                while (!srv.isClosed) attach(srv.accept())
            } catch (_: Exception) { }
        }.start()

        nsd = ctx.getSystemService(Context.NSD_SERVICE) as NsdManager
        val info = NsdServiceInfo().apply {
            serviceName = myName
            serviceType = this@NsdTransport.serviceType
            port = srv.localPort
        }
        regListener = object : NsdManager.RegistrationListener {
            override fun onServiceRegistered(i: NsdServiceInfo) { onStatus("advertising as $myName") }
            override fun onRegistrationFailed(i: NsdServiceInfo, e: Int) { onStatus("advertise failed: $e") }
            override fun onServiceUnregistered(i: NsdServiceInfo) {}
            override fun onUnregistrationFailed(i: NsdServiceInfo, e: Int) {}
        }
        nsd!!.registerService(info, NsdManager.PROTOCOL_DNS_SD, regListener)

        discListener = object : NsdManager.DiscoveryListener {
            override fun onServiceFound(i: NsdServiceInfo) {
                if (i.serviceName == myName) return
                @Suppress("DEPRECATION")
                nsd!!.resolveService(i, object : NsdManager.ResolveListener {
                    override fun onServiceResolved(r: NsdServiceInfo) {
                        Thread {
                            try {
                                attach(Socket(r.host, r.port))
                                onStatus("connected to ${r.serviceName}")
                            } catch (e: Exception) {
                                Log.w(tag, "connect failed", e)
                            }
                        }.start()
                    }
                    override fun onResolveFailed(r: NsdServiceInfo, e: Int) {}
                })
            }
            override fun onServiceLost(i: NsdServiceInfo) { onStatus("peer lost: ${i.serviceName}") }
            override fun onDiscoveryStarted(t: String) {}
            override fun onDiscoveryStopped(t: String) {}
            override fun onStartDiscoveryFailed(t: String, e: Int) { onStatus("discovery failed: $e") }
            override fun onStopDiscoveryFailed(t: String, e: Int) {}
        }
        nsd!!.discoverServices(serviceType, NsdManager.PROTOCOL_DNS_SD, discListener)
    }

    private fun attach(s: Socket) {
        sockets.add(s)
        Thread {
            try {
                val din = DataInputStream(s.getInputStream())
                val hdr = ByteArray(4)
                while (true) {
                    din.readFully(hdr)
                    val plen = ((hdr[2].toInt() and 0xFF) shl 8) or (hdr[3].toInt() and 0xFF)
                    val rest = ByteArray(plen + 2)
                    din.readFully(rest)
                    onFrame(hdr + rest)
                }
            } catch (_: Exception) {
                sockets.remove(s)
                onStatus("peer disconnected")
            }
        }.start()
    }

    fun send(frame: ByteArray): Int {
        var sent = 0
        for (s in sockets) {
            try {
                s.getOutputStream().apply { write(frame); flush() }
                sent++
            } catch (_: Exception) {
                sockets.remove(s)
            }
        }
        return sent
    }

    fun stop() {
        try { discListener?.let { nsd?.stopServiceDiscovery(it) } } catch (_: Exception) {}
        try { regListener?.let { nsd?.unregisterService(it) } } catch (_: Exception) {}
        try { server?.close() } catch (_: Exception) {}
        for (s in sockets) try { s.close() } catch (_: Exception) {}
        sockets.clear()
    }
}
