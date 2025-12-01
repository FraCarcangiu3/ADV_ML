#!/usr/bin/env python3
"""
human_listen_and_label.py - CLI per ascolto soggettivo e labeling

Riproduce .wav in una cartella, filtra per tipo (pitch/noise/tone/combo/all),
randomizza su richiesta e salva risposte in ADV_ML/tests/subjective_results.csv.
Compatibile con afplay (macOS), ffplay (Linux/Windows con ffmpeg) e fallback
sounddevice (se disponibile) quando ffplay non c'è.
"""

import os
import sys
import csv
import argparse
import random
import subprocess
from pathlib import Path
from datetime import datetime

SUBJECTIVE_CSV = Path("ADV_ML/tests/subjective_results.csv")


def detect_player(preferred: str | None = None) -> str:
	if preferred:
		return preferred
	if sys.platform == "darwin":
		return "afplay"
	return "ffplay"


def play_with_system_player(file_path: Path, player: str) -> bool:
	if player == "afplay":
		cmd = ["afplay", str(file_path)]
	else:
		cmd = ["ffplay", "-nodisp", "-autoexit", str(file_path)]
	try:
		subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
		return True
	except Exception:
		return False


def play_with_sounddevice(file_path: Path) -> bool:
	try:
		import soundfile as sf
		import sounddevice as sd
		y, sr = sf.read(str(file_path), always_2d=False)
		sd.play(y, sr)
		sd.wait()
		return True
	except Exception:
		return False


def play_audio(file_path: Path, player: str) -> bool:
	# prova system player
	if play_with_system_player(file_path, player):
		return True
	# fallback a sounddevice
	return play_with_sounddevice(file_path)


def parse_variant_type_and_value(filename: str) -> tuple[str, float]:
	stem = Path(filename).stem
	# Convenzioni generate: *_pitch_[pn]\d+.wav; *_noise_snr\d+.wav; *_tone_XXXXhz.wav; *_combo_*.wav; *_eq_tilt_[pm]\ddB.wav
	if "_pitch_" in stem:
		part = stem.split("_pitch_")[-1]
		sign = -1 if part.startswith("n") else 1
		val = part[1:]
		try:
			return "pitch", sign * float(val)
		except ValueError:
			return "pitch", 0.0
	if "_noise_snr" in stem and "pink" not in stem:
		try:
			val = float(stem.split("_noise_snr")[-1])
			return "noise", val
		except ValueError:
			return "noise", 0.0
	if "_noise_pink_snr" in stem:
		try:
			val = float(stem.split("_noise_pink_snr")[-1])
			return "noise_pink", val
		except ValueError:
			return "noise_pink", 0.0
	if "_tone_" in stem and stem.endswith("hz"):
		try:
			freq = float(stem.split("_tone_")[-1].removesuffix("hz"))
			return "tone", freq
		except ValueError:
			return "tone", 0.0
	if "_eq_tilt_" in stem:
		seg = stem.split("_eq_tilt_")[-1]
		seg = seg.replace("dB", "")
		try:
			val = float(seg.replace("p", "+").replace("m", "-"))
			return "eq_tilt", val
		except ValueError:
			return "eq_tilt", 0.0
	if "_combo_" in stem:
		return "combo", 0.0
	return "unknown", 0.0


def filter_by_types(files: list[Path], types: set[str]) -> list[Path]:
	if "all" in types:
		return files
	selected: list[Path] = []
	for f in files:
		vtype, _ = parse_variant_type_and_value(f.name)
		if vtype in types:
			selected.append(f)
	return selected


def ask_yes_no(prompt: str) -> str:
	ans = input(prompt).strip().upper()
	while ans not in ("Y", "N"):
		ans = input("Please enter Y or N: ").strip().upper()
	return ans


def ask_severity() -> int:
	val = input("Quanto evidente? (1-5): ").strip()
	while not val.isdigit() or int(val) not in (1, 2, 3, 4, 5):
		val = input("Inserisci un numero tra 1 e 5: ").strip()
	return int(val)


def run_session(folder: Path, subject: str, types: set[str], randomize: bool, player: str) -> None:
	if not folder.exists():
		print(f"ERROR: cartella non trovata: {folder}")
		return
	wav_files = [p for p in folder.glob("*.wav") if "_ref" not in p.name]
	ref = next((p for p in folder.glob("*_ref.wav")), None)
	if ref is None:
		print("WARNING: riferimento *_ref.wav non trovato, si procederà solo con le varianti.")
	
	wav_files = filter_by_types(wav_files, types)
	if randomize:
		random.shuffle(wav_files)
	
	print("=" * 60)
	print(f"ASCOLTO GUIDATO — {folder.name}")
	print("=" * 60)
	print(f"Soggetto: {subject}")
	print(f"File da testare: {len(wav_files)}")
	print("\nIstruzioni:\n- Ascolterai (opz.) il RIFERIMENTO, poi una VARIANTE\n- Indica se percepisci differenza e la severità\n- Premi INVIO per iniziare...")
	input()
	
	rows: list[dict] = []
	for i, f in enumerate(wav_files, 1):
		print(f"\n--- {i}/{len(wav_files)} — {f.name} ---")
		if ref is not None:
			print("Riproduco RIFERIMENTO...")
			play_audio(ref, player)
		print("Riproduco VARIANTE...")
		play_audio(f, player)
		
		perceived = ask_yes_no("Hai percepito una differenza? (Y/N): ")
		severity = 0
		if perceived == "Y":
			severity = ask_severity()
		notes = input("Note (facoltative): ").strip()
		vtype, value = parse_variant_type_and_value(f.name)
		rows.append({
			"subject": subject,
			"file": f.name,
			"value": value,
			"type": vtype,
			"perceived_change": perceived,
			"severity": severity,
			"notes": notes,
			"timestamp": datetime.now().isoformat()
		})
		print("✓ Registrato")
	
	SUBJECTIVE_CSV.parent.mkdir(parents=True, exist_ok=True)
	file_exists = SUBJECTIVE_CSV.exists()
	with open(SUBJECTIVE_CSV, "a", newline="") as fh:
		writer = csv.DictWriter(
			fh,
			fieldnames=[
				"subject",
				"file",
				"value",
				"type",
				"perceived_change",
				"severity",
				"notes",
				"timestamp",
			],
		)
		if not file_exists:
			writer.writeheader()
		writer.writerows(rows)
	print(f"\n✓ Sessione completa. Risultati salvati in: {SUBJECTIVE_CSV}")


def main() -> None:
	parser = argparse.ArgumentParser(description="Ascolto soggettivo e labeling varianti audio")
	parser.add_argument("folder", help="Cartella con .wav (es: ADV_ML/tests/output/audible_variants/auto)")
	parser.add_argument("--subject", default="user", help="Nome/ID soggetto")
	parser.add_argument(
		"--types",
		nargs="+",
		default=["all"],
		choices=["pitch", "noise", "noise_pink", "tone", "eq_tilt", "combo", "all"],
		help="Filtra per tipo variante",
	)
	parser.add_argument("--randomize", action="store_true", help="Riproduzione in ordine casuale")
	parser.add_argument("--player", choices=["afplay", "ffplay"], help="Forza il player di sistema")
	args = parser.parse_args()
	
	folder = Path(args.folder)
	types = set(args.types)
	player = detect_player(args.player)
	run_session(folder, args.subject, types, args.randomize, player)


if __name__ == "__main__":
	main()
