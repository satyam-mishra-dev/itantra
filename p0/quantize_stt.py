"""P4: int8 dynamic quantization of the converted IndicConformer NeMo-CTC model,
with before/after measurement using the exact sherpa-onnx OfflineRecognizer
config the Android app uses.

Run: .venv/bin/python quantize_stt.py [modeldir]   (default models/nemo-ctc-indicconformer-hi)
"""
import os
import re
import sys
import time

import jiwer
import onnx
import sherpa_onnx
import soundfile as sf
from onnxruntime.quantization import QuantType, quantize_dynamic

MODELDIR = sys.argv[1] if len(sys.argv) > 1 else 'models/nemo-ctc-indicconformer-hi'
FP32 = os.path.join(MODELDIR, 'model.onnx')
INT8 = os.path.join(MODELDIR, 'model.int8.onnx')
TOKENS = os.path.join(MODELDIR, 'tokens.txt')

SENTENCES = [
    "चक्रवात तट की ओर बढ़ रहा है।",
    "सभी लोग तुरंत सुरक्षित स्थान पर जाएँ।",
    "राहत नाव सुबह पाँच बजे घाट पर पहुँचेगी।",
    "बिजली के तारों से दूर रहें।",
]
WAVS = [f'out_{i}.wav' for i in range(4)]


def norm_dev(s):
    return re.sub(r'[।.,!?\s]+', ' ', s).strip()


def copy_metadata(src_path, dst_path):
    src = onnx.load(src_path, load_external_data=False)
    dst = onnx.load(dst_path)
    have = {p.key for p in dst.metadata_props}
    for p in src.metadata_props:
        if p.key not in have:
            q = dst.metadata_props.add()
            q.key, q.value = p.key, p.value
    onnx.save(dst, dst_path)
    return sorted(p.key for p in onnx.load(dst_path, load_external_data=False).metadata_props)


def measure(model_path):
    t0 = time.perf_counter()
    rec = sherpa_onnx.OfflineRecognizer.from_nemo_ctc(
        model=model_path, tokens=TOKENS, num_threads=2)  # same config family as app
    load_s = time.perf_counter() - t0
    hyps, audio_s, dec_s = [], 0.0, 0.0
    for w in WAVS:
        samples, sr = sf.read(w, dtype='float32')
        audio_s += len(samples) / sr
        s = rec.create_stream()
        s.accept_waveform(sr, samples)
        t = time.perf_counter()
        rec.decode_stream(s)
        dec_s += time.perf_counter() - t
        hyps.append(s.result.text)
    cer = jiwer.cer([norm_dev(r) for r in SENTENCES], [norm_dev(h) for h in hyps])
    return dict(load_s=load_s, rtf=dec_s / audio_s, cer=cer, hyps=hyps,
                mb=os.path.getsize(model_path) / 1e6)


if __name__ == '__main__':
    if not os.path.exists(INT8):
        print('quantizing (dynamic int8, weights only) ...')
        t = time.perf_counter()
        quantize_dynamic(FP32, INT8, weight_type=QuantType.QInt8)
        print(f'quantized in {time.perf_counter()-t:.0f}s')
    keys = copy_metadata(FP32, INT8)
    print('int8 metadata keys:', keys)

    fp = measure(FP32)
    q8 = measure(INT8)
    cer_vs_fp32 = jiwer.cer([norm_dev(h) for h in fp['hyps']],
                            [norm_dev(h) for h in q8['hyps']])
    print(f"\n| Model | Size MB | Load s | RTF | CER vs ref |")
    print(f"| fp32  | {fp['mb']:.0f} | {fp['load_s']:.1f} | {fp['rtf']:.3f} | {fp['cer']:.1%} |")
    print(f"| int8  | {q8['mb']:.0f} | {q8['load_s']:.1f} | {q8['rtf']:.3f} | {q8['cer']:.1%} |")
    print(f"int8 CER vs fp32 transcripts: {cer_vs_fp32:.1%}")
    for h in q8['hyps']:
        print('int8:', h)
