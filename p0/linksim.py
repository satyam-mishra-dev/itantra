"""Low-bitrate link simulator — does a 60-second voice conversation keep up in real time?

Pushes the held-out sentences (alternating speakers) through modelled bearers as
(a) VarnaCode frames (b) UTF-8 text frames (c) Codec2-450 audio (d) AMR-NB audio,
with stop-and-wait ARQ (ACK + retransmit) under packet loss / BER.

Bearer model: bitrate, one-way latency, loss %, BER, MTU, LoRa airtime formula +
1% duty cycle (ETSI/IN865 style: after a TX the channel rests 99x its airtime).
Deterministic (seeded). Stdlib + numpy/matplotlib for the chart.
Run: python linksim.py   → tables on stdout + chart-linksim.png
"""
import math
import random

import frame
from bench_compression import TEST, CHARS_PER_SEC

HDR = 6                      # iTantra frame header + CRC
ACK_BYTES = len(frame.pack('', 'hi', frame.ACK, 0))
CONV_SECONDS = 60
PAUSE = 1.0                  # gap between speakers


class Bearer:
    def __init__(self, name, bps, latency_ms=50, loss=0.0, ber=0.0, mtu=200, lora_sf=None, duty=None):
        self.name, self.bps, self.lat = name, bps, latency_ms / 1000
        self.loss, self.ber, self.mtu, self.sf, self.duty = loss, ber, mtu, lora_sf, duty

    def airtime(self, nbytes):
        """Seconds on air for one packet. LoRa uses the Semtech formula (125 kHz, CR 4/5, explicit hdr)."""
        if self.sf is None:
            return nbytes * 8 / self.bps
        bw, sf, cr = 125e3, self.sf, 1
        tsym = (2 ** sf) / bw
        de = 1 if sf >= 11 else 0
        n = 8 + max(math.ceil((8 * nbytes - 4 * sf + 28 + 16) / (4 * (sf - 2 * de))) * (cr + 4), 0)
        return (12.25 + n) * tsym

    def off_time(self, airtime):
        """Regulatory rest after a TX: 1% duty ⇒ 99× the airtime."""
        return airtime * (1 / self.duty - 1) if self.duty else 0.0

    def dropped(self, nbytes, rng):
        p = 1 - (1 - self.loss) * (1 - self.ber) ** (nbytes * 8)
        return rng.random() < p


BEARERS = [
    Bearer('LoRa SF12', 293, 100, mtu=51, lora_sf=12, duty=0.01),
    Bearer('LoRa SF9', 1760, 100, mtu=115, lora_sf=9, duty=0.01),
    Bearer('LoRa SF7', 5470, 100, mtu=222, lora_sf=7, duty=0.01),
    Bearer('LoRa SF7 no duty cap', 5470, 100, mtu=222, lora_sf=7),  # licensed / ISRO-class link
    Bearer('dying link 300 bps', 300, 300, mtu=64),
    Bearer('AFSK 1200 baud', 1200, 50, mtu=128),
    Bearer('GSM CSD 9.6 kbps', 9600, 250, mtu=256),
    Bearer('Bluetooth SPP 100 kbps', 100_000, 30, mtu=990),
]


def conversation():
    """[(t_ready, lang, text, spoken_secs)] — sentences alternate speakers until 60 s are filled."""
    turns, t, i = [], 0.0, 0
    order = [(l, s) for l, ss in TEST.items() for s in ss]
    while True:
        lang, text = order[i % len(order)]
        secs = len(text) / CHARS_PER_SEC.get(lang, 10.0)
        if t + secs > CONV_SECONDS:
            break
        t += secs
        turns.append((t, lang, text, secs))   # ready when the speaker stops (STT finalizes)
        t += PAUSE
        i += 1
    return turns


def packets(enc, lang, text, secs, mtu):
    """Packet sizes (bytes on the wire) for one sentence under an encoding."""
    if enc == 'VarnaCode':
        return [len(frame.pack(text, lang))]
    if enc == 'UTF-8':
        body = len(text.encode('utf-8'))
    elif enc == 'Codec2-450':
        body = math.ceil(secs * 450 / 8)
    elif enc == 'AMR-NB':
        body = math.ceil(secs * 12200 / 8)
    else:
        raise ValueError(enc)
    cap = mtu - HDR
    return [HDR + min(cap, body - i) for i in range(0, body, cap)] if body else [HDR]


def simulate(bearer, enc, seed=0, arq=True, turns=None):
    """Serialize the conversation over the bearer. Returns per-sentence delivery latency,
    time the last byte arrives, packets sent (incl. retransmits) and payload packets."""
    rng = random.Random(seed)
    turns = turns or conversation()
    t_free = 0.0                      # channel becomes usable at
    latencies, sent, useful = [], 0, 0
    last_arrival = 0.0
    for t_ready, lang, text, secs in turns:
        for size in packets(enc, lang, text, secs, bearer.mtu):
            useful += 1
            while True:
                start = max(t_free, t_ready)
                air = bearer.airtime(size)
                sent += 1
                arrival = start + air + bearer.lat
                t_free = start + air + bearer.off_time(air)
                if not arq:
                    break
                lost = bearer.dropped(size, rng)
                ack_air = bearer.airtime(ACK_BYTES)
                if not lost and not bearer.dropped(ACK_BYTES, rng):
                    t_free = max(t_free, arrival + ack_air + bearer.lat)  # sender waits for the ACK
                    break
                # timeout ≈ RTT + ack airtime, then retransmit (data or ACK was lost)
                t_free = max(t_free, start + air + 2 * bearer.lat + ack_air + 0.1)
        latencies.append(arrival - t_ready)
        last_arrival = max(last_arrival, arrival)
    return {'lat': latencies, 'end': last_arrival, 'sent': sent, 'useful': useful, 'n': len(turns)}


def sustainable(r):
    """Real time kept if the last sentence lands within 5 s of the conversation ending."""
    return r['end'] <= CONV_SECONDS + 5


def table():
    encs = ['VarnaCode', 'UTF-8', 'Codec2-450', 'AMR-NB']
    lines = ['| Bearer | Encoding | mean latency | p95 | last byte at | keeps real time? |',
             '|---|---|---|---|---|---|']
    res = {}
    for b in BEARERS:
        for e in encs:
            r = simulate(b, e)
            res[(b.name, e)] = r
            lat = sorted(r['lat'])
            p95 = lat[int(0.95 * (len(lat) - 1))]
            lines.append(f"| {b.name} | {e} | {sum(lat) / len(lat):.1f} s | {p95:.1f} s | "
                         f"{r['end']:.0f} s | {'✓' if sustainable(r) else '✗ backlog ' + format(r['end'] - CONV_SECONDS, '.0f') + ' s'} |")
    return '\n'.join(lines), res


def arq_table():
    lines = ['| Bearer | loss | delivered | packets sent (retx) | mean latency | goodput |',
             '|---|---|---|---|---|---|']
    for b in [BEARERS[1], BEARERS[4], BEARERS[5]]:
        for loss in (0.0, 0.05, 0.10, 0.20):
            bb = Bearer(b.name, b.bps, b.lat * 1000, loss, 0.0, b.mtu, b.sf, b.duty)
            r = simulate(bb, 'VarnaCode', seed=1)
            lat = sum(r['lat']) / len(r['lat'])
            bytes_useful = r['useful'] * 45
            goodput = bytes_useful * 8 / max(r['end'], 1)
            lines.append(f"| {b.name} | {loss:.0%} | {r['n']}/{r['n']} | {r['sent']} (+{r['sent'] - r['useful']}) | "
                         f"{lat:.1f} s | {goodput:.0f} bps |")
    return '\n'.join(lines)


def chart(res, path='chart-linksim.png'):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family': 'Arial', 'font.size': 12, 'axes.edgecolor': '#90a4ae',
                         'axes.titleweight': 'bold', 'figure.facecolor': 'white'})
    colors = {'VarnaCode': '#e65100', 'UTF-8': '#1565c0', 'Codec2-450': '#78909c', 'AMR-NB': '#b0bec5'}
    order = sorted(BEARERS, key=lambda b: b.bps)
    names = [b.name.replace(' ', '\n', 1) for b in order]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5), dpi=200)
    x = range(len(order))
    for e, c in colors.items():
        a1.plot(list(x), [sum(res[(b.name, e)]['lat']) / len(res[(b.name, e)]['lat']) for b in order],
                marker='o', lw=2.2, color=c, label=e)
        a2.bar([i + list(colors).index(e) * 0.2 - 0.3 for i in x],
               [min(res[(b.name, e)]['end'] - CONV_SECONDS, 600) for b in order], width=0.2, color=c, label=e, zorder=3)
    a1.set_yscale('log'); a1.set_xticks(list(x)); a1.set_xticklabels(names, fontsize=9)
    a1.set_ylabel('mean sentence delivery latency (s, log)')
    a1.set_title('One 60-s conversation: latency per bearer')
    a1.grid(axis='y', color='#eceff1'); a1.legend(frameon=False)
    a1.axhline(5, color='#2e7d32', ls='--', lw=1.5); a1.text(0.02, 5.4, 'walkie-talkie usable (< 5 s)', color='#2e7d32', fontsize=10)
    a2.axhline(5, color='#2e7d32', ls='--', lw=1.5)
    a2.set_xticks(list(x)); a2.set_xticklabels(names, fontsize=9)
    a2.set_ylabel('backlog after the conversation ends (s, capped at 600)')
    a2.set_title('Does the link keep up in real time?'); a2.grid(axis='y', color='#eceff1', zorder=0)
    a2.set_yscale('symlog', linthresh=5)
    for a in (a1, a2):
        for s in ['top', 'right']: a.spines[s].set_visible(False)
    plt.tight_layout(); plt.savefig(path); plt.close()


if __name__ == '__main__':
    t, res = table()
    print(f'{len(conversation())} sentences in {CONV_SECONDS} s\n')
    print(t); print(); print(arq_table())
    chart(res)
    print('\nchart-linksim.png written')
