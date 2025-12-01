#!/usr/bin/env python3

from __future__ import annotations
from pathlib import Path

import argparse
import matplotlib.pyplot as plt
import numpy as np
import soundfile as sf

try:
    from .flac_to_wav import convert_flac_to_wav
except ImportError:
    from flac_to_wav import convert_flac_to_wav


# Directory containing .flac files (relative to project root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_AUDIO_DIR = PROJECT_ROOT / "Data" / "audio" / "audio_loopback_flac"
TRIMMED_AUDIO_DIR = PROJECT_ROOT / "Data" / "audio" / "trimmed_flac"
WAV_OUTPUT_DIR = PROJECT_ROOT / "Data" / "audio" / "audio_loopback_wav"
CSV_DIR = PROJECT_ROOT / "Data" / "csv" / "audio_loopback_csv"


def has_flac_files(directory: Path) -> bool:
    """Return True if the directory contains at least one .flac file."""
    if not directory.exists() or not directory.is_dir():
        return False
    return any(p.suffix.lower() == ".flac" for p in directory.iterdir())


def list_flac_files(directory: Path) -> list[Path]:
    """Return .flac files sorted by most recent first."""
    return sorted(
        (p for p in directory.iterdir() if p.suffix.lower() == ".flac"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def select_flac_file(files: list[Path]) -> Path:
    """Prompt the user to select one of the available FLAC files."""
    print("Available .flac files (most recent first):")
    for idx, file in enumerate(files, 1):
        print(f"{idx}. {file.name}")

    while True:
        try:
            selection = int(input("Select a file by number: "))
            if 1 <= selection <= len(files):
                return files[selection - 1]
        except ValueError:
            pass
        print("Invalid selection. Please enter one of the listed numbers.")


def plot_waveforms(original_data=None, trimmed_data=None, title: str = "") -> None:
    """Plot the waveform of both versions if present."""
    datasets = []
    if original_data is not None:
        datasets.append(("Original", original_data))
    if trimmed_data is not None:
        datasets.append(("Trimmed", trimmed_data))

    if not datasets:
        print("No waveforms to display.")
        return

    fig, axes = plt.subplots(len(datasets), 1, sharex=True, figsize=(12, 4 * len(datasets)))
    if len(datasets) == 1:
        axes = [axes]

    for ax, (label, data) in zip(axes, datasets):
        ax.plot(data)
        ax.set_title(f"{label} - {title}" if title else label)
        ax.set_xlabel("Samples")
        ax.set_ylabel("Amplitude")

    fig.tight_layout()
    plt.show()


def describe_audio(data: np.ndarray | None, label: str) -> None:
    if data is None:
        print(f"{label}: not available.")
        return
    length = data.shape[0]
    channels = 1 if data.ndim == 1 else data.shape[1]
    print(f"{label}: {length} samples, {channels} channel(s)")


def save_audio_matrix_to_csv(audio_data: np.ndarray, destination: Path) -> Path:
    """Persist the entire audio matrix to a CSV file."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    np.savetxt(destination, audio_data, delimiter=",")
    return destination


def ask_use_trimmed() -> bool:
    """Prompt the user to decide whether to use the trimmed dataset."""
    while True:
        answer = input("Use the trimmed files? [y/N]: ").strip().lower()
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no", ""}:
            return False
        print("Invalid response. Please enter 'y' or 'n'.")


def resolve_audio_directory(source_choice: str | None) -> tuple[Path, bool]:
    """Return the directory to load from and whether it contains trimmed audio."""
    trimmed_available = has_flac_files(TRIMMED_AUDIO_DIR)

    if source_choice == "trimmed":
        if not trimmed_available:
            raise FileNotFoundError(
                f"No trimmed files found in {TRIMMED_AUDIO_DIR}. "
                "Run the trimming script first."
            )
        return TRIMMED_AUDIO_DIR, True
    if source_choice == "original":
        return RAW_AUDIO_DIR, False

    if trimmed_available and ask_use_trimmed():
        return TRIMMED_AUDIO_DIR, True

    return RAW_AUDIO_DIR, False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Play or convert the original FLAC files or the trimmed ones."
    )
    parser.add_argument(
        "--source",
        choices=("original", "trimmed"),
        help="Select the dataset without the interactive prompt.",
    )
    return parser.parse_args()


def counterpart_paths(selected_file: Path, base_dir: Path) -> tuple[Path, Path]:
    """Return the absolute paths of the original and trimmed versions of the file."""
    try:
        relative = selected_file.relative_to(base_dir)
    except ValueError:
        relative = selected_file.name

    raw_path = (RAW_AUDIO_DIR / relative).resolve()
    trimmed_path = (TRIMMED_AUDIO_DIR / relative).resolve()
    return raw_path, trimmed_path


def main() -> None:
    args = parse_args()
    audio_dir, using_trimmed = resolve_audio_directory(args.source)

    if not audio_dir.exists():
        raise FileNotFoundError(f"Directory not found: {audio_dir}")

    flac_files = list_flac_files(audio_dir)
    if not flac_files:
        dataset_label = "trimmed" if using_trimmed else "original"
        raise FileNotFoundError(f"No {dataset_label} .flac files found in {audio_dir}")

    selected_file = select_flac_file(flac_files)

    raw_path, trimmed_path = counterpart_paths(selected_file, audio_dir)

    wav_destination = None
    if using_trimmed:
        trimmed_wav_dir = WAV_OUTPUT_DIR / "trimmed"
        trimmed_wav_dir.mkdir(parents=True, exist_ok=True)
        wav_destination = trimmed_wav_dir

    wav_path = convert_flac_to_wav(selected_file, wav_destination)
    print(f"Converted {selected_file.name} to WAV format: {wav_path}")

    audio_data, samplerate = sf.read(wav_path)
    print(f"Loading {wav_path}...")
    print("Shape:", audio_data.shape)
    print("Data type:", audio_data.dtype)
    print("First values:", audio_data)

    csv_dir = CSV_DIR / ("trimmed" if using_trimmed else "")
    csv_path = csv_dir / (selected_file.stem + ".csv")
    save_audio_matrix_to_csv(audio_data, csv_path)
    print(f"Audio matrix saved to {csv_path}")

    original_data = None
    trimmed_data = None

    if raw_path.exists():
        if using_trimmed:
            original_data, _ = sf.read(raw_path)
        else:
            original_data = audio_data
    else:
        print(f"⚠️ Original version not found: {raw_path}")

    if trimmed_path.exists():
        if using_trimmed:
            trimmed_data = audio_data
        else:
            trimmed_data, _ = sf.read(trimmed_path)
    else:
        print(f"⚠️ Trimmed version not found: {trimmed_path}")

    describe_audio(original_data, "Original")
    describe_audio(trimmed_data, "Trimmed")

    if (
        original_data is not None
        and trimmed_data is not None
        and original_data.ndim == trimmed_data.ndim
        and (original_data.ndim == 1 or original_data.shape[1] == trimmed_data.shape[1])
    ):
        print(
            "✅ Confirmed: trimming only affected the length "
            f"({original_data.shape[0]} -> {trimmed_data.shape[0]} samples)."
        )
    elif original_data is not None and trimmed_data is not None:
        print("⚠️ Warning: channel counts differ between original and trimmed audio.")

    plot_waveforms(original_data, trimmed_data, selected_file.name)


if __name__ == "__main__":
    main()
