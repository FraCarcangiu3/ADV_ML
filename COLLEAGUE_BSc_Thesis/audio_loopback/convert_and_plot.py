#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path
import shlex
from typing import Sequence

import numpy as np
import soundfile as sf

DEFAULT_SOURCE = Path("Data/audio/audio_loopback_flac")
DEFAULT_DESTINATION = Path("Data/audio/test")
SPARKS = " .:-=+*#%@"


def normalize_uuid(raw: str) -> str:
    raw = raw.strip()
    if not raw:
        raise ValueError("Empty UUID provided.")
    if raw.startswith("audio_event_"):
        return raw
    return f"audio_event_{raw}"


def resolve_source_path(source_root: Path, uuid: str) -> Path:
    normalized = normalize_uuid(uuid)
    candidate = source_root / f"{normalized}.flac"
    if not candidate.exists():
        raise FileNotFoundError(f"FLAC not found: {candidate}")
    return candidate


def ascii_waveform(samples: np.ndarray, width: int = 80) -> str:
    if samples.ndim > 1:
        samples = samples.mean(axis=1)
    if len(samples) == 0:
        return "[empty signal]"
    indexes = np.linspace(0, len(samples) - 1, num=width, dtype=int)
    slice_values = samples[indexes]
    max_abs = float(np.max(np.abs(slice_values))) or 1.0
    normalized = slice_values / max_abs
    chars = []
    for value in normalized:
        idx = int(((value + 1) / 2) * (len(SPARKS) - 1))
        idx = max(0, min(len(SPARKS) - 1, idx))
        chars.append(SPARKS[idx])
    return "".join(chars)


def process_uuid(
    uuid: str,
    source_root: Path,
    destination_root: Path,
    width: int,
) -> None:
    source_path = resolve_source_path(source_root, uuid)
    data, samplerate = sf.read(source_path, dtype="float32")
    waveform = ascii_waveform(data, width=width)
    relative_name = source_path.stem + ".wav"
    destination_root.mkdir(parents=True, exist_ok=True)
    destination_path = destination_root / relative_name
    sf.write(destination_path, data, samplerate)
    print(
        f"\n🎯 {source_path.name}\n"
        f"   Duration: {len(data) / samplerate:.2f}s | Sample rate: {samplerate}\n"
        f"   Waveform: {waveform}\n"
        f"   Saved WAV → {destination_path}"
    )


def convert_many(
    uuids: Sequence[str],
    source_root: Path,
    destination_root: Path,
    width: int,
) -> int:
    processed = 0
    for uuid in uuids:
        try:
            process_uuid(uuid, source_root, destination_root, width)
            processed += 1
        except Exception as exc:  # pylint: disable=broad-except
            print(f"\n❌ {uuid}: {exc}")
    if processed:
        print(
            f"\nCompleted conversion for {processed} file(s). Output root: {destination_root}"
        )
    return processed


def interactive_loop(
    source_root: Path,
    destination_root: Path,
    width: int,
) -> None:
    print(
        "\nInteractive mode ready. Commands:\n"
        "  convert <uuid1> [uuid2 ...]  Convert and preview one or more UUIDs\n"
        "  help                         Show this message again\n"
        "  quit/exit                    Leave the program\n"
    )
    while True:
        try:
            raw = input("command> ").strip()
        except EOFError:
            print("\nExiting.")
            break
        if not raw:
            continue
        if raw.lower() in {"quit", "exit"}:
            print("Bye!")
            break
        if raw.lower() == "help":
            print(
                "Commands:\n"
                "  convert <uuid1> [uuid2 ...]  Convert and preview UUIDs sequentially\n"
                "  help                         Show this message again\n"
                "  quit/exit                    Leave the program\n"
            )
            continue
        try:
            tokens = shlex.split(raw)
        except ValueError as exc:
            print(f"Could not parse command: {exc}")
            continue
        if not tokens:
            continue
        command, *args = tokens
        if command.lower() == "convert":
            if not args:
                print("Please provide at least one UUID after 'convert'.")
                continue
            convert_many(args, source_root, destination_root, width)
        else:
            print(f"Unknown command '{command}'. Type 'help' for instructions.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Print an ASCII waveform preview for selected FLAC UUIDs and convert each file to WAV, "
            "saving them under the 'test' directory (configurable)."
        )
    )
    parser.add_argument(
        "uuids",
        nargs="*",
        help="UUIDs or filenames (with/without the 'audio_event_' prefix) to process immediately.",
    )
    parser.add_argument(
        "--uuid-file",
        action="append",
        type=Path,
        default=[],
        help=(
            "Path to a text file containing one UUID or filename per line "
            "(blank lines and lines starting with '#' are ignored). "
            "Can be passed multiple times."
        ),
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=DEFAULT_SOURCE,
        help=f"Folder containing FLAC files (default: {DEFAULT_SOURCE}).",
    )
    parser.add_argument(
        "--destination-root",
        type=Path,
        default=DEFAULT_DESTINATION,
        help=f"Where converted WAVs will be stored (default: {DEFAULT_DESTINATION}).",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=80,
        help="Character width for the ASCII waveform preview (default: 80).",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Start the interactive prompt after processing CLI UUIDs.",
    )
    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="Disable the interactive prompt even if no UUIDs are provided.",
    )
    args = parser.parse_args()

    source_root = args.source_root.resolve()
    destination_root = args.destination_root.resolve()

    def load_uuids_from_file(path: Path) -> list[str]:
        lines: list[str] = []
        for line in path.read_text().splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.endswith(".csv"):
                stripped = stripped[:-4]
            lines.append(stripped)
        return lines

    batch_uuids: list[str] = list(args.uuids)
    for file_path in args.uuid_file:
        if not file_path.exists():
            parser.error(f"UUID file does not exist: {file_path}")
        batch_uuids.extend(load_uuids_from_file(file_path))

    convert_many(batch_uuids, source_root, destination_root, args.width)

    should_run_interactive = (not batch_uuids and not args.no_interactive) or args.interactive
    if should_run_interactive:
        interactive_loop(source_root, destination_root, args.width)
