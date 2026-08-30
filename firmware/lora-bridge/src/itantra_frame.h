// iTantra frame parser — mirror of p0/frame.py (keep in sync; parity-tested
// by test_frame_compat.py). Pure C, no Arduino deps, so it compiles on host.
//
// Layout (big-endian):
//   byte 0    : ver(2) | lang(4) | priority(2)
//   byte 1    : seq
//   bytes 2-3 : payload length
//   payload
//   last 2    : CRC-16/CCITT-FALSE over header+payload
#pragma once
#include <stdint.h>
#include <stddef.h>

#define ITANTRA_MAX_FRAME 255  // SX127x FIFO cap; VarnaCode sentences are ~45 B

#define ITANTRA_PRIO_NORMAL 0
#define ITANTRA_PRIO_ALERT  1
#define ITANTRA_PRIO_ACK    2

static inline uint16_t itantra_crc16(const uint8_t *d, size_t n) {
  uint16_t c = 0xFFFF;
  for (size_t i = 0; i < n; i++) {
    c ^= (uint16_t)d[i] << 8;
    for (int b = 0; b < 8; b++)
      c = (c & 0x8000) ? (uint16_t)((c << 1) ^ 0x1021) : (uint16_t)(c << 1);
  }
  return c;
}

// Streaming check at the head of buf[0..n):
//   >0 : complete valid frame of that many bytes
//    0 : incomplete — need more bytes
//   -1 : invalid at head (bad CRC or oversize) — drop a byte and resync
static inline int itantra_frame_check(const uint8_t *buf, size_t n) {
  if (n < 6) return 0;
  uint16_t plen = (uint16_t)((buf[2] << 8) | buf[3]);
  size_t total = 4u + plen + 2u;
  if (total > ITANTRA_MAX_FRAME) return -1;
  if (n < total) return 0;
  uint16_t crc = (uint16_t)((buf[total - 2] << 8) | buf[total - 1]);
  if (itantra_crc16(buf, total - 2) != crc) return -1;
  return (int)total;
}

// Build a payload-less frame (used for the duty-cycle ACK warning). out must
// hold 6 bytes. Returns length (6).
static inline int itantra_frame_mini(uint8_t *out, uint8_t prio, uint8_t seq) {
  out[0] = (uint8_t)(prio & 3);  // ver 0, lang 0 (en), prio
  out[1] = seq;
  out[2] = 0;
  out[3] = 0;
  uint16_t crc = itantra_crc16(out, 4);
  out[4] = (uint8_t)(crc >> 8);
  out[5] = (uint8_t)(crc & 0xFF);
  return 6;
}
