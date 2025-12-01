#!/usr/bin/env python3

import os
import sys
import queue
import subprocess
import threading
import time
import socket
import signal
import uuid
import csv
import shutil
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
import sys
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pynput import mouse, keyboard
from pynput.keyboard import Controller as KeyboardController
from player_positions.grab_player_position import prune_over_cap, ALL_LABELS_CSV
POSITION_JSON_DIR = PROJECT_ROOT / "Data" / "Json" / "position_json"
MERGED_SAMPLES_JSON_DIR = PROJECT_ROOT / "Data" / "Json" / "merged_samples"
MERGED_SAMPLES_JSON_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_ROOT = PROJECT_ROOT / "Data" / "screenshots"

# ANSI color definitions
YELLOW = "\033[93m"
GREEN = "\033[92m"
BLUE = "\033[94m"
RED = "\033[91m"
CYAN = "\033[96m"
RESET = "\033[0m"

# Define script paths relative to project root
RECORD_SCRIPT = PROJECT_ROOT / "audio_loopback" / "record_audio.py"
SCREENSHOT_SCRIPT = PROJECT_ROOT / "player_positions" / "grab_player_position.py"

TASKS = queue.Queue()
DEBOUNCE_MS = 200
_last_click_ts = 0.0

CLICK_THRESHOLD = 8
_click_counter = 0
KEYBOARD_CONTROLLER = KeyboardController()
LAST_SHOT_STATUS = "No shots yet"

REC_PROC = None  # recorder Popen handle
UDP_HOST = "127.0.0.1"
UDP_PORT = 9999
UDP_TOKEN = b"SHOT"
ANGLE_MICRO_ORDER = ["nnw", "nn", "nne", "wnw", "ww", "wsw", "ssw", "ss", "sse", "ene", "ee", "ese"]
DIST_MACRO_ORDER = ["near", "medium", "far"]
DIST_MICRO_ORDER = [
    "near_1", "near_2", "near_3",
    "medium_1", "medium_2", "medium_3",
    "far_1", "far_2", "far_3",
]
GOAL_PER_PAIR = int(os.environ.get("POSITION_GOAL_PER_PAIR", "9"))
GOAL_PER_MICRO = int(os.environ.get("POSITION_GOAL_PER_MICRO", "81"))
GOAL_PER_DIST_MACRO = int(os.environ.get("POSITION_GOAL_PER_DIST", "324"))
LABEL_CSV_DIR = PROJECT_ROOT / "Data" / "csv" / "labels_csv"
AUDIO_FLAC_DIR = PROJECT_ROOT / "Data" / "audio" / "audio_loopback_flac"
FLAC_JSON_DIR = PROJECT_ROOT / "Data" / "Json" / "flac_json"

def _prepare_keyboard_listener() -> bool:
    """
    Ensure the macOS accessibility check used by pynput is available.
    Some PyObjC builds miss HIServices.AXIsProcessTrusted, which would raise
    a KeyError inside pynput's listener thread. We patch in a safe fallback.
    """
    if sys.platform != "darwin":
        return True
    try:
        import pynput._util.darwin as darwin_util
    except Exception as e:
        print(f"{YELLOW}[!] Cannot load pynput darwin util: {e}. Keyboard listener disabled.{RESET}")
        return False

    hiservices = getattr(darwin_util, "HIServices", None)
    if hiservices is None:
        print(f"{YELLOW}[!] HIServices module unavailable. Keyboard listener disabled.{RESET}")
        return False

    if hasattr(hiservices, "AXIsProcessTrusted"):
        return True

    fallback = getattr(hiservices, "AXIsProcessTrustedWithOptions", None)
    if fallback:
        def _ax_fallback(options=None):
            try:
                return fallback(options)
            except Exception:
                return True

        setattr(hiservices, "AXIsProcessTrusted", _ax_fallback)
        print(f"{YELLOW}[!] Patched missing AXIsProcessTrusted with fallback. Accessibility check may be approximate.{RESET}")
        return True

    setattr(hiservices, "AXIsProcessTrusted", lambda *_, **__: True)
    print(f"{YELLOW}[!] Missing AXIsProcessTrusted; inserted no-op to keep keyboard listener running.{RESET}")
    return True

def execute_shot_tasks(unique_id: str):
    """Wait for audio capture and run minimap grab in parallel threads for a single UUID."""
    threads = [
        threading.Thread(
            name="audio-wait",
            target=wait_for_audio_capture,
            args=(unique_id,),
        ),
        threading.Thread(
            name="screenshot-shot",
            target=run_script,
            args=(SCREENSHOT_SCRIPT, ["--uuid", unique_id]),
        ),
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

def run_script(script_path, args=None):
    """Runs a Python script and streams its output."""
    script_path = Path(script_path)
    args = args or []
    arg_str = "" if not args else " " + " ".join(args)
    print(f"{BLUE}[→] Starting: {script_path.name}{arg_str}{RESET}\n")
    if not script_path.is_file():
        print(f"{RED}[✗] Not found: {script_path}{RESET}\n")
        return
    try:
        cmd = [sys.executable, str(script_path), *args]
        subprocess.run(cmd, check=True)
        print(f"{GREEN}[✓] Finished: {script_path.name}{RESET}\n")
    except subprocess.CalledProcessError as e:
        print(f"{RED}[✗] Error while running {script_path}: {e}{RESET}\n")

def wait_for_audio_capture(unique_id: str, timeout: float = 15.0, poll_interval: float = 0.25):
    """
    Block until the recorder writes the FLAC and metadata files for the UUID.
    Returns when both files exist or when the timeout is reached.
    """
    flac_path = AUDIO_FLAC_DIR / f"audio_event_{unique_id}.flac"
    meta_path = FLAC_JSON_DIR / f"flac_metadata_{unique_id}.json"

    deadline = time.time() + timeout
    while time.time() < deadline:
        if flac_path.exists() and meta_path.exists():
            debug_msg = f"[✓] Audio ready for UUID {unique_id}: {flac_path.name}"
            print(f"{GREEN}{debug_msg}{RESET}")
            return
        time.sleep(poll_interval)
    print(f"{YELLOW}[!] Audio files for UUID {unique_id} not detected within timeout.{RESET}")


def _print_saved_labels(unique_id: str):
    """Print and return status for labels saved for the given UUID."""
    csv_path = LABEL_CSV_DIR / f"labels_{unique_id}.csv"
    if not csv_path.exists():
        msg = f"No labels CSV for {unique_id} (likely skipped/pruned)"
        print(f"{YELLOW}[!] {msg}{RESET}")
        return msg
    try:
        with open(csv_path, newline="") as f:
            rows = list(csv.reader(f))
            if len(rows) < 2:
                msg = f"CSV {csv_path.name} has no data rows"
                print(f"{YELLOW}[!] {msg}{RESET}")
                return msg
            header, data = rows[0], rows[1]
            def _get(name, default=None):
                try:
                    idx = header.index(name)
                    return data[idx]
                except ValueError:
                    return default
            angle = _get("angle_deg")
            dist = _get("distance_px")
            angle_micro = _get("angle_micro")
            angle_macro = _get("angle_macro")
            dist_micro = _get("distance_micro")
            dist_macro = _get("distance_macro")
            msg = (f"Saved labels for {unique_id}: "
                   f"angle={angle} ({angle_macro}/{angle_micro})  "
                   f"distance={dist} ({dist_macro}/{dist_micro})")
            print(f"{BLUE}[→] {msg}{RESET}")
            return msg
    except Exception as e:
        msg = f"Cannot read {csv_path.name}: {e}"
        print(f"{YELLOW}[!] {msg}{RESET}")
        return msg


def send_shot_udp(payload: bytes):
    """Send UDP trigger to recorder (2s pre + 2s post). Handles port conflicts by trying 9999 then 10000."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.sendto(payload, (UDP_HOST, UDP_PORT))
            print(f"{BLUE}[→] Sent trigger to udp://{UDP_HOST}:{UDP_PORT} ({payload!r}){RESET}")
        except OSError as e:
            # Try alternative port if port 9999 is in use
            if getattr(e, "errno", None) in (48, 98):
                alt_port = 10000
                try:
                    sock.sendto(payload, (UDP_HOST, alt_port))
                    print(f"{BLUE}[→] Sent trigger to udp://{UDP_HOST}:{alt_port} ({payload!r}){RESET}")
                except Exception as ex2:
                    print(f"{RED}[✗] Failed to send trigger to alt port {alt_port}: {ex2}{RESET}")
            else:
                print(f"{RED}[✗] Failed to send trigger: {e}{RESET}")
        finally:
            sock.close()
    except Exception as e:
        print(f"{RED}[✗] Failed to send trigger: {e}{RESET}")


def probe_position():
    """Capture once (no audio trigger) and print current macro/micro categories."""
    print(f"{BLUE}[→] Probe request: capturing minimap (no audio) ...{RESET}")
    try:
        run_script(SCREENSHOT_SCRIPT, ["--probe"])
    except Exception as e:
        print(f"{RED}[✗] Probe failed: {e}{RESET}")


def _count_labels(csv_dir: Path, label_order: list[str], column_name: str) -> dict[str, int]:
    """
    Count occurrences of a label column from combined label CSVs.
    Expects a header row; falls back to positional columns if missing.
    """
    counts = {k: 0 for k in label_order}
    if not csv_dir.exists():
        return counts
    for csv_path in csv_dir.glob("labels_*.csv"):
        try:
            with open(csv_path, newline="") as f:
                rows = list(csv.reader(f))
                if len(rows) < 2:
                    continue
                header, data = rows[0], rows[1]
                try:
                    idx = header.index(column_name)
                except ValueError:
                    idx = 0
                val = data[idx].strip() if idx < len(data) else None
                if val in counts:
                    counts[val] += 1
        except Exception as e:
            print(f"{YELLOW}[!] Cannot read {csv_path.name}: {e}{RESET}")
    return counts


def _count_pair_matrix(csv_dir: Path, angle_order: list[str], dist_micro_order: list[str]) -> dict[str, dict[str, int]]:
    """
    Count occurrences for each (angle_micro, distance_micro) pair.
    Returns a nested dict angle -> dist_micro -> count.
    """
    matrix = {a: {d: 0 for d in dist_micro_order} for a in angle_order}
    if not csv_dir.exists():
        return matrix
    for csv_path in csv_dir.glob("labels_*.csv"):
        try:
            with open(csv_path, newline="") as f:
                rows = list(csv.reader(f))
                if len(rows) < 2:
                    continue
                header, data = rows[0], rows[1]
                try:
                    a_idx = header.index("angle_micro")
                    d_idx = header.index("distance_micro")
                except ValueError:
                    continue
                angle = data[a_idx].strip() if a_idx < len(data) else None
                dist = data[d_idx].strip() if d_idx < len(data) else None
                if angle in matrix and dist in matrix.get(angle, {}):
                    matrix[angle][dist] += 1
        except Exception as e:
            print(f"{YELLOW}[!] Cannot read {csv_path.name}: {e}{RESET}")
    return matrix


def prune_labels_over_cap():
    """Invoke pruning from grab_player_position to enforce caps before reporting."""
    pruned = prune_over_cap(LABEL_CSV_DIR, ALL_LABELS_CSV, screenshots_root=SCREENSHOTS_ROOT)
    if pruned:
        removed_list = ", ".join(pruned)
        print(f"{YELLOW}[~] Pruned {len(pruned)} old sample(s) to respect caps: {removed_list}{RESET}")


def report_dataset_balance():
    """Print current balance vs goal for angle/distance labels (macro & micro grid)."""
    prune_labels_over_cap()
    angle_counts = _count_labels(LABEL_CSV_DIR, ANGLE_MICRO_ORDER, "angle_micro")
    dist_counts = _count_labels(LABEL_CSV_DIR, DIST_MACRO_ORDER, "distance_macro")
    pair_matrix = _count_pair_matrix(LABEL_CSV_DIR, ANGLE_MICRO_ORDER, DIST_MICRO_ORDER)

    def _table(counts, order, title, goal):
        rows = []
        header = f"{title:<8} | {'done':>4} | {'missing':>7}"
        rows.append(header)
        rows.append("-" * len(header))
        for k in order:
            c = counts.get(k, 0)
            missing = max(0, goal - c)
            rows.append(f"{k:<8} | {c:>4} | {missing:>7}")
        return "\n".join(rows)

    # Last shot status
    print(f"{BLUE}[→] Last shot:{RESET} {LAST_SHOT_STATUS}")

    # Matrix per angle_micro x distance_micro
    header_cells = ["angle/dist"] + [f"{d:^7}" for d in DIST_MICRO_ORDER]
    header_line = " | ".join(header_cells)
    rows = [header_line, "-" * len(header_line)]
    for idx, angle in enumerate(ANGLE_MICRO_ORDER):
        cells = []
        for dist in DIST_MICRO_ORDER:
            c = pair_matrix.get(angle, {}).get(dist, 0)
            if c >= GOAL_PER_PAIR:
                cells.append(f"{GREEN}{c:>2}/{GOAL_PER_PAIR:<2}{RESET}")
            else:
                cells.append(f"{c:>2}/{GOAL_PER_PAIR:<2}")
        rows.append(f"{angle:<9} | " + " | ".join(cells))
        if (idx + 1) % 3 == 0 and idx + 1 < len(ANGLE_MICRO_ORDER):
            rows.append("-" * len(header_line))
    print(f"{BLUE}[→] Pair balance (goal {GOAL_PER_PAIR} per angle_micro×distance_micro):{RESET}\n" + "\n".join(rows))


def cleanup_audio_if_needed(unique_id: str):
    """
    If labels CSV was skipped for this UUID, delete the corresponding audio/metadata.
    """
    labels_csv = LABEL_CSV_DIR / f"labels_{unique_id}.csv"
    if labels_csv.exists():
        return

    flac_path = AUDIO_FLAC_DIR / f"audio_event_{unique_id}.flac"
    meta_path = FLAC_JSON_DIR / f"flac_metadata_{unique_id}.json"
    shot_dir = SCREENSHOTS_ROOT / f"minimap_{unique_id}"
    removed = []
    for p in [flac_path, meta_path]:
        if p.exists():
            try:
                p.unlink()
                removed.append(p.name)
            except Exception as e:
                print(f"{YELLOW}[!] Could not delete {p}: {e}{RESET}")
    if shot_dir.exists():
        try:
            shutil.rmtree(shot_dir)
            removed.append(str(shot_dir))
        except Exception as e:
            print(f"{YELLOW}[!] Could not delete screenshots {shot_dir}: {e}{RESET}")
    if removed:
        print(f"{YELLOW}[!] CSV skipped; removed audio artifacts for {unique_id}: {', '.join(removed)}{RESET}")

def worker():
    while True:
        unique_id = TASKS.get()
        try:
            # Execute both capture tasks concurrently for this UUID
            execute_shot_tasks(unique_id)
            print(f"{CYAN}[✓] Both tasks completed for UUID {unique_id}!{RESET}")
            status = _print_saved_labels(unique_id)
            global LAST_SHOT_STATUS
            if status:
                LAST_SHOT_STATUS = status
            else:
                LAST_SHOT_STATUS = f"No labels for {unique_id} (analysis failed or pruned; see logs)"
            print(f"{CYAN}[~] Waiting for the next shot trigger...{RESET}")
            report_dataset_balance()
            cleanup_audio_if_needed(unique_id)
        finally:
            TASKS.task_done()

def main():
    global REC_PROC
    print(f"{YELLOW}=== Automator: persistent recorder + click-to-capture ==={RESET}\n")
    if not RECORD_SCRIPT.is_file():
        print(f"{RED}[✗] Recorder not found: {RECORD_SCRIPT}{RESET}\n")
        return
    # Prune and show current balance before starting
    prune_labels_over_cap()
    report_dataset_balance()
    # Launch recorder once (ring buffer + UDP trigger)
    REC_PROC = subprocess.Popen([sys.executable, str(RECORD_SCRIPT)])
    print(f"{GREEN}[✓] Recorder started (PID {REC_PROC.pid}). Triggers will save 4s events.{RESET}\n")
    print(f"{YELLOW}Left-click sends trigger; screenshot queued with the SAME UUID.{RESET}\n")

def on_click(x, y, button, pressed):
    from pynput.mouse import Button
    global _last_click_ts, _click_counter
    if pressed and button == Button.left:
        now = time.time() * 1000.0
        if now - _last_click_ts < DEBOUNCE_MS:
            return
        _last_click_ts = now
        # Generate a new UUID for each click
        unique_id = str(uuid.uuid4())
        payload = UDP_TOKEN + b"|" + unique_id.encode("utf-8")
        send_shot_udp(payload)
        TASKS.put(unique_id)  # Queue the UUID instead of the timestamp
        print(f"\n{CYAN}🖱️ Left click! Trigger + screenshot scheduled for UUID {unique_id} (queue={TASKS.qsize()}).{RESET}\n")
        _click_counter += 1
        if _click_counter >= CLICK_THRESHOLD:
            try:
                time.sleep(2)
                KEYBOARD_CONTROLLER.press("r")
                KEYBOARD_CONTROLLER.release("r")
                print(f"{GREEN}[✓] Auto-pressed 'r' after {CLICK_THRESHOLD} clicks. Counter reset.{RESET}")
            except Exception as e:
                print(f"{RED}[✗] Failed to auto-press 'r': {e}{RESET}")
            finally:
                _click_counter = 0


def on_key_press(key):
    try:
        if key == keyboard.Key.enter:
            probe_position()
    except Exception:
        pass

def _shutdown(*_args):
    print(f"\n{YELLOW}Shutting down...{RESET}")
    try:
        if REC_PROC and REC_PROC.poll() is None:
            REC_PROC.terminate()
            try:
                REC_PROC.wait(timeout=3)
            except subprocess.TimeoutExpired:
                REC_PROC.kill()
    except Exception:
        pass
    os._exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)
    t = threading.Thread(target=worker, daemon=True)
    t.start()
    main()
    key_listener = None
    try:
        if _prepare_keyboard_listener():
            key_listener = keyboard.Listener(on_press=on_key_press)
            key_listener.start()
        else:
            print(f"{YELLOW}[!] Keyboard listener disabled; Enter probe shortcut unavailable.{RESET}")
        with mouse.Listener(on_click=on_click) as listener:
            listener.join()
        if key_listener:
            key_listener.stop()
            key_listener.join()
    except KeyboardInterrupt:
        _shutdown()
