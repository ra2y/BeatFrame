import csv

# get timeline object
resolve = app.GetResolve()
pm = resolve.GetProjectManager()
project = pm.GetCurrentProject()
timeline = project.GetCurrentTimeline() 

CSV_FILEPATH = "PLACEHOLDER"
with open(CSV_FILEPATH, mode='r', newline='') as file:
    reader = csv.reader(file)
    
    for row in reader:
        if not row:
            continue
        try:
            timestamp = float(row[0])
            
            # convert timestamps to frame by getting the fps of project
            fps = float(timeline.GetSetting("timelineFrameRate"))
            frame = round(timestamp * fps)

            timeline.AddMarker(frame, 'Blue', 'Important Beat', 'Detailed Note here', 1)
        except ValueError:
            print(f"Skipping invalid value: {row[0]}")

