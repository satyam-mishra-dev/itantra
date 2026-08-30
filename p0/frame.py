"""iTantra Frame protocol.

Layout (big-endian):
  byte 0    : ver(2 bits) | lang(4 bits) | priority(2 bits)
  byte 1    : seq (mod 256)
  bytes 2-3 : payload length in bytes
  payload   : VarnaCode-compressed text
  last 2    : CRC-16/CCITT-FALSE over header+payload

Bearer-agnostic: same frame rides TCP, Bluetooth RFCOMM, or LoRa serial.
Stdlib only.
"""
import os
import struct

from varnacode import LANGS, encode, decode

VER = 0
VER_ENC = 2  # version 2 = AES-GCM envelope: payload = nonce(12) + ciphertext + tag(16)
NORMAL, ALERT, ACK = 0, 1, 2


def crc16(data):
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def pack(text, lang, prio=NORMAL, seq=0, key=None, nonce=None):
    payload = encode(text, lang)
    ver = VER
    if key is not None:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        ver = VER_ENC
        nonce = nonce if nonce is not None else os.urandom(12)
        aad = bytes([(ver << 6) | (LANGS.index(lang) << 2) | prio, seq & 0xFF])
        payload = nonce + AESGCM(key).encrypt(nonce, payload, aad)
    if len(payload) > 0xFFFF:
        raise ValueError('payload too large')
    hdr = struct.pack('>BBH', (ver << 6) | (LANGS.index(lang) << 2) | prio, seq & 0xFF, len(payload))
    body = hdr + payload
    return body + struct.pack('>H', crc16(body))


def unpack(frame, key=None):
    if len(frame) < 6:
        raise ValueError('short frame')
    body, crc = frame[:-2], struct.unpack('>H', frame[-2:])[0]
    if crc16(body) != crc:
        raise ValueError('CRC mismatch')
    b0, seq, plen = struct.unpack('>BBH', body[:4])
    if len(body) - 4 != plen:
        raise ValueError('length mismatch')
    lang = LANGS[(b0 >> 2) & 0xF]
    ver = b0 >> 6
    payload = body[4:]
    if ver == VER_ENC:
        if key is None:
            raise ValueError('encrypted frame, key required')
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        try:
            payload = AESGCM(key).decrypt(bytes(payload[:12]), bytes(payload[12:]), bytes(body[:2]))
        except Exception:
            raise ValueError('auth failed')
    return {'ver': ver, 'lang': lang, 'prio': b0 & 3, 'seq': seq,
            'text': decode(payload, lang)}
