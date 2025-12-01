# Test Plan - Obfuscated Audio System for AssaultCube

## General Structure
1. Introduction – goals and scope.
2. Test Summary – table of groups.
3. Detailed Test Cases – scenario, setup, steps, success criteria, metrics.
4. Test Tooling – scripts and measurement tools.
5. Evaluation Metrics – key quantitative values.
6. Test Report Structure – standardized report format.
7. Thesis Note – how to use results in the dissertation.

## Introduction
This plan assesses an authenticated audio streaming system with watermarking in AssaultCube. Goals:
1) Core functionality: streaming works and sounds are reproduced correctly;
2) Security: HMAC and signatures protect against tampering;
3) Obfuscation: watermarking techniques are applied correctly;
4) Performance: no noticeable degradation of gameplay;
5) Compatibility: legacy clients continue to work (fallback).

## Test Summary
| Category | Test Case | Objective | Status |
|---|---|---|---|
| Core Functionality | Tests 1–3 | Verify transmission and playback | Pending |
| Security & Integrity | Tests 4–6 | Validate HMAC/signature protections | Pending |
| Obfuscation | Tests 7–9 | Evaluate watermarking techniques | Pending |
| Performance | Tests 10–12 | Measure performance impact | Pending |
| Compatibility | Tests 13–14 | Verify legacy fallback | Pending |
| Integration | Tests 15–16 | Interactions with VoIP | Pending |

(All tests are pending execution.)

## Detailed Test Cases
Follow a uniform template: Scenario; Setup; Steps; Success Criteria; Metrics.

### Test 1: Basic Audio Transmission
Scenario: server sends an audio file; client receives and plays back.
Success: all chunks received, HMAC verified, latency <100 ms.

### Test 2: Missing Chunk Handling
Scenario: simulate packet loss (~10% UDP) and verify retry mechanism.
Success: retransmissions recover missing chunks; final checksum valid.

### Test 3: Network Latency
Scenario: variable delay (50–200 ms). Success: correct ordering; no stutter; max latency <300 ms.

### Test 4: Invalid HMAC Detection
Scenario: MITM alters a chunk; client rejects it and requests retry.

### Test 5: Timing Attack
Scenario: skipped audio updates flagged; event logged; telemetry sent.

### Test 6: Signature Validation
Scenario: tamper with control message (e.g., sample_rate); client rejects.

### Test 7: Pitch‑Shift Watermarking
Scenario: per‑client variations; imperceptible differences; watermark extractable.

### Test 8: EQ‑Based Watermarking
Scenario: filter parameterization per client; extraction feasible.

### Test 9: Spread‑Spectrum Watermarking
Scenario: robust extraction from recordings; imperceptibility preserved.

### Test 10: CPU Overhead
Target: <5% vs baseline; fps stable (>60).

### Test 11: Added Latency
Target: <50 ms vs baseline; consistent across events.

### Test 12: Scalability
Scenario: many concurrent sounds (e.g., 16 players); ordering preserved; latency stable.

### Test 13: Legacy Fallback
Scenario: legacy client with no streaming capability; server falls back to ID triggers.

### Test 14: Mixed Versions
Scenario: half modern, half legacy clients; no interference.

### Test 15–16: VoIP Integration (Discord/TeamSpeak)
Scenario: maintain speech intelligibility; watermark remains detectable on VoIP recordings.

## Test Tooling
- Automation scripts (test_framework/): functionality, security, obfuscation, performance, integration.
- Monitoring tools (monitoring_tools/): CPU, latency, spectrum (FFT), network.

## Evaluation Metrics
Primary: audio latency (ms), CPU overhead (%), watermark detection accuracy (%), security false positives (%).
Secondary: MOS subjective quality (>4.0), robustness after compression/resampling (>85%), legacy compatibility (100%).

## Test Report Structure
Standardized markdown with setup, results, metrics, logs, and conclusions.

## Thesis Note
Use results to produce comparative graphs and quantitative evidence; discuss trade‑offs (quality vs robustness vs performance), limitations, and future optimizations.
