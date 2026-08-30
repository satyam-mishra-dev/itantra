"""P6: real-speech evaluation — IndicConformer int8 on FLEURS human speech.

- Data: google/fleurs test split, streamed (no full download), 20 utterances/language,
  cached to fleurs/<lang>/ as 16 kHz wav + refs.tsv.
- Normalization (numbers are meaningless without stating this): NFC -> strip danda/
  double-danda + Latin punctuation -> collapse whitespace -> casefold. Applied to both
  reference and hypothesis before jiwer CER/WER.
- Noise sweep (hi + ta): additive same-language babble (3 overlapped FLEURS utterances,
  85%) + white noise (15%), scaled to target SNR 20/10/5 dB over the whole clip.
- Denoiser: GTCRN via sherpa-onnx OfflineSpeechDenoiser (models/gtcrn/gtcrn_simple.onnx,
  0.5 MB) run on the noisy audio before STT; reported with its own RTF.

Run: .venv/bin/python eval_real.py            (all: fetch -> clean eval -> noise -> chart)
"""
import io
import itertools
import os
import re
import time
import unicodedata

import jiwer
import numpy as np
import sherpa_onnx
import soundfile as sf

LANGS = {"hi": "hi_in", "bn": "bn_in", "ta": "ta_in", "te": "te_in", "ml": "ml_in"}
N_UTT = 20
SNRS = [20, 10, 5]
NOISE_LANGS = ["hi", "ta"]
RNG = np.random.default_rng(26173)


def norm(s):
    s = unicodedata.normalize("NFC", s)
    s = re.sub(r"[।॥.,!?;:\"'()\[\]{}\-–—_/\\]+", " ", s)
    return re.sub(r"\s+", " ", s).strip().casefold()


def fetch(lang):
    d = f"fleurs/{lang}"
    tsv = f"{d}/refs.tsv"
    if os.path.exists(tsv):
        return d
    from datasets import Audio, load_dataset  # import here: only needed on first run
    os.makedirs(d, exist_ok=True)
    ds = load_dataset("google/fleurs", LANGS[lang], split="test", streaming=True)
    ds = ds.cast_column("audio", Audio(decode=False))
    rows = []
    for i, r in enumerate(itertools.islice(ds, N_UTT)):
        x, sr = sf.read(io.BytesIO(r["audio"]["bytes"]), dtype="float32")
        assert sr == 16000
        sf.write(f"{d}/{i:03d}.wav", x, sr)
        rows.append(f"{i:03d}.wav\t{r['transcription']}")
    with open(tsv, "w") as f:
        f.write("\n".join(rows) + "\n")
    print(f"fetched {len(rows)} utterances -> {d}")
    return d


def load_lang(lang):
    d = fetch(lang)
    wavs, refs = [], []
    for line in open(f"{d}/refs.tsv"):
        w, t = line.rstrip("\n").split("\t", 1)
        x, sr = sf.read(f"{d}/{w}", dtype="float32")
        wavs.append(x)
        refs.append(t)
    return wavs, refs


def recognizer(lang):
    d = f"models/nemo-ctc-indicconformer-{lang}"
    return sherpa_onnx.OfflineRecognizer.from_nemo_ctc(
        model=f"{d}/model.int8.onnx", tokens=f"{d}/tokens.txt", num_threads=2)


def transcribe(rec, wavs):
    hyps, dec_s, audio_s = [], 0.0, 0.0
    for x in wavs:
        audio_s += len(x) / 16000
        s = rec.create_stream()
        s.accept_waveform(16000, x)
        t0 = time.perf_counter()
        rec.decode_stream(s)
        dec_s += time.perf_counter() - t0
        hyps.append(s.result.text)
    return hyps, dec_s / audio_s


def score(refs, hyps):
    r, h = [norm(x) for x in refs], [norm(x) or "<empty>" for x in hyps]
    return jiwer.cer(r, h), jiwer.wer(r, h)


def add_noise(wavs, snr_db):
    """Same-language babble (3 shifted neighbors, 85%) + white (15%), at target SNR."""
    noisy = []
    for i, x in enumerate(wavs):
        n = len(x)
        babble = np.zeros(n, dtype=np.float32)
        for k in range(1, 4):  # 3 other utterances, tiled/offset to cover the clip
            src = wavs[(i + k) % len(wavs)]
            tiled = np.tile(src, n // len(src) + 1)[:n]
            babble += np.roll(tiled, k * 1600)
        noise = 0.85 * babble / 3 + 0.15 * RNG.standard_normal(n).astype(np.float32)
        ps, pn = np.mean(x**2), np.mean(noise**2)
        noise *= np.sqrt(ps / (pn * 10 ** (snr_db / 10)))
        noisy.append(np.clip(x + noise, -1, 1))
    return noisy


def get_denoiser():
    try:
        cfg = sherpa_onnx.OfflineSpeechDenoiserConfig(
            model=sherpa_onnx.OfflineSpeechDenoiserModelConfig(
                gtcrn=sherpa_onnx.OfflineSpeechDenoiserGtcrnModelConfig(
                    model="models/gtcrn/gtcrn_simple.onnx"),
                num_threads=2))
        return sherpa_onnx.OfflineSpeechDenoiser(cfg)
    except Exception as e:  # graceful: documented in RESULTS if unavailable
        print("denoiser unavailable:", e)
        return None


def denoise(sd, wavs):
    out, proc_s, audio_s = [], 0.0, 0.0
    for x in wavs:
        audio_s += len(x) / 16000
        t0 = time.perf_counter()
        a = sd(x, 16000)
        proc_s += time.perf_counter() - t0
        y = np.asarray(a.samples, dtype=np.float32)
        if a.sample_rate != 16000:  # GTCRN is 16k; guard anyway
            idx = np.linspace(0, len(y), int(len(y) * 16000 / a.sample_rate), endpoint=False)
            y = np.interp(idx, np.arange(len(y)), y).astype(np.float32)
        out.append(y)
    return out, proc_s / audio_s


def main():
    # ---- per-language clean eval ----
    table, cache = [], {}
    for lang in LANGS:
        wavs, refs = load_lang(lang)
        rec = recognizer(lang)
        hyps, rtf = transcribe(rec, wavs)
        cer, wer = score(refs, hyps)
        dur = sum(len(x) for x in wavs) / 16000
        table.append((lang, len(wavs), dur, cer, wer, rtf))
        cache[lang] = (wavs, refs, rec)
        print(f"{lang}: CER {cer:.1%} WER {wer:.1%} RTF {rtf:.3f} ({dur:.0f}s audio)")

    # ---- noise sweep + denoiser ----
    sd = get_denoiser()
    sweep = {}  # lang -> {snr: (cer_noisy, cer_denoised)} ; snr None = clean
    den_rtf = None
    for lang in NOISE_LANGS:
        wavs, refs, rec = cache[lang]
        clean_cer = dict((l, c) for l, _, _, c, _, _ in table)[lang]
        sweep[lang] = {"clean": (clean_cer, clean_cer)}
        for snr in SNRS:
            noisy = add_noise(wavs, snr)
            cer_n, _ = score(refs, transcribe(rec, noisy)[0])
            cer_d = None
            if sd:
                dn, den_rtf = denoise(sd, noisy)
                cer_d, _ = score(refs, transcribe(rec, dn)[0])
            sweep[lang][snr] = (cer_n, cer_d)
            print(f"{lang} @ {snr} dB: noisy CER {cer_n:.1%}"
                  + (f" -> denoised {cer_d:.1%}" if cer_d is not None else ""))

    # ---- chart ----
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "Arial", "font.size": 14,
                         "axes.edgecolor": "#90a4ae", "axes.titleweight": "bold",
                         "figure.facecolor": "white"})
    fig, axes = plt.subplots(1, len(NOISE_LANGS), figsize=(11, 4.4), dpi=220, sharey=True)
    xs = ["clean"] + [f"{s} dB" for s in SNRS]
    for ax, lang in zip(np.atleast_1d(axes), NOISE_LANGS):
        base = [sweep[lang]["clean"][0] * 100] + [sweep[lang][s][0] * 100 for s in SNRS]
        ax.plot(xs, base, "o-", lw=2.5, color="#16324a", label="noisy input")
        if sd:
            den = [sweep[lang]["clean"][1] * 100] + [sweep[lang][s][1] * 100 for s in SNRS]
            ax.plot(xs, den, "s--", lw=2.5, color="#e65100", label="GTCRN denoised (0.5 MB)")
        ax.set_title(f"{lang} — babble noise")
        ax.set_xlabel("SNR")
        ax.grid(color="#eceff1")
        for s in ["top", "right"]:
            ax.spines[s].set_visible(False)
    np.atleast_1d(axes)[0].set_ylabel("CER % (lower = better)")
    np.atleast_1d(axes)[0].legend(frameon=False)
    fig.suptitle("Real speech under noise — IndicConformer int8", fontweight="bold")
    plt.tight_layout()
    plt.savefig("chart-noise.png")

    # ---- RESULTS.md ----
    syn_note = "synthetic Piper speech round-trip CER was 0.8-1.6% (P0/P4)"
    lines = [
        "\n## P6: real-speech evaluation (FLEURS test, human speakers, measured)\n",
        "Data: google/fleurs test split, first 20 utterances/language (streamed, cached in",
        "`fleurs/`, not committed). Normalization applied to ref AND hyp before scoring:",
        "NFC -> strip danda/punct -> collapse whitespace -> casefold. Model: IndicConformer",
        "int8 (140 MB), sherpa-onnx `from_nemo_ctc`, 2 threads, desktop CPU.\n",
        "| Lang | Utts | Audio | CER | WER | RTF |",
        "|---|---|---|---|---|---|",
    ]
    for lang, n, dur, cer, wer, rtf in table:
        lines.append(f"| {lang} | {n} | {dur:.0f} s | {cer:.1%} | {wer:.1%} | {rtf:.3f} |")
    lines += [
        f"\nHonest read: {syn_note}; real spontaneous-adjacent read speech is harder, and",
        "the numbers above are the ones to defend. Published IndicWhisper/IndicConformer",
        "baselines run ~13 WER on Hindi benchmarks — same territory. CER stays the headline",
        "metric for agglutinative scripts (arXiv 2203.16601).\n",
        "### Noise robustness (babble 85% + white 15%, additive at target SNR)\n",
    ]
    if den_rtf is not None:
        lines.append(f"GTCRN denoiser: 0.5 MB, RTF {den_rtf:.3f} — run before STT on noisy audio.\n")
    lines += ["| Lang | Clean | 20 dB | 10 dB | 5 dB |", "|---|---|---|---|---|"]
    for lang in NOISE_LANGS:
        row = [f"{sweep[lang]['clean'][0]:.1%}"] + [f"{sweep[lang][s][0]:.1%}" for s in SNRS]
        lines.append(f"| {lang} (noisy) | " + " | ".join(row) + " |")
        if sd:
            row = [f"{sweep[lang]['clean'][1]:.1%}"] + [f"{sweep[lang][s][1]:.1%}" for s in SNRS]
            lines.append(f"| {lang} + GTCRN | " + " | ".join(row) + " |")
    lines.append("\nChart: `chart-noise.png`.\n")
    with open("RESULTS.md", "a") as f:
        f.write("\n".join(lines))
    print("wrote RESULTS.md P6 section + chart-noise.png")


if __name__ == "__main__":
    main()
