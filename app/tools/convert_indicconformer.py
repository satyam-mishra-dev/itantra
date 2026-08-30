#!/usr/bin/env python3
"""Fetch + fix an IndicConformer NeMo-CTC ONNX (trysem/indicconformer-120m-onnx)
so sherpa-onnx can load it — desktop-verified recipe (Hindi: CER 0.0%, RTF 0.054
on the p0 Piper wav):

  1. download <lang>/model.onnx + <lang>/vocab.json
  2. tokens.txt = "token id" per line from vocab.json, then append "<blk> <len>"
     (NeMo CTC blank = last id)
  3. inject ONNX metadata sherpa-onnx requires:
     vocab_size=len+1 · normalize_type=per_feature · subsampling_factor=4 ·
     model_type=EncDecCTCModel
     (subsampling_factor MUST be 4 — 8 silently truncates transcripts)

Usage: python3 convert_indicconformer.py <lang> <outdir> [--int8]
       --int8 also emits model.int8.onnx (dynamic weight quantization, 493->~140 MB,
       measured Hindi: CER 0.8%->1.6%, RTF 0.047->0.059 — sideload this one to phones)
Then:  adb push <outdir>/ /sdcard/Android/data/com.nullpointers.itantra/files/models/<lang>/stt/
Deps:  pip install onnx  (+ onnxruntime for --int8; and curl on PATH)
"""
import json
import os
import subprocess
import sys

import onnx

sys.argv = [a for a in sys.argv if a != '--int8'] if (INT8 := '--int8' in sys.argv) else sys.argv
lang, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
base = f"https://huggingface.co/trysem/indicconformer-120m-onnx/resolve/main/{lang}"

for f in ("model.onnx", "vocab.json"):
    dst = os.path.join(out, f)
    if not os.path.exists(dst):
        print(f"downloading {lang}/{f} ...")
        subprocess.run(["curl", "-sL", "-o", dst, f"{base}/{f}"], check=True)

vocab = json.load(open(os.path.join(out, "vocab.json")))
with open(os.path.join(out, "tokens.txt"), "w") as f:
    for i, t in enumerate(vocab):
        f.write(f"{t} {i}\n")
    f.write(f"<blk> {len(vocab)}\n")

path = os.path.join(out, "model.onnx")
m = onnx.load(path, load_external_data=False)
meta = {"vocab_size": len(vocab) + 1, "normalize_type": "per_feature",
        "subsampling_factor": 4, "model_type": "EncDecCTCModel"}
for k, v in meta.items():
    for p in m.metadata_props:
        if p.key == k:
            p.value = str(v)
            break
    else:
        p = m.metadata_props.add()
        p.key, p.value = k, str(v)
onnx.save(m, path)
print(f"done: {out}/model.onnx + tokens.txt ({len(vocab) + 1} tokens) — sherpa-onnx NeMo-CTC ready")

if INT8:
    from onnxruntime.quantization import QuantType, quantize_dynamic
    q = os.path.join(out, "model.int8.onnx")
    print("quantizing to int8 ...")
    quantize_dynamic(path, q, weight_type=QuantType.QInt8)
    qm = onnx.load(q)
    have = {p.key for p in qm.metadata_props}
    for k, v in meta.items():  # re-inject: quantizer strips custom metadata
        if k not in have:
            p = qm.metadata_props.add()
            p.key, p.value = k, str(v)
    onnx.save(qm, q)
    print(f"done: {q} ({os.path.getsize(q)/1e6:.0f} MB)")
