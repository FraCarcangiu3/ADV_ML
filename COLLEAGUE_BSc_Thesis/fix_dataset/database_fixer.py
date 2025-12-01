#!/usr/bin/env python3

"""
Unified toolbox for dataset maintenance tasks:
- Fix angle fields and rename merged JSON files.
- Convert FLAC recordings to CSV (and optionally WAV).
- Export polar labels to per-UUID CSVs.
- Analyze non-zero report outputs.
- Check UUID alignment between audio and merged labels.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable, List

import numpy as np
import soundfile as sf

# ANSI colors for readability
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_RED = "\033[91m"
COLOR_CYAN = "\033[96m"
COLOR_RESET = "\033[0m"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = PROJECT_ROOT / "Data"


def color(text: str, code: str) -> str:
    return f"{code}{text}{COLOR_RESET}"


def prompt_bool(question: str, default: bool = True) -> bool:
    """
    Ask the user a yes/no question. Returns True for yes, False for no.
    """
    suffix = " [Y/n]: " if default else " [y/N]: "
    while True:
        reply = input(color(question + suffix, COLOR_CYAN)).strip().lower()
        if not reply:
            return default
        if reply in {"y", "yes"}:
            return True
        if reply in {"n", "no"}:
            return False
        print(color("Please answer y or n.", COLOR_YELLOW))


def delete_uuid_everywhere(uid: str, data_root: Path = DATA_ROOT) -> None:
    """
    Delete every file under data_root whose name contains the given UUID.
    """
    if not data_root.exists():
        return
    for path in data_root.rglob(f"*{uid}*"):
        if path.is_file():
            try:
                path.unlink()
                print(color(f"🗑️ Removed {path}", COLOR_RED))
            except Exception as exc:
                print(color(f"⚠️ Failed to remove {path}: {exc}", COLOR_YELLOW))

# ----------------------------
# Angle fixing helpers
# ----------------------------

ANGLE_KEY = "angle_deg"


def normalize_angle(raw_value: Any) -> float:
    """Shift angle by 180° and wrap into [0, 360)."""
    return (float(raw_value) + 180.0) % 360.0


def update_angle_fields(payload: Any) -> List[str]:
    """Recursively normalize every field named ANGLE_KEY. Returns dotted paths updated."""
    updated_paths: List[str] = []

    def _walk(node: Any, path: List[str]) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                current_path = path + [key]
                if key == ANGLE_KEY:
                    try:
                        node[key] = normalize_angle(value)
                        updated_paths.append(".".join(current_path))
                    except (TypeError, ValueError):
                        pass
                    continue
                _walk(value, current_path)
        elif isinstance(node, list):
            for idx, value in enumerate(node):
                _walk(value, path + [str(idx)])

    _walk(payload, [])
    return updated_paths


def rename_with_suffix(json_path: Path) -> Path:
    """Ensure file name starts with merged_fixed_ prefix."""
    if json_path.stem.startswith("merged_fixed_"):
        return json_path

    if json_path.stem.startswith("merged_"):
        uuid = json_path.stem[len("merged_") :]
    else:
        uuid = json_path.stem

    target = json_path.with_name(f"merged_fixed_{uuid}.json")
    json_path.rename(target)
    return target


def fix_angles_in_folder(folder_path: Path) -> None:
    folder_path = Path(folder_path)
    if not folder_path.is_dir():
        raise NotADirectoryError(f"{folder_path} is not a directory")

    for json_file in folder_path.rglob("merged*.json"):
        if json_file.name.startswith("merged_fixed_"):
            continue
        with json_file.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

        updated_paths = update_angle_fields(data)
        if not updated_paths:
            continue

        with json_file.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=4)

        new_path = rename_with_suffix(json_file)
        print(f"✅ Fixed {json_file.name} ({', '.join(updated_paths)}) → {new_path.name}")


# ----------------------------
# FLAC to CSV (and WAV) helpers
# ----------------------------

def flac_files(root: Path):
    for file_path in sorted(root.rglob("*.flac")):
        if file_path.is_file():
            yield file_path


def normalize_wav_filters(raw_names: Iterable[str]) -> set[str]:
    filters: set[str] = set()
    for raw_name in raw_names:
        trimmed = str(raw_name).strip()
        if not trimmed:
            continue
        path_like = Path(trimmed)
        filters.add(trimmed)
        filters.add(path_like.name)
        filters.add(path_like.stem)
    return filters


def should_export_as_wav(relative_path: Path, filters: set[str], export_all: bool) -> bool:
    if export_all:
        return True
    if not filters:
        return False
    candidates = {
        relative_path.as_posix(),
        str(relative_path),
        relative_path.name,
        relative_path.stem,
    }
    return any(candidate in filters for candidate in candidates)


def convert_file(
    source: Path,
    source_root: Path,
    destination_root: Path,
    *,
    wav_destination: Path | None = None,
    wav_name_filters: set[str] | None = None,
    export_all_wav: bool = False,
    trim_head: int = 0,
    trim_tail: int = 0,
) -> None:
    data, samplerate = sf.read(source, dtype="float32")
    if trim_head or trim_tail:
        start = min(trim_head, data.shape[0])
        end = data.shape[0] - trim_tail if trim_tail > 0 else data.shape[0]
        end = max(start, end)
        data = data[start:end]
        if data.size == 0:
            print(color(f"⚠️ Skipped {source.name}: trimming removed all samples", COLOR_YELLOW))
            return
    relative = source.relative_to(source_root)
    destination_csv = destination_root / relative.with_suffix(".csv")
    destination_csv.parent.mkdir(parents=True, exist_ok=True)
    np.savetxt(destination_csv, data, delimiter=",", fmt="%.8f")
    print(f"✅ {source} → {destination_csv} (sr={samplerate}, trim_head={trim_head}, trim_tail={trim_tail})")
    filters = wav_name_filters if wav_name_filters is not None else set()
    if should_export_as_wav(relative, filters, export_all_wav):
        wav_root = wav_destination or destination_root
        wav_path = wav_root / relative.with_suffix(".wav")
        wav_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(wav_path, data, samplerate)
        print(f"🎧 {source} → {wav_path} (sr={samplerate})")


def convert_new_flacs(
    root: Path,
    destination: Path,
    *,
    uuids_filter: set[str] | None = None,
    wav_destination: Path | None = None,
    wav_filters: set[str] | None = None,
    export_all_wav: bool = False,
    trim_head: int = 0,
    trim_tail: int = 0,
) -> list[Path]:
    """Convert only FLAC files whose CSV does not yet exist (optionally filtered by UUID)."""
    if not root.exists():
        raise FileNotFoundError(f"The source folder {root} does not exist")
    if not root.is_dir():
        raise NotADirectoryError(f"{root} is not a directory")
    wav_filters = wav_filters or set()
    files = list(flac_files(root))
    created: list[Path] = []
    for file_path in files:
        stem = file_path.stem
        if stem.startswith("audio_event_"):
            uid = stem[len("audio_event_") :]
        else:
            uid = stem
        if uuids_filter is not None and uid not in uuids_filter:
            continue
        relative = file_path.relative_to(root)
        destination_csv = destination / relative.with_suffix(".csv")
        if destination_csv.exists():
            continue
        destination_csv.parent.mkdir(parents=True, exist_ok=True)
        convert_file(
            file_path,
            root,
            destination,
            wav_destination=wav_destination,
            wav_name_filters=wav_filters,
            export_all_wav=export_all_wav,
            trim_head=trim_head,
            trim_tail=trim_tail,
        )
        created.append(destination_csv)
    print(f"Converted {len(created)} new FLAC file(s).")
    return created


# ----------------------------
# Export polar labels helpers
# ----------------------------

DEFAULT_SOURCE = Path("Data/Json/merged_samples")
DEFAULT_DESTINATION = Path("Data/csv/merged_samples_csv")


def extract_angle_distance(json_path: Path) -> tuple[float, float]:
    with json_path.open() as handle:
        payload = json.load(handle)
    polar = payload["position"]["polar_coordinates"]
    angle = float(polar["angle_deg"])
    distance = float(polar["distance_rel"])
    return angle, distance


def destination_for(json_path: Path, destination_root: Path) -> Path:
    try:
        uuid = json_path.stem.split("_", maxsplit=2)[-1]
        if len(uuid) < 10 or uuid == json_path.stem:
            uuid = json_path.stem
    except IndexError:
        uuid = json_path.stem
    return destination_root / f"{uuid}.csv"


def combine_polar_csvs(source_dir: Path, output_csv: Path, include_uuid: bool = False) -> int:
    """
    Merge per-UUID polar CSVs (angle_deg; distance optional) into a single file.
    Useful for reaching a target dataset size (es. ~1200 samples) senza concatenazioni manuali.
    """
    source_dir = Path(source_dir)
    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory does not exist: {source_dir}")
    csv_files = sorted(source_dir.glob("*.csv"))
    if not csv_files:
        print(f"No CSV files found in {source_dir}")
        return 0

    rows: list[list[str]] = []
    has_distance = False
    for csv_path in csv_files:
        if csv_path.name == "all_labels.csv":
            continue
        try:
            with csv_path.open(newline="") as handle:
                reader = list(csv.reader(handle))
        except Exception as exc:
            print(color(f"⚠️ Cannot read {csv_path.name}: {exc}", COLOR_YELLOW))
            continue

        if len(reader) < 2:
            print(color(f"⚠️ Skipping {csv_path.name}: missing data row", COLOR_YELLOW))
            continue
        header, data = reader[0], reader[1]
        if "angle_deg" not in header:
            print(color(f"⚠️ Skipping {csv_path.name}: missing angle_deg column", COLOR_YELLOW))
            continue
        try:
            angle_idx = header.index("angle_deg")
        except ValueError:
            angle_idx = 0
        dist_idx = None
        if "distance_rel" in header:
            has_distance = True
            dist_idx = header.index("distance_rel")

        angle_val = data[angle_idx] if angle_idx < len(data) else ""
        dist_val = data[dist_idx] if dist_idx is not None and dist_idx < len(data) else ""
        uid = csv_path.stem
        if include_uuid:
            row = [uid, angle_val]
            if has_distance:
                row.append(dist_val)
        else:
            row = [angle_val]
            if has_distance:
                row.append(dist_val)
        rows.append(row)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    header_row = ["angle_deg"]
    if has_distance:
        header_row.append("distance_rel")
    if include_uuid:
        header_row = ["uuid"] + header_row
    with output_csv.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header_row)
        writer.writerows(rows)
    print(color(f"✅ Combined {len(rows)} file(s) into {output_csv}", COLOR_GREEN))
    return len(rows)


# ----------------------------
# Merge position + audio metadata helpers
# ----------------------------


def extract_uuid_from_name(stem: str, prefix: str) -> str | None:
    if stem.startswith(prefix):
        return stem[len(prefix) :]
    return None


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def merge_new_samples(
    flac_dir: Path,
    position_dir: Path,
    merged_dir: Path,
    exclude_ids: set[str] | None = None,
) -> list[str]:
    """
    Create merged_{uuid}.json for UUIDs present in both flac_dir and position_dir,
    skipping ones already merged/merged_fixed.
    """
    if not flac_dir.exists():
        print(color(f"[WARN] FLAC metadata dir not found: {flac_dir} (skipping merge)", COLOR_YELLOW))
        return []
    if not position_dir.exists():
        print(color(f"[WARN] Position dir not found: {position_dir} (skipping merge)", COLOR_YELLOW))
        return []

    flac_ids = {
        extract_uuid_from_name(p.stem, "flac_metadata_")
        for p in flac_dir.glob("flac_metadata_*.json")
    }
    flac_ids.discard(None)
    pos_ids = {
        extract_uuid_from_name(p.stem, "position_")
        for p in position_dir.glob("position_*.json")
    }
    pos_ids.discard(None)
    merged_existing = {
        extract_uuid_from_name(p.stem, "merged_")
        for p in merged_dir.glob("merged_*.json")
    }
    merged_existing.update(
        extract_uuid_from_name(p.stem, "merged_fixed_")
        for p in merged_dir.glob("merged_fixed_*.json")
    )
    merged_existing.discard(None)

    intersection = {uid for uid in flac_ids if uid in pos_ids}
    new_ids = intersection - merged_existing
    if exclude_ids:
        new_ids -= exclude_ids

    created: list[str] = []
    merged_dir.mkdir(parents=True, exist_ok=True)
    for uid in sorted(new_ids):
        flac_path = flac_dir / f"flac_metadata_{uid}.json"
        pos_path = position_dir / f"position_{uid}.json"
        try:
            flac_payload = load_json(flac_path)
            pos_payload = load_json(pos_path)
            merged_payload = {
                "id": uid,
                "position": pos_payload,
                "audio": flac_payload.get("audio", {}),
                "source_files": {
                    "position": pos_path.name,
                    "audio_metadata": flac_path.name,
                },
            }
            out_path = merged_dir / f"merged_{uid}.json"
            with out_path.open("w", encoding="utf-8") as handle:
                json.dump(merged_payload, handle, indent=4)
            created.append(uid)
            print(f"✅ Merged {uid} -> {out_path.name}")
        except Exception as exc:
            print(f"⚠️ Failed to merge {uid}: {exc}")
            continue
    return created


def export_new_polar_files(
    source_dir: Path,
    destination_dir: Path,
    with_header: bool = True,
    uuids_filter: set[str] | None = None,
) -> list[Path]:
    """Export angle/distance for merged_fixed JSONs that do not yet have a CSV. Optionally filter by UUID."""
    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory does not exist: {source_dir}")
    json_files = sorted(source_dir.glob("merged_fixed_*.json"))
    destination_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for json_file in json_files:
        uid = json_file.stem[len("merged_fixed_") :] if json_file.stem.startswith("merged_fixed_") else json_file.stem
        if uuids_filter is not None and uid not in uuids_filter:
            continue
        csv_path = destination_for(json_file, destination_dir)
        if csv_path.exists():
            continue
        try:
            angle, distance = extract_angle_distance(json_file)
            with csv_path.open("w", newline="") as handle:
                writer = csv.writer(handle)
                if with_header:
                    writer.writerow(["angle_deg", "distance_rel"])
                writer.writerow([f"{angle}", f"{distance}"])
        except Exception as exc:
            print(f"⚠️ {exc}")
            continue
        written.append(csv_path)
        print(f"✅ {json_file.name} → {csv_path.name}")
    print(f"Created {len(written)} new polar CSV file(s).")
    return written


# ----------------------------
# UUID alignment helpers
# ----------------------------

def extract_from_flac(path: Path) -> str | None:
    stem = path.stem
    if stem.startswith("audio_event_"):
        return stem[len("audio_event_") :]
    return stem or None


def extract_from_merged(path: Path) -> str | None:
    stem = path.stem
    if stem.startswith("merged_fixed_"):
        return stem[len("merged_fixed_") :]
    if stem.startswith("merged_"):
        return stem[len("merged_") :]
    return stem or None


def gather_ids(root: Path, pattern: str, extractor) -> set[str]:
    ids: set[str] = set()
    for file_path in root.glob(pattern):
        uid = extractor(file_path)
        if uid:
            ids.add(uid)
    return ids


# ----------------------------
# Analyze report helpers
# ----------------------------

def parse_report(
    lines: list[str],
    *,
    first_threshold: int,
    last_threshold: int,
) -> tuple[list[str], list[str], list[str]]:
    """Return three lists: no-non-zero, first<threshold, last>threshold."""
    no_values: list[str] = []
    first_lt: list[str] = []
    last_gt: list[str] = []
    pattern = re.compile(r"first non-zero value at row (\d+); last at row (\d+)")

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        name = line.split(":", 1)[0]
        lowered = line.lower()
        if "no non-zero values found" in lowered:
            no_values.append(name)
            continue
        match = pattern.search(lowered)
        if not match:
            continue
        first = int(match.group(1))
        last = int(match.group(2))
        if first < first_threshold:
            first_lt.append(name)
        if last > last_threshold:
            last_gt.append(name)

    return no_values, first_lt, last_gt


def load_lines_from_source(input_path: Path | None) -> list[str]:
    if input_path:
        return input_path.read_text().splitlines()
    if sys.stdin.isatty():
        raise SystemExit("Provide --input or pipe the report via STDIN.")
    return sys.stdin.read().splitlines()


def print_section(title: str, entries: list[str]) -> None:
    print(f"{title} ({len(entries)}):")
    if entries:
        for name in entries:
            print(f"  {name}")
    else:
        print("  (none)")
    print()


# ----------------------------
# Command entrypoints
# ----------------------------

def cmd_fix_angles(args: argparse.Namespace) -> None:
    fix_angles_in_folder(args.folder)


def cmd_convert_flac(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    destination = args.destination.resolve()
    if not root.exists():
        raise FileNotFoundError(f"The source folder {root} does not exist")
    if not root.is_dir():
        raise NotADirectoryError(f"{root} is not a directory")
    destination.mkdir(parents=True, exist_ok=True)
    wav_destination = args.wav_destination.resolve() if args.wav_destination else None
    wav_filters = normalize_wav_filters(args.wav_names)

    files = list(flac_files(root))
    if not files:
        print(f"No FLAC files found in {root}")
        return

    print(f"Found {len(files)} FLAC files. Starting conversion…")
    for file_path in files:
        convert_file(
            file_path,
            root,
            destination,
            wav_destination=wav_destination,
            wav_name_filters=wav_filters,
            export_all_wav=args.export_all_wav,
            trim_head=args.trim_head_samples,
            trim_tail=args.trim_tail_samples,
        )
    print("Conversion complete.")


def cmd_export_polar(args: argparse.Namespace) -> None:
    source_dir = args.source
    destination_dir = args.destination
    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory does not exist: {source_dir}")
    json_files = sorted(source_dir.glob("merged_fixed_*.json"))
    if not json_files:
        print(f"No merged_fixed_*.json files found in {source_dir}")
        return

    print(f"Found {len(json_files)} JSON file(s). Writing CSVs to {destination_dir} ...")
    destination_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    for json_file in json_files:
        try:
            angle, distance = extract_angle_distance(json_file)
            csv_path = destination_for(json_file, destination_dir)
            with csv_path.open("w", newline="") as handle:
                writer = csv.writer(handle)
                if not args.no_header:
                    writer.writerow(["angle_deg"])
                writer.writerow([f"{angle}"])
        except Exception as exc:
            print(f"⚠️ {exc}")
            continue
        written += 1
        print(f"✅ {json_file.name} → {csv_path.name}")
    print(f"Done. Created {written} CSV file(s).")

def cmd_check_uuid(args: argparse.Namespace) -> None:
    if not args.audio_root.exists():
        raise FileNotFoundError(f"Audio directory not found: {args.audio_root}")
    if not args.merged_root.exists():
        raise FileNotFoundError(f"Merged directory not found: {args.merged_root}")

    audio_ids = gather_ids(args.audio_root, "audio_event_*.flac", extract_from_flac)
    merged_ids = gather_ids(args.merged_root, "merged*.json", extract_from_merged)

    missing_in_merged = sorted(audio_ids - merged_ids)
    missing_in_audio = sorted(merged_ids - audio_ids)

    print(f"Audio UUIDs: {len(audio_ids)}")
    print(f"Merged UUIDs: {len(merged_ids)}\n")

    print(f"Present in audio but missing in merged (count={len(missing_in_merged)}):")
    if missing_in_merged:
        for uid in missing_in_merged:
            print(f"  {uid}")
    else:
        print("  (none)")

    print(f"\nPresent in merged but missing in audio (count={len(missing_in_audio)}):")
    if missing_in_audio:
        for uid in missing_in_audio:
            print(f"  {uid}")
    else:
        print("  (none)")

    def confirm(prompt: str) -> bool:
        if args.yes:
            return True
        reply = input(f"{prompt} [y/N]: ").strip().lower()
        return reply in {"y", "yes"}

    if args.delete_audio_extras and missing_in_merged:
        if confirm(f"\nDelete {len(missing_in_merged)} audio file(s) that have no merged counterpart?"):
            for uid in missing_in_merged:
                flac_path = args.audio_root / f"audio_event_{uid}.flac"
                if flac_path.exists():
                    flac_path.unlink()
                    print(f"🗑️ Removed {flac_path}")
                else:
                    print(f"⚠️ Audio file not found for {uid}")

    if args.delete_merged_extras and missing_in_audio:
        if confirm(f"\nDelete {len(missing_in_audio)} merged file(s) that have no audio counterpart?"):
            for uid in missing_in_audio:
                json_path = args.merged_root / f"merged_fixed_{uid}.json"
                if json_path.exists():
                    json_path.unlink()
                    print(f"🗑️ Removed {json_path}")
                else:
                    print(f"⚠️ Merged file not found for {uid}")


def cmd_analyze_report(args: argparse.Namespace) -> None:
    lines = load_lines_from_source(args.input)
    no_values, first_lt, last_gt = parse_report(
        lines,
        first_threshold=args.first_threshold,
        last_threshold=args.last_threshold,
    )

    print_section("No non-zero values", no_values)
    print_section(f"First row < {args.first_threshold}", first_lt)
    print_section(f"Last row > {args.last_threshold}", last_gt)


def cmd_incremental(args: argparse.Namespace) -> None:
    """Run incremental pipeline on new files only."""
    merged_root = args.merged_root.resolve()
    position_root = args.position_root.resolve()
    flac_json_root = args.flac_json_root.resolve()
    audio_root = args.audio_root.resolve()
    audio_csv = args.audio_csv.resolve()
    coord_csv = args.coord_csv.resolve()

    # Determine already-processed UUIDs (existing CSV outputs)
    processed_ids = {
        p.stem[len("audio_event_") :] if p.stem.startswith("audio_event_") else p.stem
        for p in audio_csv.glob("audio_event_*.csv")
    }
    processed_ids |= {
        p.stem[len("labels_") :] if p.stem.startswith("labels_") else p.stem
        for p in coord_csv.glob("*.csv")
        if p.stem != "all_labels"
    }

    # Step 1: merge new pairs into merged_*.json
    new_ids: set[str] = set()
    if prompt_bool("Proceed with merging new samples?"):
        new_ids = set(
            merge_new_samples(flac_json_root, position_root, merged_root, exclude_ids=processed_ids)
        )
    else:
        print(color("Skipped merging new samples.", COLOR_YELLOW))

    # Step 2: convert new FLACs to CSV (filtered to new IDs)
    new_audio_csvs: list[Path] = []
    if prompt_bool("Convert new FLAC files to CSV?"):
        wav_destination = args.wav_destination.resolve() if args.wav_destination else None
        wav_filters = normalize_wav_filters(args.wav_names)
        new_audio_csvs = convert_new_flacs(
            audio_root,
            audio_csv,
            uuids_filter=new_ids if new_ids else None,
            wav_destination=wav_destination,
            wav_filters=wav_filters,
            export_all_wav=args.export_all_wav,
            trim_head=args.trim_head_samples,
            trim_tail=args.trim_tail_samples,
        )
    else:
        print(color("Skipped FLAC to CSV conversion.", COLOR_YELLOW))

    # Step 3: drop zero-only audio CSVs and corresponding merged JSON
    if new_audio_csvs and prompt_bool("Check and remove zero-only audio CSVs?"):
        removed = 0
        for csv_path in new_audio_csvs:
            try:
                data = np.loadtxt(csv_path, delimiter=",")
                if np.allclose(data, 0):
                    uid = csv_path.stem
                    if uid.startswith("audio_event_"):
                        uid = uid[len("audio_event_") :]
                    csv_path.unlink()
                    for candidate in (
                        merged_root / f"merged_{uid}.json",
                        merged_root / f"merged_fixed_{uid}.json",
                    ):
                        if candidate.exists():
                            candidate.unlink()
                    print(color(f"🗑️ Removed zero-only CSV and merged JSON for {uid}", COLOR_RED))
                    removed += 1
            except Exception as exc:
                print(color(f"⚠️ Failed zero-check on {csv_path}: {exc}", COLOR_YELLOW))
        if removed:
            print(color(f"Removed {removed} zero-only audio CSV(s).", COLOR_YELLOW))
    elif new_audio_csvs:
        print(color("Skipped zero-only CSV check.", COLOR_YELLOW))

    # Step 4: (alignment check removed on request)


# ----------------------------
# CLI wiring
# ----------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dataset maintenance toolbox.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # fix-angles
    p_fix = subparsers.add_parser("fix-angles", help="Normalize angle_deg fields and rename merged files.")
    p_fix.add_argument(
        "--folder",
        type=Path,
        default=PROJECT_ROOT / "Data/Json/merged_samples",
        help="Root folder containing merged JSON files.",
    )
    p_fix.set_defaults(func=cmd_fix_angles)

    # convert-flac
    p_conv = subparsers.add_parser("convert-flac", help="Convert FLAC files to CSV (and optionally WAV).")
    p_conv.add_argument(
        "--root",
        type=Path,
        default=PROJECT_ROOT / "Data/audio/audio_loopback_flac",
        help="Source folder containing FLAC files (recursive).",
    )
    p_conv.add_argument(
        "--destination",
        type=Path,
        default=PROJECT_ROOT / "Data/csv/audio_loopback_csv",
        help="Destination folder for CSV exports.",
    )
    p_conv.add_argument(
        "--wav-destination",
        type=Path,
        default=None,
        help="Optional destination for WAV exports (defaults to CSV destination).",
    )
    p_conv.add_argument(
        "--wav-names",
        nargs="*",
        default=(),
        help="Base names (with or without extensions) of files that should also be exported as WAV.",
    )
    p_conv.add_argument(
        "--export-all-wav",
        action="store_true",
        help="Export a WAV file for every converted FLAC.",
    )
    p_conv.add_argument(
        "--trim-head-samples",
        type=int,
        default=0,
        help="Number of samples to drop from the start of each audio before export.",
    )
    p_conv.add_argument(
        "--trim-tail-samples",
        type=int,
        default=0,
        help="Number of samples to drop from the end of each audio before export.",
    )
    p_conv.set_defaults(func=cmd_convert_flac)

    # export-polar
    p_polar = subparsers.add_parser("export-polar", help="Export angle/distance from merged JSON to CSV.")
    p_polar.add_argument(
        "--source",
        type=Path,
        default=PROJECT_ROOT / DEFAULT_SOURCE,
        help=f"Directory containing merged_fixed JSON files (default: {DEFAULT_SOURCE}).",
    )
    p_polar.add_argument(
        "--destination",
        type=Path,
        default=PROJECT_ROOT / DEFAULT_DESTINATION,
        help=f"Directory where the CSV files will be written (default: {DEFAULT_DESTINATION}).",
    )
    p_polar.add_argument(
        "--no-header",
        action="store_true",
        help="Do not write the header row (angle_deg).",
    )
    p_polar.set_defaults(func=cmd_export_polar)

    # check-uuid
    p_uuid = subparsers.add_parser("check-uuid", help="Compare UUIDs between audio FLACs and merged JSONs.")
    p_uuid.add_argument(
        "--audio-root",
        type=Path,
        default=PROJECT_ROOT / "Data/audio/audio_loopback_flac",
        help="Directory containing audio_event_*.flac files.",
    )
    p_uuid.add_argument(
        "--merged-root",
        type=Path,
        default=PROJECT_ROOT / "Data/Json/merged_samples",
        help="Directory containing merged JSON files.",
    )
    p_uuid.add_argument(
        "--delete-audio-extras",
        action="store_true",
        default=True,
        help="Delete files that exist only in the audio directory (default: delete).",
    )
    p_uuid.add_argument(
        "--delete-merged-extras",
        action="store_true",
        default=True,
        help="Delete files that exist only in the merged directory (default: delete).",
    )
    p_uuid.add_argument(
        "--yes",
        action="store_true",
        default=True,
        help="Skip confirmation prompts when deleting files (default: skip).",
    )
    p_uuid.set_defaults(func=cmd_check_uuid)

    # analyze-report
    p_report = subparsers.add_parser("analyze-report", help="Analyze output from find_first_nonzero_csv.py.")
    p_report.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Path to the saved report file (defaults to reading from STDIN).",
    )
    p_report.add_argument(
        "--first-threshold",
        type=int,
        default=40_000,
        help="Upper bound for the 'first non-zero value' filter (default: 40000).",
    )
    p_report.add_argument(
        "--last-threshold",
        type=int,
        default=150_000,
        help="Lower bound for the 'last at row' filter (default: 150000).",
    )
    p_report.set_defaults(func=cmd_analyze_report)

    # incremental
    p_inc = subparsers.add_parser(
        "incremental",
        help="Incremental pipeline: merge new samples, convert FLAC->CSV, and run alignment checks.",
    )
    p_inc.add_argument(
        "--audio-root",
        type=Path,
        default=PROJECT_ROOT / "Data/audio/audio_loopback_flac",
        help="Directory containing audio_event_*.flac files.",
    )
    p_inc.add_argument(
        "--flac-json-root",
        type=Path,
        default=PROJECT_ROOT / "Data/Json/flac_json",
        help="Directory containing flac_metadata_*.json files.",
    )
    p_inc.add_argument(
        "--position-root",
        type=Path,
        default=PROJECT_ROOT / "Data/Json/position_json",
        help="Directory containing position_*.json files.",
    )
    p_inc.add_argument(
        "--audio-csv",
        type=Path,
        default=PROJECT_ROOT / "Data/csv/audio_loopback_csv",
        help="Destination folder for audio CSV exports.",
    )
    p_inc.add_argument(
        "--wav-destination",
        type=Path,
        default=None,
        help="Optional destination for WAV exports (defaults to the CSV destination).",
    )
    p_inc.add_argument(
        "--wav-names",
        nargs="*",
        default=(),
        help="Base names (with or without extensions) of files that should also be exported as WAV.",
    )
    p_inc.add_argument(
        "--export-all-wav",
        action="store_true",
        help="Export a WAV file for every converted FLAC.",
    )
    p_inc.add_argument(
        "--trim-head-samples",
        type=int,
        default=0,
        help="Number of samples to drop from the start of each audio before export.",
    )
    p_inc.add_argument(
        "--trim-tail-samples",
        type=int,
        default=0,
        help="Number of samples to drop from the end of each audio before export.",
    )
    p_inc.add_argument(
        "--merged-root",
        type=Path,
        default=PROJECT_ROOT / "Data/Json/merged_samples",
        help="Directory containing merged JSON files.",
    )
    p_inc.add_argument(
        "--coord-csv",
        type=Path,
        default=PROJECT_ROOT / "Data/csv/labels_csv",
        help="Directory containing coordinate label CSVs (labels_<uuid>.csv).",
    )
    p_inc.add_argument(
        "--delete-audio-extras",
        action="store_true",
        default=True,
        help="Delete files that exist only in the audio directory (alignment step, default: delete).",
    )
    p_inc.add_argument(
        "--delete-merged-extras",
        action="store_true",
        default=True,
        help="Delete files that exist only in the merged directory (alignment step, default: delete).",
    )
    p_inc.add_argument(
        "--yes",
        action="store_true",
        default=True,
        help="Skip confirmation prompts when deleting files (alignment step, default: skip).",
    )
    p_inc.set_defaults(func=cmd_incremental)

    return parser


def main() -> None:
    parser = build_parser()
    if len(sys.argv) == 1:
        # Default to incremental pipeline when no arguments are provided.
        args = parser.parse_args(["incremental"])
    else:
        args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
