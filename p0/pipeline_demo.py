"""Full-loop smoke test on real models, desktop CPU:
  Hindi text -> Piper VITS TTS -> wav -> STT -> text -> CER/WER.

Two STT engines evaluated on the same synthesized wavs:
  1. Whisper-tiny (sherpa-onnx, multilingual) — romanizes Hindi, so raw CER is
     script-mismatched; we also report a transliteration-normalized CER (approx).
  2. Vosk small-hi 0.22 (42 MB) — outputs Devanagari, honest same-script CER.

Downloads models to p0/models/ on first run. Run: .venv/bin/python pipeline_demo.py
"""
import glob
import json
import os
import re
import tarfile
import time
import urllib.request
import zipfile

import jiwer
import numpy as np
import sherpa_onnx
import soundfile as sf
from indic_transliteration import sanscript
from vosk import KaldiRecognizer, Model

MODELS = 'models'
TTS_URL = ('https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/'
           'vits-piper-hi_IN-pratham-medium.tar.bz2')
STT_URL = ('https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/'
           'sherpa-onnx-whisper-tiny.tar.bz2')
VOSK_URL = 'https://alphacephei.com/vosk/models/vosk-model-small-hi-0.22.zip'

SENTENCES = [
    "चक्रवात तट की ओर बढ़ रहा है।",
    "सभी लोग तुरंत सुरक्षित स्थान पर जाएँ।",
    "राहत नाव सुबह पाँच बजे घाट पर पहुँचेगी।",
    "बिजली के तारों से दूर रहें।",
]


def fetch(url):
    os.makedirs(MODELS, exist_ok=True)
    name = url.rsplit('/', 1)[1]
    stem = name.replace('.tar.bz2', '').replace('.zip', '')
    tgt = os.path.join(MODELS, stem)
    if not os.path.isdir(tgt):
        path = os.path.join(MODELS, name)
        if not os.path.exists(path):
            print('downloading', name, '...')
            urllib.request.urlretrieve(url, path)
        if name.endswith('.zip'):
            with zipfile.ZipFile(path) as z:
                z.extractall(MODELS)
        else:
            with tarfile.open(path) as t:
                t.extractall(MODELS)
        os.remove(path)
    return tgt


def norm_dev(s):
    return re.sub(r'[।.,!?\s]+', ' ', s).strip()


def norm_lat(s):
    return re.sub(r'[^a-z0-9 ]+', ' ', s.lower()).strip() or ' '


def to_latin(dev):  # Devanagari -> Harvard-Kyoto, for approximate cross-script CER
    return sanscript.transliterate(dev, sanscript.DEVANAGARI, sanscript.HK)


def resample16k(samples, rate):
    x = np.asarray(samples, dtype=np.float64)
    n = int(len(x) * 16000 / rate)
    return np.interp(np.linspace(0, len(x), n, endpoint=False), np.arange(len(x)), x)


def du(d):
    return sum(os.path.getsize(p) for p in glob.glob(d + '/**/*', recursive=True)
               if os.path.isfile(p)) / 2**20


def main():
    tts_dir = fetch(TTS_URL)
    stt_dir = fetch(STT_URL)
    vosk_dir = fetch(VOSK_URL)

    tts = sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(
        model=sherpa_onnx.OfflineTtsModelConfig(
            vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                model=glob.glob(tts_dir + '/*.onnx')[0],
                tokens=tts_dir + '/tokens.txt',
                data_dir=tts_dir + '/espeak-ng-data'),
            num_threads=2)))

    whisper = sherpa_onnx.OfflineRecognizer.from_whisper(
        encoder=glob.glob(stt_dir + '/*encoder.int8.onnx')[0],
        decoder=glob.glob(stt_dir + '/*decoder.int8.onnx')[0],
        tokens=glob.glob(stt_dir + '/*tokens*.txt')[0],
        language='hi', task='transcribe', num_threads=2)

    vosk = Model(vosk_dir)

    wavs, tts_rtfs = [], []
    for i, ref in enumerate(SENTENCES):
        speak = ref.replace('।', '')  # normalization stage: Piper speaks the danda aloud ("पूर्णविराम") otherwise
        t0 = time.perf_counter()
        audio = tts.generate(speak)
        t_tts = time.perf_counter() - t0
        dur = len(audio.samples) / audio.sample_rate
        tts_rtfs.append(t_tts / dur)
        wavs.append((ref, audio.samples, audio.sample_rate, dur))
        sf.write(f'out_{i}.wav', audio.samples, audio.sample_rate)

    # Whisper-tiny (romanized output -> transliteration-normalized CER, approximate)
    w_hyps, w_rtfs = [], []
    for ref, samples, rate, dur in wavs:
        t0 = time.perf_counter()
        s = whisper.create_stream()
        s.accept_waveform(rate, samples)
        whisper.decode_stream(s)
        w_rtfs.append((time.perf_counter() - t0) / dur)
        w_hyps.append(s.result.text.strip())

    # Vosk small-hi (Devanagari output -> honest same-script CER)
    v_hyps, v_rtfs = [], []
    for ref, samples, rate, dur in wavs:
        t0 = time.perf_counter()
        rec = KaldiRecognizer(vosk, 16000)
        pcm = (np.clip(resample16k(samples, rate), -1, 1) * 32767).astype('<i2').tobytes()
        rec.AcceptWaveform(pcm)
        v_rtfs.append((time.perf_counter() - t0) / dur)
        v_hyps.append(json.loads(rec.FinalResult())['text'])

    refs_dev = [norm_dev(r) for r, *_ in wavs]
    w_cer_translit = jiwer.cer([norm_lat(to_latin(r)) for r in refs_dev],
                               [norm_lat(h) for h in w_hyps])
    v_cer = jiwer.cer(refs_dev, [norm_dev(h) for h in v_hyps])
    v_wer = jiwer.wer(refs_dev, [norm_dev(h) for h in v_hyps])

    for i, (ref, w, v) in enumerate(zip(refs_dev, w_hyps, v_hyps)):
        print(f'[{i}] ref: {ref}\n    whisper: {w}\n    vosk:    {v}')

    mean = lambda xs: sum(xs) / len(xs)
    out = f"""## Pipeline smoke test (measured on this machine, CPU)

Loop: Hindi text -> Piper VITS (hi_IN-pratham-medium) -> wav -> STT -> text, {len(SENTENCES)} sentences.
Round-trip CER compounds BOTH engines' errors (TTS pronunciation + STT recognition) —
per-engine CER on natural speech is lower. Whisper-tiny emits romanized Hindi, so its raw
same-script CER is meaningless; we report a transliteration-normalized approximation.
IndicConformer int8 (native Devanagari, research/stt.md) replaces both in P1.

| Metric | Piper TTS | Whisper-tiny STT | Vosk small-hi STT |
|---|---|---|---|
| RTF (mean) | {mean(tts_rtfs):.3f} | {mean(w_rtfs):.3f} | {mean(v_rtfs):.3f} |
| Round-trip CER | — | ~{w_cer_translit:.0%} (translit-normalized, approx) | {v_cer:.1%} (same-script, honest) |
| Round-trip WER | — | — | {v_wer:.1%} |
| Model on disk | {du(tts_dir):.0f} MB | {du(stt_dir):.0f} MB (fp32+int8) | {du(vosk_dir):.0f} MB |
"""
    print(out)
    with open('RESULTS.md', 'a') as f:
        f.write(out + '\n')


if __name__ == '__main__':
    main()
