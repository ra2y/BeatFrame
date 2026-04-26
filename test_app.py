from main import analyze_and_export

audio_file = "Therapy.mp3"

result = analyze_and_export(audio_file, "output/beats.csv")

print("Tempo:", result["tempo"])
print("Beat count:", len(result["beat_times"]))
print("Cut point count:", len(result["cut_points"]))
print("CSV path:", result["csv_path"])
print("Cut points:", result["cut_points"])