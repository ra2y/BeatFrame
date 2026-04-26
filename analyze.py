import csv
import json
import os
from typing import List, Dict, Any

import librosa
import numpy as np


def format_mm_ss(seconds: float) -> str:
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}:{secs:05.2f}"


def analyze_audio(
    audio_path: str,
    sensitivity: float = 0.70,
    max_markers: int = 20,
    min_gap: float = 3.0,
    top_n: int = 15,
    output_dir: str = ".",
) -> str:
    """
    Analyze audio and write both a CSV and a JSON manifest.
    Returns the CSV path (what AnalyzeWorker emits via finished signal).
    """
    y, sr = librosa.load(audio_path)
    duration = float(len(y) / sr)

    # ── tempo + beats ──────────────────────────────────────────────────────────
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    tempo = float(np.ravel(tempo)[0])
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    # ── onset strength ─────────────────────────────────────────────────────────
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    if onset_env.size == 0 or onset_env.max() == 0:
        cut_points = [float(t) for t in beat_times[:max_markers]]
        top_peaks = []
    else:
        times = librosa.times_like(onset_env, sr=sr)
        norm_onset = onset_env / onset_env.max()

        # min_gap slider → wait frames so spacing is enforced at detection time
        wait_frames = max(1, int(min_gap * sr / 512))

        # sensitivity slider (0-1) maps to delta (0.05 – 0.40)
        delta = 0.05 + (1.0 - sensitivity) * 0.35

        peaks = librosa.util.peak_pick(
            norm_onset,
            pre_max=3,
            post_max=3,
            pre_avg=3,
            post_avg=3,
            delta=delta,
            wait=wait_frames,
        )

        peak_times = times[peaks]
        peak_strengths = norm_onset[peaks]

        # keep peaks above 0.25 normalised strength
        important_mask = peak_strengths >= 0.25
        important_times = peak_times[important_mask]
        important_strengths = peak_strengths[important_mask]

        # snap beats → nearest strong peak within 100 ms
        cut_points: List[float] = []
        snap_window = 0.5
        max_dist = 0.1

        for bt in beat_times:
            local_mask = np.abs(important_times - bt) <= snap_window
            local_times = important_times[local_mask]
            local_str = important_strengths[local_mask]
            if len(local_times) == 0:
                continue
            best_idx = np.argmax(local_str)
            nearest = local_times[best_idx]
            if abs(nearest - bt) < max_dist:
                cut_points.append(float(nearest))

        # deduplicate, sort, cap at max_markers
        cut_points = sorted(set(round(t, 4) for t in cut_points))
        cut_points = [float(t) for t in cut_points[:max_markers]]

        # top_n strongest peaks (for the timestamp list in the UI)
        if len(important_times) > 0:
            sorted_by_strength = np.argsort(important_strengths)[::-1][:top_n]
            top_peaks = [
                {
                    "time_seconds": float(important_times[i]),
                    "time_fmt": format_mm_ss(float(important_times[i])),
                    "strength": float(important_strengths[i]),
                }
                for i in sorted_by_strength
            ]
            top_peaks.sort(key=lambda x: x["time_seconds"])
        else:
            top_peaks = []

    # ── mood heuristic ─────────────────────────────────────────────────────────
    if tempo < 90:
        mood = "Chill"
    elif tempo < 130:
        mood = "Upbeat"
    elif tempo < 160:
        mood = "Energetic"
    else:
        mood = "Intense"

    # ── write CSV ──────────────────────────────────────────────────────────────
    os.makedirs(output_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(audio_path))[0]
    csv_path = os.path.join(output_dir, f"{base}_timestamps.csv")

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["time_seconds", "time_fmt"])
        for t in cut_points:
            writer.writerow([t, format_mm_ss(t)])

    # ── write JSON manifest (read by on_analysis_done) ─────────────────────────
    manifest = {
        "bpm": round(tempo, 1),
        "peak_count": len(cut_points),
        "beat_count": int(len(beat_times)),
        "mood": mood,
        "duration": round(duration, 2),
        "cut_points": cut_points,
        "top_peaks": top_peaks,
    }
    json_path = csv_path.replace(".csv", ".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return csv_path