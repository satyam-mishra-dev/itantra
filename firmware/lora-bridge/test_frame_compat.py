#!/usr/bin/env python3
"""Parity test: C++ itantra_frame.h vs p0/frame.py.

Generates frames with the Python reference, corrupts some, and asserts the
compiled C parser accepts/rejects identically. No hardware needed.
Run: python3 test_frame_compat.py
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'p0'))
import frame  # noqa: E402
from varnacode import LANGS  # noqa: E402

HOST_MAIN = r'''
#include <stdio.h>
#include <string.h>
#include "itantra_frame.h"
int main(void) {
  char line[4096];
  while (fgets(line, sizeof line, stdin)) {
    size_t hexlen = strcspn(line, "\n");
    uint8_t buf[2048]; size_t n = 0;
    for (size_t i = 0; i + 1 < hexlen; i += 2) {
      unsigned v; sscanf(line + i, "%2x", &v); buf[n++] = (uint8_t)v;
    }
    int r = itantra_frame_check(buf, n);
    puts(r == (int)n && n > 0 ? "ACCEPT" : "REJECT");
  }
  return 0;
}
'''


def python_accepts(b):
    try:
        frame.unpack(b)
        return True
    except (ValueError, KeyError, IndexError):
        return False


def main():
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, 'host.c')
        exe = os.path.join(td, 'host')
        with open(src, 'w') as f:
            f.write(HOST_MAIN)
        subprocess.run(['cc', '-I', os.path.join(HERE, 'src'), '-o', exe, src],
                       check=True)

        cases = []
        for lang in LANGS:
            for prio in (frame.NORMAL, frame.ALERT, frame.ACK):
                good = frame.pack('चेतावनी: नदी का जलस्तर बढ़ रहा है' if lang == 'hi'
                                  else 'flood warning at the river bank', lang,
                                  prio, seq=len(cases) & 0xFF)
                cases.append(good)                     # valid
                cases.append(good[:-1])                # truncated
                bad = bytearray(good); bad[5] ^= 0x40  # payload bit flip
                cases.append(bytes(bad))
                bad = bytearray(good); bad[-1] ^= 0xFF  # CRC flip
                cases.append(bytes(bad))
        cases.append(b'')          # empty
        cases.append(b'\x00\x01')  # short
        # C parser caps frames at ITANTRA_MAX_FRAME=255; python doesn't. Only
        # compare within the cap (LoRa/SX127x can't carry >255 B anyway).
        cases = [c for c in cases if len(c) <= 255]

        out = subprocess.run([exe], input='\n'.join(c.hex() for c in cases) + '\n',
                             capture_output=True, text=True, check=True)
        verdicts = out.stdout.split()
        assert len(verdicts) == len(cases), (len(verdicts), len(cases))
        for c, v in zip(cases, verdicts):
            expect = 'ACCEPT' if python_accepts(c) else 'REJECT'
            assert v == expect, f'parity break on {c.hex()}: C={v} py={expect}'
        print(f'parity OK: {len(cases)} cases, C parser == frame.py')


if __name__ == '__main__':
    main()
