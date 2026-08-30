# P0 — desktop truth pipeline

Measured numbers before any Android code. See `RESULTS.md` for output.

```sh
python3 -m venv .venv && ./.venv/bin/pip install sherpa-onnx onnxruntime jiwer soundfile numpy
./.venv/bin/python test_p0.py            # VarnaCode + frame tests (assert-based)
./.venv/bin/python bench_compression.py  # held-out compression table -> RESULTS.md
./.venv/bin/python pipeline_demo.py      # real TTS->STT loop, downloads ~140MB models -> RESULTS.md
```

- `varnacode.py` — per-language Huffman text coder (escape = 21-bit codepoint, lossless for any string)
- `frame.py` — bearer-agnostic wire frame: ver|lang|prio|seq|len + CRC-16
- Models land in `models/` (gitignored).
