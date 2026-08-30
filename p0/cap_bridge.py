"""CAP/SACHET bridge: official alerts re-broadcast into the offline net.

NDMA's SACHET portal (sachet.ndma.gov.in, built on the Common Alerting
Protocol) publishes CAP XML for agency re-dissemination (see /CapFeed and the
agency integration guide). An iTantra gateway node — one phone or LoRa node
that still has internet, or a pre-disaster cache — parses the CAP alert,
picks the local-language <info> block, and broadcasts it as an ALERT frame:
the official warning arrives SPOKEN, in the village's language, on phones
with no connectivity.

Stdlib only. Live feed URL is a parameter (agency feed may need
registration — flagged honestly); tests run on a bundled sample.
"""
import urllib.request
import xml.etree.ElementTree as ET

from frame import pack, ALERT, NORMAL

# CAP language tag -> iTantra lang code
CAP_LANGS = {'hi': 'hi', 'bn': 'bn', 'ta': 'ta', 'te': 'te', 'gu': 'gu',
             'kn': 'kn', 'ml': 'ml', 'mr': 'mr', 'or': 'or', 'en': 'en'}
URGENT_SEVERITIES = {'Extreme', 'Severe'}
MAX_CHARS = 200  # keep the spoken alert one LoRa-frame-ish sized


def _tag(el):
    return el.tag.rsplit('}', 1)[-1]


def _text(parent, name):
    for el in parent.iter():
        if _tag(el) == name and el.text:
            return el.text.strip()
    return ''


def parse_cap(xml_str):
    """CAP 1.2 alert XML -> list of info dicts (one per <info> block)."""
    root = ET.fromstring(xml_str)
    infos = []
    for el in root.iter():
        if _tag(el) == 'info':
            infos.append({
                'language': _text(el, 'language')[:2].lower() or 'en',
                'event': _text(el, 'event'),
                'severity': _text(el, 'severity'),
                'headline': _text(el, 'headline'),
                'description': _text(el, 'description'),
                'instruction': _text(el, 'instruction'),
                'area': _text(el, 'areaDesc'),
            })
    return infos


def spoken_text(info):
    """Hazard -> location -> action, per alert-construction guidance."""
    parts = [info['headline'] or info['event'], info['area'], info['instruction']]
    text = '. '.join(p for p in parts if p)
    return text[:MAX_CHARS]


def to_frame(xml_str, lang_pref='hi', seq=0):
    infos = parse_cap(xml_str)
    if not infos:
        raise ValueError('no <info> blocks')
    info = next((i for i in infos if CAP_LANGS.get(i['language']) == lang_pref),
                infos[0])
    lang = CAP_LANGS.get(info['language'], 'en')
    prio = ALERT if info['severity'] in URGENT_SEVERITIES else NORMAL
    return pack(spoken_text(info), lang, prio=prio, seq=seq), prio


def fetch(url, timeout=15):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read().decode('utf-8', 'replace')


SAMPLE_CAP = '''<?xml version="1.0" encoding="UTF-8"?>
<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
  <identifier>NDMA-IMD-2026-CYCLONE-042</identifier>
  <sender>imd@sachet.ndma.gov.in</sender>
  <status>Actual</status><msgType>Alert</msgType><scope>Public</scope>
  <info>
    <language>en-IN</language>
    <event>Cyclone Warning</event>
    <severity>Extreme</severity>
    <headline>Severe Cyclonic Storm expected to cross coast tonight</headline>
    <description>Wind speeds 110-120 kmph gusting to 135 kmph.</description>
    <instruction>Move to the nearest cyclone shelter immediately.</instruction>
    <area><areaDesc>Balasore and Bhadrak districts, Odisha</areaDesc></area>
  </info>
  <info>
    <language>or-IN</language>
    <event>Cyclone Warning</event>
    <severity>Extreme</severity>
    <headline>Aaji rati prabala batya asuchhi</headline>
    <instruction>Nikatastha batya ashraya sthala ku jaantu.</instruction>
    <area><areaDesc>Balasore, Bhadrak</areaDesc></area>
  </info>
</alert>'''


def demo():
    from frame import unpack
    infos = parse_cap(SAMPLE_CAP)
    assert len(infos) == 2 and infos[0]['severity'] == 'Extreme'
    assert infos[1]['language'] == 'or'
    fr, prio = to_frame(SAMPLE_CAP, lang_pref='or', seq=3)
    assert prio == ALERT
    out = unpack(fr)
    text = out[3] if isinstance(out, tuple) and len(out) > 3 else str(out)
    assert 'batya' in text and 'Balasore' in text
    en_fr, _ = to_frame(SAMPLE_CAP, lang_pref='ta')  # no Tamil block -> falls back
    print(f'cap_bridge ok: 2 info blocks, Odia ALERT frame {len(fr)} B, '
          f'fallback frame {len(en_fr)} B')


if __name__ == '__main__':
    demo()
