# Research Proposal: Audio Watermarking and Obfuscation as Anti-Cheat in AssaultCube

## Abstract
This proposal explores the use of audio watermarking and obfuscation as an anti-cheat mechanism in a real game engine (AssaultCube). Building on an analysis of the OpenAL-based client audio subsystem and the network protocol (server→client sound triggers), we propose to evaluate an authenticated and per-user customized audio channel that carries imperceptible yet measurable marks. The goal is not to replace existing anti-cheat measures, but to add a new defensive dimension against pattern-based automation and to enable forensic attribution. The study focuses on feasibility, perceptual impact, robustness to manipulation, and compatibility with the engine.

## Introduction and Context
AssaultCube is an open-source FPS that uses OpenAL for audio playback with a consolidated pipeline for sounds and music. The current architecture relies on: (i) a client-side audio manager responsible for OpenAL initialization, 3D mixing and playback; (ii) network messages that carry sound IDs/triggers from server to client; and (iii) local assets (OGG/WAV) decoded and played through OpenAL.

Project objective: investigate how to extend this subsystem so that audio can carry imperceptible watermarks and light obfuscation, reducing the reliability of audio-driven cheating and enabling post‑event verification/attribution.

### Technical references in the code (to show understanding)
- Audio manager (OpenAL device/context setup, OGG music streaming, source scheduling)
- Sound definitions and categories (ID→asset mapping; weapon, movement, voicecom)
- OpenAL wrappers (sources/buffers, OGG/WAV loading, 3D positioning)
- Network protocol (SV_SOUND / SV_VOICECOM) handled on the client to trigger local playback
These references are used only to frame the discussion; no implementation details or code are proposed here.

## Analysis of the Audio Subsystem
Audio follows an event→trigger→local playback chain:

```
Game event (e.g., shot, footstep, voicecom)
        ↓
      Server (game logic)
        ↓
 Network message (sound ID)
        ↓
 Client: network handler → resolves ID to asset
        ↓
 Decoding (OGG/WAV) → Buffer → OpenAL Source
        ↓
     3D mixing → Device playback
```

- The server sends an ID; the client selects the local asset, decodes, and plays it. 
- Background music is streamed (OGG) with higher priority and double buffering. 
- Sources (weapons, footsteps, ambience) are prioritized and distance-attenuated; channels are scheduled to avoid saturation. 
- The server currently does not send audio content, only triggers/IDs. 

This suggests watermarking/obfuscation should be injected after decoding (PCM) and before mixing, with parameters controlled by the server.

## Motivation for Audio Anti‑Cheat
Modern cheats often rely on audio pattern recognition or on clean audio streams for automation (e.g., alerts). A perfectly reproducible channel makes it easy to train robust classifiers.

Watermarking/obfuscation aims to:
- prevent deterministic recognition of sounds (reducing automation reliability);
- enable forensic attribution (per‑client watermark) from recordings;
- raise the cost of cheat development by forcing watermark removal/neutralization.

The challenge is to balance robustness and imperceptibility while preserving user experience and client compatibility.

## Extension Idea (conceptual, not implementation)
We propose two complementary directions:

1) Client‑side parametric obfuscation
- Apply per‑client, deterministic micro‑transformations (e.g., light pitch, EQ, or phase variations) to PCM after decoding and before mixing.
- Parameters derive from client identity or a server‑shared seed.
- Expected effect: subjectively identical sounds that are not perfectly coincident across clients, reducing automatic recognition.

2) Per‑client watermarking
- Embed a low‑amplitude, wideband (or band‑selective) mark encoding a per‑client/session identifier.
- Robust against resampling, recompression, downmix, and moderate device/driver perturbations.
- Expected effect: attribution from external recordings and support for post‑event verification.

Optional third direction:
- Controlled distribution of audio content: in some cases, deliver server‑controlled assets/variants (leveraging existing autodownload mechanisms), to enable “signed” or parameterized content while preserving caching.

## Validation Plan (qualitative)
We will evaluate perception, robustness, and performance:
- Perception/UX: ABX listening tests, MOS scores; predefined acceptance thresholds.
- Robustness/Anti‑tampering: resistance to resampling, recompression, EQ, mono downmix, loopback/external recording; recovery rate of the mark.
- Performance: added end‑to‑end latency (event→playback), CPU usage in the audio thread, stability under load (many concurrent sources).
- Compatibility: mixed sessions with modified vs legacy clients.

Key metrics (indicative): added latency (ms), minimum MOS (>4/5), watermark recognition rate (>90% clean, >80% degraded), CPU overhead (<5%).

## Open Questions and Challenges
- Psychoacoustic modeling: which masking effects to exploit to maximize imperceptibility and robustness?
- Parameterization: how to ensure per‑client distinctiveness with low collision, across noisy and heterogeneous devices?
- Secure parameter channel: authenticated, MITM‑resistant distribution without over‑trusting the client.
- Interaction with 3D mixing: ensure Doppler/attenuation/reassignments do not annihilate the mark.
- Forensic protocol: attribution while minimizing privacy risks and false positives.
- Portability: how broadly this applies to other OpenAL‑based engines.

Advisors’ expertise would be most helpful in: DSP/psychoacoustics; network security and keying/attestation; game engine integration.

## Conclusions and Next Steps
We propose an incremental path to introduce audio watermarking/obfuscation in a real engine, with attention to compatibility, perceived quality, and robustness. Next steps: select one or two techniques, define a lightweight parameter distribution protocol, and set up qualitative/quantitative experiments. Feedback from advisors will guide method selection, acceptance criteria, and prototype planning.
