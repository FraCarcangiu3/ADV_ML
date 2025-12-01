# AssaultCube Audio Subsystem – Technical Documentation (EN)

## Introduction and Objectives
This document analyzes the AssaultCube audio subsystem and outlines extensions to support audio obfuscation and watermarking for anti‑cheat purposes. It summarizes code locations, architecture, server→client flow, proposed protocol extensions, security considerations, and a test plan – in a form suitable for research and engineering review.

## Code Scan (Summary)
Command patterns used: grep/find on sound/audio keywords, formats (.ogg/.wav), OpenAL calls, and protocol messages (SV_SOUND/SV_VOICECOM). Assets are located under packages/audio/.

## Audio Architecture (High‑Level)
```
Game event → Server trigger (SV_SOUND/SV_VOICECOM) → Network message (sound ID)
→ Client handler → Audio manager (playsound) → Buffer loader (OGG/WAV)
→ OpenAL source → Mixer → Audio device
```
Client holds all audio assets locally; server sends IDs only.

## Server→Client Flow
- Current model: ID triggers; no audio content sent over the network.
- Limitation: hard to personalize/secure; enables external pattern recognition.
- Proposal: optional authenticated streaming for selected assets; per‑client param/seed delivery for obfuscation/watermarking.

## Proposed Extension (Concept)
- New control messages for audio file delivery (chunked) or for parameter distribution.
- Per‑client obfuscation (light pitch/EQ/phase) after decoding, before mixing.
- Per‑client watermark (wideband or band‑selective) to enable attribution.
- Backward compatibility via capability flags and full fallback to legacy triggers.

## Security and Anti‑Tamper (Concept)
- HMAC per chunk; signed control messages; periodic key rotation.
- Logging and telemetry for timing anomalies and suspected audio hooking.

## Test Plan (Qualitative)
- UX (MOS/ABX), robustness to resampling/recompression/downmix/recordings, performance (latency/CPU), compatibility (mixed clients). Targets: added latency <50–100 ms; CPU overhead <5%; detection >90% (clean) and >80% (moderate degradation).

## Glossary (Selected)
Sampling rate; FFT; HMAC; Chunking; Watermarking; Spread‑spectrum; OpenAL; OGG Vorbis; Anti‑tamper.

## References
OpenAL 1.1 Specification; Digital watermarking literature; Game security references.
