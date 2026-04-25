# Beat tracking example
import librosa

# 1. Get the file path to an included audio example
filename = 'Overture.mp3'

# 2. Load the audio as a waveform `y`
#    Store the sampling rate as `sr`
y, sr = librosa.load(filename)

# 3. Run the default beat tracker
tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)

tempo = float(tempo[0])
print('Estimated tempo: {:.2f} beats per minute'.format(tempo))

# 4. Convert the frame indices of beat events into timestamps
beat_times = librosa.frames_to_time(beat_frames, sr=sr)

# compute onset strength
# onset_env is a 1D array telling us how strong audio change is at the moment
onset_env = librosa.onset.onset_strength(y=y, sr=sr)

# convert to strengths timestamps
times = librosa.times_like(onset_env, sr=sr)

# filter to strongest peaks
peaks = librosa.util.peak_pick(
    onset_env,
    pre_max=3,
    post_max=3,
    pre_avg=3,
    post_avg=3,
    delta=0.7,
    wait= 15
)

peak_times = times[peaks]
peak_strengths = onset_env[peaks]

# Normalize strength
norm_strength = (onset_env - onset_env.min()) / (onset_env.max() - onset_env.min())

# Only keep strong hits
important = peaks[norm_strength[peaks] > 0.6]

important_times = times[important]

#strongest beats that we will leave timestamp at
cut_points = []

for bt in beat_times:
    # Find closest onset peak
    nearest_peak = min(important_times, key=lambda x: abs(x - bt))
    
    # If it's close enough, use it
    if abs(nearest_peak - bt) < 0.1:
        cut_points.append(nearest_peak)
    else:
        cut_points.append(bt)

print(len(peak_times))
print(len(beat_times))
print(len(cut_points))