"""Full-loop smoke test on real models, desktop CPU:
  Hindi text -> Piper VITS TTS -> wav -> Whisper-tiny STT -> text -> CER/WER.
Downloads models to p0/models/ on first run (~140 MB total).
Run: .venv/bin/python pipeline_demo.py
"""
import glob
import os
import re
import tarfile
import time
import urllib.request

import jiwer
import sherpa_onnx
import soundfile as sf

MODELS = 'models'
TTS_URL = ('https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/'
           'vits-piper-hi_IN-pratham-medium.tar.bz2')
STT_URL = ('https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/'
           'sherpa-onnx-whisper-tiny.tar.bz2')

SENTENCES = [
    "चक्रवात तट की ओर बढ़ रहा है।",
    "सभी लोग तुरंत सुरक्षित स्थान पर जाएँ।",
    "राहत नाव सुबह पाँच बजे घाट पर पहुँचेगी।",
    "बिजली के तारों से दूर रहें।",
]


def fetch(url):
    os.makedirs(MODELS, exist_ok=True)
    name = url.rsplit('/', 1)[1]
    tgt = os.path.join(MODELS, name.replace('.tar.bz2', ''))
    if not os.path.isdir(tgt):
        path = os.path.join(MODELS, name)
        if not os.path.exists(path):
            print('downloading', name, '...')
            urllib.request.urlretrieve(url, path)
        with tarfile.open(path) as t:
            t.extractall(MODELS)
        os.remove(path)
    return tgt


def norm(s):
    return re.sub(r'[।.,!?\s]+', ' ', s).strip()


def main():
    tts_dir = fetch(TTS_URL)
    stt_dir = fetch(STT_URL)

    tts = sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(
        model=sherpa_onnx.OfflineTtsModelConfig(
            vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                model=glob.glob(tts_dir + '/*.onnx')[0],
                tokens=tts_dir + '/tokens.txt',
                data_dir=tts_dir + '/espeak-ng-data'),
            num_threads=2)))

    stt = sherpa_onnx.OfflineRecognizer.from_whisper(
        encoder=glob.glob(stt_dir + '/*encoder*.onnx')[0],
        decoder=glob.glob(stt_dir + '/*decoder*.onnx')[0],
        tokens=glob.glob(stt_dir + '/*tokens*.txt')[0],
        language='hi', task='transcribe', num_threads=2)

    rows, refs, hyps = [], [], []
    for i, ref in enumerate(SENTENCES):
        t0 = time.perf_counter()
        audio = tts.generate(ref)
        t_tts = time.perf_counter() - t0
        dur = len(audio.samples) / audio.sample_rate
        sf.write(f'out_{i}.wav', audio.samples, audio.sample_rate)

        t0 = time.perf_counter()
        s = stt.create_stream()
        s.accept_waveform(audio.sample_rate, audio.samples)
        stt.decode_stream(s)
        t_stt = time.perf_counter() - t0
        hyp = s.result.text.strip()

        refs.append(norm(ref))
        hyps.append(norm(hyp))
        rows.append((ref, hyp, dur, t_tts / dur, t_stt / dur))
        print(f'[{i}] dur={dur:.2f}s tts_rtf={t_tts/dur:.3f} stt_rtf={t_stt/dur:.3f}')
        print('  ref:', ref)
        print('  hyp:', hyp)

    cer = jiwer.cer(refs, hyps)
    wer = jiwer.wer(refs, hyps)
    tts_rtf = sum(r[3] for r in rows) / len(rows)
    stt_rtf = sum(r[4] for r in rows) / len(rows)

    def du(d):
        return sum(os.path.getsize(p) for p in glob.glob(d + '/**/*', recursive=True)
                   if os.path.isfile(p)) / 2**20

    out = f"""## Pipeline smoke test (measured on this machine, CPU)

Loop: Hindi text -> Piper VITS (hi_IN-pratham-medium) -> wav -> Whisper-tiny STT (lang=hi) -> text.

| Metric | Value |
|---|---|
| TTS RTF (mean, {len(rows)} sentences) | {tts_rtf:.3f} |
| STT RTF (mean) | {stt_rtf:.3f} |
| CER (TTS+STT round-trip, punctuation-normalized) | {cer:.1%} |
| WER (same) | {wer:.1%} |
| TTS model on disk | {du(tts_dir):.0f} MB |
| STT model on disk | {du(stt_dir):.0f} MB |

*Round-trip CER compounds BOTH engines' errors — per-engine CER is lower. Whisper-tiny
is the placeholder STT; IndicConformer int8 replaces it in P1 (see research/stt.md).*
"""
    print(out)
    with open('RESULTS.md', 'a') as f:
        f.write(out + '\n')


if __name__ == '__main__':
    main()
