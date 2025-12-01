#!/usr/bin/env python3

import os
import json
import socket
import queue
import soundcard as sc
import numpy as np
import threading
import soundfile as sf
from datetime import datetime


# ANSI colors for status messages
CYAN = "\033[96m"
RESET = "\033[0m"

# === CONFIG ===
PRE_SECONDS = 0.5           # seconds kept before trigger
POST_SECONDS = 1.4            # seconds recorded after trigger
CHUNK_SECONDS = 0.01        # acquisition chunk for low latency ring buffer update
SAMPLERATE = 96000          # Hz
CHANNELS = 8                # channels
UDP_HOST = "0.0.0.0"        # listen on all interfaces
UDP_PORT = 9999             # must match automator
UDP_TOKEN = b"SHOT"         # trigger prefix

OUT_DIR = "Data/audio"
OUT_PREFIX = "audio_event"
def _env_flag(key: str, default: bool) -> bool:
    return os.environ.get(key, str(int(default))).strip().lower() in ("1", "true", "yes", "on")

# Default: FLAC on, WAV off (enable with SAVE_WAV=1 if needed)
SAVE_FLAC = _env_flag("SAVE_FLAC", True)
SAVE_WAV = _env_flag("SAVE_WAV", False)
FLAC_SUBDIR = "audio_loopback_flac"
WAV_SUBDIR = "audio_loopback_wav"

stop_event = threading.Event()

class UdpShotListener(threading.Thread):
    """
    UDP listener that enqueues timestamp strings on trigger.
    Payloads:
      - b"SHOT"                      -> use current UTC time
      - b"SHOT|DD-MM-YYYY_HH-MM-SS"  -> use provided timestamp string
    """
    def __init__(self, host: str, port: int, token: bytes, out_queue: "queue.Queue[str]"):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.token = token
        self.out_queue = out_queue
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.sock.bind((self.host, self.port))
        except OSError as e:
            # Errno 48 on macOS, 98 on Linux: address already in use
            if getattr(e, "errno", None) in (48, 98):
                print(f"[✗] Port {self.port} already in use. Trying another port...")
                self.port = 10000  # Try an alternative port
                self.sock.bind((self.host, self.port))
                print(f"[✓] Now using port {self.port}")
            else:
                raise

    def run(self):
        while not stop_event.is_set():
            try:
                self.sock.settimeout(0.2)
                data, _addr = self.sock.recvfrom(1024)
            except socket.timeout:
                continue
            if not data.startswith(self.token):
                continue
            uuid_str = None
            # Accept either b"SHOT|<uuid>" or b"SHOT|<timestamp>" for compatibility
            if b"|" in data:
                try:
                    uuid_str = data.split(b"|", 1)[1].decode("utf-8").strip()
                except Exception:
                    uuid_str = None
            if not uuid_str:
                # fallback to timestamp, but UUID is preferred
                uuid_str = datetime.utcnow().strftime('%d-%m-%Y_%H-%M-%S')
            self.out_queue.put(uuid_str)

def main():
    if not (SAVE_FLAC or SAVE_WAV):
        raise RuntimeError("At least one of SAVE_FLAC or SAVE_WAV must be True.")
    if SAVE_FLAC:
        os.makedirs(os.path.join(OUT_DIR, FLAC_SUBDIR), exist_ok=True)
    if SAVE_WAV:
        os.makedirs(os.path.join(OUT_DIR, WAV_SUBDIR), exist_ok=True)
    os.makedirs(os.path.join("Data", "Json"), exist_ok=True)
    # Ensure the Json/flac_json directory exists
    os.makedirs(os.path.join("Data", "Json", "flac_json"), exist_ok=True)

    # Select microphone (adjust name if needed)
    mic_name = "Black"
    one_mic = sc.get_microphone(mic_name)
    print(f"[i] Using microphone: {one_mic.name}")

    # Prepare ring buffer
    pre_samples = int(SAMPLERATE * PRE_SECONDS)
    chunk_samples = max(1, int(SAMPLERATE * CHUNK_SECONDS))
    buffer = np.zeros((pre_samples, CHANNELS), dtype=np.float32)

    # Start UDP trigger listener
    trig_q: "queue.Queue[str]" = queue.Queue()
    listener = UdpShotListener(UDP_HOST, UDP_PORT, UDP_TOKEN, trig_q)
    listener.start()
    print(f"[i] Recorder ready. Ring buffer {PRE_SECONDS}s. Listening on udp://0.0.0.0:{UDP_PORT} for {UDP_TOKEN!r}")

    try:
        with one_mic.recorder(samplerate=SAMPLERATE, channels=CHANNELS) as mic:
            print(f"[i] Start streaming. Will save {PRE_SECONDS}s pre + {POST_SECONDS}s post on trigger.")
            while not stop_event.is_set():
                # acquire small chunk and update ring buffer
                data = mic.record(numframes=chunk_samples).astype(np.float32, copy=False)
                if data.ndim == 1:
                    data = data[:, None]
                if data.shape[1] != CHANNELS:
                    # pad or slice to expected channel count
                    if data.shape[1] < CHANNELS:
                        pad = np.zeros((data.shape[0], CHANNELS - data.shape[1]), dtype=np.float32)
                        data = np.concatenate([data, pad], axis=1)
                    else:
                        data = data[:, :CHANNELS]
                buffer = np.roll(buffer, -chunk_samples, axis=0)
                buffer[-chunk_samples:, :] = data[:chunk_samples, :]

                # handle triggers
                try:
                    uuid_str = trig_q.get_nowait()
                except queue.Empty:
                    uuid_str = None

                if uuid_str is not None:
                    post_samples = int(SAMPLERATE * POST_SECONDS)
                    post = mic.record(numframes=post_samples).astype(np.float32, copy=False)
                    if post.ndim == 1:
                        post = post[:, None]
                    if post.shape[1] != CHANNELS:
                        if post.shape[1] < CHANNELS:
                            pad = np.zeros((post.shape[0], CHANNELS - post.shape[1]), dtype=np.float32)
                            post = np.concatenate([post, pad], axis=1)
                        else:
                            post = post[:, :CHANNELS]
                    event_audio = np.vstack([buffer, post])

                    # Normalize and convert to 16-bit PCM
                    event_audio_16bit = (event_audio * 32767.0).clip(-32768, 32767).astype('int16')

                    saved_paths = {}
                    if SAVE_FLAC:
                        flac_filename = f"{OUT_PREFIX}_{uuid_str}.flac"
                        flac_path = os.path.join(OUT_DIR, FLAC_SUBDIR, flac_filename)
                        sf.write(flac_path, event_audio_16bit, SAMPLERATE, subtype='PCM_16')
                        saved_paths["flac"] = flac_path

                    if SAVE_WAV:
                        wav_filename = f"{OUT_PREFIX}_{uuid_str}.wav"
                        wav_path = os.path.join(OUT_DIR, WAV_SUBDIR, wav_filename)
                        sf.write(
                            wav_path,
                            event_audio_16bit,
                            SAMPLERATE,
                            subtype='PCM_16',
                            format="WAV",
                        )
                        saved_paths["wav"] = wav_path

                    primary_path = saved_paths.get("flac") or saved_paths.get("wav")

                    # Save metadata in JSON format under the Json/flac_json directory
                    encoding_label = "flac_file" if "flac" in saved_paths else "wav_file"
                    metadata = {
                        "audio": {
                            "encoding": encoding_label,
                            "file": primary_path,
                            "files": saved_paths,
                            "sr": SAMPLERATE,
                            "channels": CHANNELS
                        }
                    }

                    metadata_filename = f"flac_metadata_{uuid_str}.json"
                    metadata_path = os.path.join("Data", "Json", "flac_json", metadata_filename)
                    with open(metadata_path, 'w') as json_file:
                        json.dump(metadata, json_file, indent=2)

                    formatted_targets = ", ".join(f"{fmt}:{path}" for fmt, path in saved_paths.items())
                    print(f"[✓] Saved event -> {formatted_targets}")
                    print(f"{CYAN}[~] Waiting for the next shot trigger...{RESET}")

    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        print("[i] Recorder exiting.")

if __name__ == "__main__":
    main()
