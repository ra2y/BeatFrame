from ui import BeatFrameApp
from PySide6.QtWidgets import QApplication
import sys

app = QApplication(sys.argv)
window = BeatFrameApp()
window.show
sys.exit(app.exec())
import csv
import os
from typing import List, Dict, Any

import librosa
import numpy as np


def analyze_audio_file(audio_path: str) -> Dict[str, Any]:
    y, sr = librosa.load(audio_path)

    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    tempo = float(np.ravel(tempo)[0])

    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    if onset_env.size == 0 or onset_env.max() == 0:
        return {
            "tempo": tempo,
            "beat_times": [],
            "cut_points": [],
        }

    times = librosa.times_like(onset_env, sr=sr)
    norm_onset = onset_env / onset_env.max()

    peaks = librosa.util.peak_pick(
        norm_onset,
        pre_max=3,
        post_max=3,
        pre_avg=3,
        post_avg=3,
        delta=0.15,
        wait=5,
    )

    peak_times = times[peaks]
    peak_strengths = norm_onset[peaks]

    important_mask = peak_strengths >= 0.25
    important_times = peak_times[important_mask]
    important_strengths = peak_strengths[important_mask]

    cut_points: List[float] = []
    window = 0.5
    max_dist = 0.1

    for bt in beat_times:
        local_mask = np.abs(important_times - bt) <= window
        local_times = important_times[local_mask]
        local_strengths = important_strengths[local_mask]

        if len(local_times) == 0:
            continue

        best_idx = np.argmax(local_strengths)
        nearest_peak = local_times[best_idx]

        if abs(nearest_peak - bt) < max_dist:
            cut_points.append(float(nearest_peak))

    cut_points = list(dict.fromkeys(np.round(cut_points, 4)))
    cut_points = [float(t) for t in cut_points]

    return {
        "tempo": tempo,
        "beat_times": [float(t) for t in beat_times],
        "cut_points": cut_points,
    }


def write_csv(cut_points: List[float], csv_path: str) -> str:
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)

    with open(csv_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["time_seconds"])
        writer.writerows([[t] for t in cut_points])

    return csv_path


def analyze_and_export(audio_path: str, csv_path: str = "timestamps.csv") -> Dict[str, Any]:
    result = analyze_audio_file(audio_path)
    written_csv = write_csv(result["cut_points"], csv_path)

    return {
        "tempo": result["tempo"],
        "beat_times": result["beat_times"],
        "cut_points": result["cut_points"],
        "csv_path": written_csv,
    }
