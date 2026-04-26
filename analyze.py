import librosa
import numpy as np

# Helper to format seconds as MM:SS
def format_mm_ss(seconds):
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"  # was unindented

def analyze_audio('Overture.mp3'):
    # 1. Load audio
    y, sr = librosa.load('Overture.mp3')

    # 2. Beat tracking
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    tempo = float(tempo[0])
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    #print('Estimated tempo: {:.2f} beats per minute'.format(tempo))

    # 3. Onset strength
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    times = librosa.times_like(onset_env, sr=sr)
    norm_strength = onset_env/onset_env.max()

    peaks = librosa.util.peak_pick(
        norm_strength,
        pre_max=3,
        post_max=3,
        pre_avg=3,
        post_avg=3,
        delta=0.10,
        wait=30
    )

    #peak_times = times[peaks]
    #peak_strengths = norm_strength[peaks]

    # 4. Filter to strong hits
    important = peaks[norm_strength[peaks] > 0.35]
    important_times = times[important]
    print(f"Found {len(important_times)} important peaks")  # add this to debug

    # 5. Align beats to nearest strong peak
    strongest_cut_points = []
    for bt in beat_times:
        if len(important_times) == 0:  # guard against empty
            strongest_cut_points.append(bt)
            continue
        nearest_peak = min(important_times, key=lambda x: abs(x - bt))
        if abs(nearest_peak - bt) < 0.1:
            strongest_cut_points.append(nearest_peak)

    # 6. Print results
    duration = len(y) / sr
    aligned = sorted(set(strongest_cut_points))

    print(f'Audio duration: {duration:.2f} seconds')
    print("Strongest beat timestamps:")
    for ts in aligned:
        print(f"- {format_mm_ss(ts)} ({ts:.2f} seconds)")
    print(f"Total aligned strongest beat timestamps: {len(aligned)}")
    return aligned # ui.py will use this list