package com.nullpointers.itantra

import android.content.Context
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.net.wifi.WifiManager
import android.util.Log
import java.io.DataInputStream
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.Inet4Address
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.NetworkInterface
import java.net.ServerSocket
import java.net.Socket
import java.util.concurrent.CopyOnWriteArrayList

/**
 * Peer discovery + plain TCP sockets. Two discovery paths run side by side because mDNS
 * alone was the field failure ("phones don't connect"): OEM Wi-Fi drivers drop multicast
 * unless a MulticastLock is held, and NsdManager resolve is flaky on hotspots.
 *   1. NSD/mDNS (_itantra._tcp) — the standard path
 *   2. UDP broadcast beacon on BEACON_PORT every 2 s ("ITANTRA name port") — survives most
 *      hotspots where mDNS does not; whoever hears a beacon dials the sender
 * Both paths dial only hosts we have no live socket to. Frames are self-delimiting.
 * ponytail: single mesh hop, last-peer-wins; multi-hop relay is P5.
 */
class NsdTransport(
    private val ctx: Context,
    private val onFrame: (ByteArray) -> Unit,
    private val onStatus: (String) -> Unit,
) : Transport {
    companion object {
        const val FIXED_PORT = 47474
        const val BEACON_PORT = 47475

        /** This phone's site-local IPv4 (Wi-Fi or hotspot), or null — shown so the other side can dial it. */
        fun myIp(): String? = try {
            NetworkInterface.getNetworkInterfaces().toList().flatMap { it.inetAddresses.toList() }
                .firstOrNull { it is Inet4Address && it.isSiteLocalAddress }?.hostAddress
        } catch (_: Exception) { null }
    }
    private val tag = "iTantraNsd"
    private val serviceType = "_itantra._tcp."
    // var: Android may rename the service on a conflict ("… (2)") — onServiceRegistered hands back the real name,
    // and the own-name check must use that or we discover and dial ourselves.
    @Volatile private var myName = "iTantra-" + android.os.Build.MODEL.replace(' ', '_') + "-" + (1000..9999).random()
    private val sockets = CopyOnWriteArrayList<Socket>()
    private var server: ServerSocket? = null
    private var beacon: DatagramSocket? = null
    private var mcast: WifiManager.MulticastLock? = null
    private var nsd: NsdManager? = null
    private var regListener: NsdManager.RegistrationListener? = null
    private var discListener: NsdManager.DiscoveryListener? = null
    @Volatile private var running = false

    override fun start() {
        running = true
        // Without this lock many Wi-Fi chipsets filter multicast/broadcast in firmware → no discovery at all.
        mcast = (ctx.applicationContext.getSystemService(Context.WIFI_SERVICE) as? WifiManager)
            ?.createMulticastLock("itantra")?.apply { setReferenceCounted(false); acquire() }

        // Fixed port so "connect by IP" is predictable; reuseAddress so a quick app restart gets it back.
        val srv = ServerSocket().apply { reuseAddress = true }
        try { srv.bind(InetSocketAddress(FIXED_PORT)) } catch (_: Exception) { srv.bind(InetSocketAddress(0)) }
        server = srv
        Thread {
            try {
                while (!srv.isClosed) srv.accept().let { attach(it, it.inetAddress.hostAddress ?: "peer") }
            } catch (_: Exception) { }
        }.start()

        startNsd(srv.localPort)
        startBeacon(srv.localPort)
    }

    private fun startNsd(port: Int) {
        nsd = ctx.getSystemService(Context.NSD_SERVICE) as NsdManager
        val info = NsdServiceInfo().apply {
            serviceName = myName
            serviceType = this@NsdTransport.serviceType
            this.port = port
        }
        regListener = object : NsdManager.RegistrationListener {
            override fun onServiceRegistered(i: NsdServiceInfo) { myName = i.serviceName; onStatus("advertising as $myName") }
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
                    override fun onServiceResolved(r: NsdServiceInfo) { dial(r.host, r.port, r.serviceName) }
                    override fun onResolveFailed(r: NsdServiceInfo, e: Int) { Log.w(tag, "resolve failed $e — beacon path will dial") }
                })
            }
            // mDNS TTL expiry fires this while the TCP socket is perfectly alive — never report it as a disconnect.
            override fun onServiceLost(i: NsdServiceInfo) { Log.i(tag, "nsd lost ${i.serviceName}") }
            override fun onDiscoveryStarted(t: String) {}
            override fun onDiscoveryStopped(t: String) {}
            override fun onStartDiscoveryFailed(t: String, e: Int) { onStatus("discovery failed: $e") }
            override fun onStopDiscoveryFailed(t: String, e: Int) {}
        }
        nsd!!.discoverServices(serviceType, NsdManager.PROTOCOL_DNS_SD, discListener)
    }

    private fun startBeacon(port: Int) {
        val ds = try {
            DatagramSocket(null).apply { reuseAddress = true; broadcast = true; bind(InetSocketAddress(BEACON_PORT)) }
        } catch (e: Exception) { Log.w(tag, "beacon socket failed", e); return }
        beacon = ds
        val hello = "ITANTRA $myName $port".toByteArray()
        Thread { // announce
            while (running) {
                for (b in broadcastAddrs()) try { ds.send(DatagramPacket(hello, hello.size, b, BEACON_PORT)) } catch (_: Exception) {}
                Thread.sleep(2000)
            }
        }.apply { isDaemon = true }.start()
        Thread { // listen
            val buf = ByteArray(256)
            while (running) {
                try {
                    val p = DatagramPacket(buf, buf.size)
                    ds.receive(p)
                    val parts = String(p.data, 0, p.length).split(' ')
                    if (parts.size == 3 && parts[0] == "ITANTRA" && parts[1] != myName)
                        dial(p.address, parts[2].toIntOrNull() ?: FIXED_PORT, parts[1])
                } catch (_: Exception) { }
            }
        }.apply { isDaemon = true }.start()
    }

    private fun broadcastAddrs(): List<InetAddress> = try {
        NetworkInterface.getNetworkInterfaces().toList().filter { it.isUp && !it.isLoopback }
            .flatMap { it.interfaceAddresses }.mapNotNull { it.broadcast } + InetAddress.getByName("255.255.255.255")
    } catch (_: Exception) { listOf(InetAddress.getByName("255.255.255.255")) }

    private fun connectedTo(host: InetAddress) = sockets.any { it.inetAddress == host }
    private val dialing = java.util.concurrent.ConcurrentHashMap.newKeySet<InetAddress>()

    /** Dial once per host: NSD-resolve and the beacon fire within the same second and used to open 4 sockets to one peer. */
    private fun isMe(host: InetAddress) = host.isLoopbackAddress || try {
        NetworkInterface.getByInetAddress(host) != null
    } catch (_: Exception) { false }

    private fun dial(host: InetAddress, port: Int, label: String) {
        if (isMe(host)) { Log.i(tag, "ignoring own address $host ($label)"); return }
        Log.i(tag, "dial $host:$port ($label)")
        if (connectedTo(host) || !dialing.add(host)) return
        Thread {
            try {
                attach(Socket().apply { connect(InetSocketAddress(host, port), 5000) }, label)
            } catch (e: Exception) { Log.w(tag, "connect $host:$port failed: ${e.message}") }
            finally { dialing.remove(host) }
        }.start()
    }

    /** Both directions announce the peer — the accept() side used to stay on "searching…" while receiving. */
    private fun attach(s: Socket, label: String) {
        sockets.add(s)
        onStatus("connected to $label")
        Thread {
            try {
                pumpFrames(DataInputStream(s.getInputStream()), onFrame)
            } catch (_: Exception) {
                sockets.remove(s)
                try { s.close() } catch (_: Exception) {}
                if (sockets.isEmpty()) onStatus("peer disconnected")   // a duplicate socket dying is not a disconnect
            }
        }.start()
    }

    /** Demo-day fallback when discovery won't cross: dial a peer directly. Retries for a minute — the other app may still be starting. */
    fun manualConnect(hostPort: String) {
        val host = hostPort.substringBefore(':').trim()
        val port = hostPort.substringAfter(':', FIXED_PORT.toString()).trim().toIntOrNull() ?: FIXED_PORT
        Thread {
            var err = "no route"
            for (attempt in 1..20) {
                if (!running) return@Thread
                try {
                    val addr = InetAddress.getByName(host)
                    if (connectedTo(addr)) return@Thread
                    attach(Socket().apply { connect(InetSocketAddress(addr, port), 3000) }, "$host:$port")
                    return@Thread
                } catch (e: Exception) {
                    err = e.message ?: e.javaClass.simpleName
                    onStatus("dialing $host… ($attempt/20)")
                    Thread.sleep(3000)
                }
            }
            onStatus("connect failed: $err")
        }.start()
    }

    override fun send(frame: ByteArray): Int {
        var sent = 0
        for (s in sockets) {
            try {
                s.getOutputStream().apply { write(frame); flush() }
                sent++
            } catch (_: Exception) {
                sockets.remove(s)
                try { s.close() } catch (_: Exception) {}
            }
        }
        return sent
    }

    override fun stop() {
        running = false
        try { discListener?.let { nsd?.stopServiceDiscovery(it) } } catch (_: Exception) {}
        try { regListener?.let { nsd?.unregisterService(it) } } catch (_: Exception) {}
        try { server?.close() } catch (_: Exception) {}
        try { beacon?.close() } catch (_: Exception) {}
        try { mcast?.release() } catch (_: Exception) {}
        for (s in sockets) try { s.close() } catch (_: Exception) {}
        sockets.clear()
    }
}
