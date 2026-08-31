"""Assert-based checks for linksim.py. Run: python test_linksim.py"""
import linksim as ls

n = 0


def check(cond, msg):
    global n
    assert cond, msg
    n += 1


turns = ls.conversation()
check(8 <= len(turns) <= 20, f'conversation size {len(turns)}')
check(turns[-1][0] <= ls.CONV_SECONDS, 'conversation fits 60 s')

# LoRa airtime formula sanity: 45 B at SF9 ≈ 0.3 s (firmware README), SF12 > SF9 > SF7
sf7, sf9, sf12 = ls.BEARERS[2], ls.BEARERS[1], ls.BEARERS[0]
check(0.25 < sf9.airtime(45) < 0.35, f'SF9 airtime {sf9.airtime(45):.3f}')
check(sf12.airtime(45) > sf9.airtime(45) > sf7.airtime(45), 'airtime grows with SF')

# encodings order: VarnaCode < UTF-8 < Codec2 < AMR in bytes and hence in latency, on every bearer
for b in ls.BEARERS:
    lats = [sum(ls.simulate(b, e)['lat']) / len(turns) for e in ('VarnaCode', 'UTF-8', 'Codec2-450', 'AMR-NB')]
    check(lats == sorted(lats), f'{b.name}: latency not monotonic in payload size {lats}')

# more bitrate → less latency (non-LoRa bearers, same encoding)
plain = [b for b in ls.BEARERS if b.sf is None]
lat_by_bps = [(b.bps, sum(ls.simulate(b, 'VarnaCode')['lat']) / len(turns)) for b in plain]
lat_by_bps.sort()
check(all(lat_by_bps[i][1] >= lat_by_bps[i + 1][1] for i in range(len(lat_by_bps) - 1)),
      f'latency should fall with bitrate: {lat_by_bps}')

# text keeps real time on the 300 bps dying link; AMR audio cannot
dying = next(b for b in ls.BEARERS if b.name.startswith('dying'))
check(ls.sustainable(ls.simulate(dying, 'VarnaCode')), 'VarnaCode on 300 bps should keep up')
check(not ls.sustainable(ls.simulate(dying, 'AMR-NB')), 'AMR on 300 bps must backlog')
free = next(b for b in ls.BEARERS if 'no duty' in b.name)
check(ls.sustainable(ls.simulate(free, 'VarnaCode')) and ls.sustainable(ls.simulate(free, 'UTF-8')), 'duty-free LoRa SF7 keeps up with text')
check(not ls.sustainable(ls.simulate(ls.BEARERS[2], 'VarnaCode')), '1% duty SF7 cannot keep 10 sentences/min')

# ARQ: lossless delivery under 20% loss, with retransmits counted, and no retx at 0% loss
b0 = ls.Bearer('t', 1200, 50, 0.0, 0.0, 128)
r0 = ls.simulate(b0, 'VarnaCode')
check(r0['sent'] == r0['useful'], 'no retransmits without loss')
b20 = ls.Bearer('t', 1200, 50, 0.20, 0.0, 128)
r20 = ls.simulate(b20, 'VarnaCode', seed=3)
check(len(r20['lat']) == len(turns), 'every sentence delivered under 20% loss')
check(r20['sent'] > r20['useful'], 'retransmits happened under loss')
check(sum(r20['lat']) > sum(r0['lat']), 'loss costs latency')
# BER-only loss also triggers ARQ
rb = ls.simulate(ls.Bearer('t', 1200, 50, 0.0, 1e-3, 128), 'VarnaCode', seed=4)
check(rb['sent'] > rb['useful'], 'BER-induced retransmits')
# no ARQ ⇒ never retransmits
check(ls.simulate(b20, 'VarnaCode', arq=False)['sent'] == r0['useful'], 'arq=False sends each packet once')

# duty cycle: LoRa SF9 rests 99× airtime
check(abs(sf9.off_time(0.3) - 29.7) < 1e-9, 'duty off-time')

print(f'OK — {n} linksim assertions passed')
