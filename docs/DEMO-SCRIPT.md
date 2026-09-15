# iTantra — 3-minute stage demo (what the judges see, and what to say)

The trap: on stage it looks like a walkie-talkie. The fix: never let voice be the thing they watch —
make them watch **the number**. Every sentence shows its byte count; the header shows the running
"× smaller than a voice call". The pitch is that number, everything else is proof.

## One line
"Voice that travels as text — 45 bytes a sentence, in ten Indian languages, over any link that
still works when the towers don't."

## Why it is not a walkie-talkie (say this in the first 20 seconds)
| walkie-talkie / phone call | iTantra |
|---|---|
| analog or 12 kbps voice, gone the moment it is spoken | 45 B text frame, stored and forwarded until it is heard — ✓ when delivered |
| one language, the listener must understand the speaker | speaker talks in Hindi, listener hears it in Odia (phrase frames) — 9 bytes |
| range = one radio hop | phones relay for each other (flood relay, 3 hops), Wi-Fi hotspot, Bluetooth, LoRa, even an old analog radio (AFSK) |
| anyone with the frequency listens in | AES-GCM with a team key |
| nothing measured | Evaluation screen: CER, latency, bytes — live, on the phone |

## The 3-minute run (two phones, hotspot on phone A, no internet)
| t | do | say |
|---|---|---|
| 0:00 | A: open app, entry screen | "Ten languages. Zero towers. Watch the number in the header." |
| 0:20 | A: hold, say a Hindi sentence, release | "That sentence just became **45 bytes**. A voice call would have been 8 kilobytes." (stats strip updates live) |
| 0:40 | B: plays it aloud | "Heard on the other phone, offline, under a second." |
| 1:00 | A: turn ALERT on, say "तुरंत निकलें" | "Priority frame: B goes to full volume, cuts in mid-message, plays twice, restores." |
| 1:20 | A: say "बारह लोग घायल हैं" → tap "send as phrase · 9 B"; B is set to Odia | "Same meaning, **9 bytes**, and B hears it in *its* language. No translation model — a shared phrasebook." |
| 1:45 | B: turn Wi-Fi off; A: send two sentences; B: Wi-Fi on | "Nothing is lost. Store-and-forward, acknowledged when B is back." (✓ appears) |
| 2:15 | B: Evaluate → HOLD TO READ, read the sentence | "Character error rate measured live — not a slide." |
| 2:40 | Header | "N sentences, X bytes, Z× smaller than a call. That is the whole idea: send the meaning, not the sound." |

## Numbers you may quote (all measured, sources in p0/RESULTS.md and app/TESTING.md)
45 B/sentence · 169× smaller than an AMR-NB cellular call · VarnaCode 4.45–5.4 bits/char (beats Unishox2 7.3–7.8, SCSU 8.2–8.7) ·
Hindi real-speech CER 2.9 % · receive → first audio 0.3–1 s on a phone · int8 STT pack 140 MB, RTF 0.7 on a Realme · AFSK frame 0.3 s of audio,
works at 6 dB SNR, Reed–Solomon buys ≈2 dB · relay +9 B/hop · encryption +28 B/frame · location +7 B.

## Don't
Don't demo Bluetooth pairing live (Settings UI, slow). Don't type — the typed box only exists for languages without a pack.
Don't say "889× vs cellular" (that is vs raw G.711). Don't promise 22 languages: the codebooks are trained for these ten.
