#!/usr/bin/env python3

from __future__ import annotations
import argparse
import soundfile as sf
from pathlib import Path
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "Data" / "audio" / "audio_loopback_wav"


def convert_flac_to_wav(
    flac_path: str | Path,
    output_path: Optional[str | Path] = None,
    *,
    overwrite: bool = True,
) -> Path:
    """
    Convert a FLAC file into WAV format.

    Args:
        flac_path: Path to the source .flac file.
        output_path: Destination file path or directory. Defaults to
            PROJECT_ROOT/Data/audio/audio_loopback_wav with the same stem.
        overwrite: Allow overwriting the destination file if it exists.

    Returns:
        Path to the generated .wav file.
    """
    src = Path(flac_path).expanduser()
    if not src.exists():
        raise FileNotFoundError(f"FLAC file not found: {src}")
    if src.suffix.lower() != ".flac":
        raise ValueError(f"Expected a .flac file, got {src.suffix}: {src}")

    if output_path is None:
        dst_dir = DEFAULT_OUTPUT_DIR
        dst = dst_dir / (src.stem + ".wav")
    else:
        dst = Path(output_path).expanduser()
        if dst.is_dir():
            dst = dst / src.with_suffix(".wav").name
        if not dst.suffix or dst.suffix.lower() != ".wav":
            dst = dst.with_suffix(".wav")
    dst = dst.resolve()
    dst.parent.mkdir(parents=True, exist_ok=True)

    if dst.exists() and not overwrite:
        raise FileExistsError(f"Destination already exists: {dst}")

    audio_data, samplerate = sf.read(src)
    sf.write(dst, audio_data, samplerate)

    return dst


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert a FLAC recording to WAV format."
    )
    parser.add_argument(
        "flac_file",
        help="Path to the .flac file that should be converted.",
    )
    parser.add_argument(
        "-o",
        "--output",
        help=(
            "Destination file or directory. Defaults to "
            "Data/audio/audio_loopback_wav/<name>.wav."
        ),
    )
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="Fail instead of overwriting the destination file if it exists.",
    )
    return parser


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()
    dst = convert_flac_to_wav(
        args.flac_file,
        args.output,
        overwrite=not args.no_overwrite,
    )
    print(f"Converted to WAV: {dst}")


if __name__ == "__main__":
    main()
