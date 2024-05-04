import cv2
import json
import numpy as np
import os
import pandas as pd

def load_json(json_path):
    with open(json_path, "r") as file:
        data = json.load(file)
    return data

def interpolate_mouse_position(frame_time, timestamps, positions):
    if frame_time <= timestamps[0]:
        return positions[0]
    if frame_time >= timestamps[-1]:
        return positions[-1]

    for i in range(1, len(timestamps)):
        if frame_time < timestamps[i]:
            t1, t2 = timestamps[i - 1], timestamps[i]
            p1, p2 = positions[i - 1], positions[i]
            weight = (frame_time - t1) / (t2 - t1)
            interpolated_position = (1 - weight) * np.array(p1) + weight * np.array(p2)
            return interpolated_position

    return positions[-1]

def find_mouse(frame, x, y, radius=15, aspect_ratio_range=(0.8, 1.2)):
    # Define the region of interest
    x1, y1 = max(x - radius, 0), max(y - radius, 0)
    x2, y2 = min(x + radius, frame.shape[1]), min(y + radius, frame.shape[0])
    roi = frame[y1:y2, x1:x2]
    
    # Convert to grayscale and apply Gaussian blur
    gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    gray_roi = cv2.GaussianBlur(gray_roi, (5, 5), 0)
    
    # Apply Canny edge detection
    edges = cv2.Canny(gray_roi, 100, 200)
    
    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Find the contour with the largest area and appropriate aspect ratio
    mouse_contour = None
    max_area = 0
    for contour in contours:
        (mx, my, mw, mh) = cv2.boundingRect(contour)
        aspect_ratio = float(mw) / mh
        if aspect_ratio_range[0] <= aspect_ratio <= aspect_ratio_range[1]:
            area = cv2.contourArea(contour)
            if area > max_area:
                max_area = area
                mouse_contour = contour
    
    if mouse_contour is not None:
        (mx, my, mw, mh) = cv2.boundingRect(mouse_contour)
        return (x1 + mx, y1 + my, mw, mh)
    else:
        return None

def process_video(video_path, json_path, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    cap = cv2.VideoCapture(video_path)
    mouse_data = load_json(json_path)
    mouse_data = [item for item in mouse_data if item["type"] == "mouse_move"]
    timestamps = [item["time"] * 1000 for item in mouse_data]
    positions = [[item["position"]["x"], item["position"]["y"]] for item in mouse_data]

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    frame_count = 0
    results = []

    while True:
        ret, frame = cap.read()

        if not ret:
            break

        frame_time = cap.get(cv2.CAP_PROP_POS_MSEC)
        mouse_position = interpolate_mouse_position(frame_time, timestamps, positions)
        x, y = int(mouse_position[0] * width), int(mouse_position[1] * height)

        mouse = find_mouse(frame, x, y)
        if mouse:
            mx, my, mw, mh = mouse
            cv2.rectangle(frame, (mx, my), (mx + mw, my + mh), (0, 255, 0), 2)
            results.append({
                "Frame": frame_count,
                "X": mx,
                "Y": my,
                "Width": mw,
                "Height": mh
            })

        print(f"Frame {frame_count}: {mouse}")
        if mouse:
            frame_file = f"frame_{frame_count}.png"
            cv2.imwrite(os.path.join(output_dir, frame_file), frame)
        frame_count += 1

    cap.release()
    df = pd.DataFrame(results)
    df.to_csv(os.path.join(output_dir, "mouse_positions.csv"), index=False)
    print("Processing complete. Results saved to", output_dir)

# Example usage
names = ["2024-04-29_22-49-33"]

for name in names:
    video_path = f"/Users/bernoulli_hermes/projects/cad/detect/videos/screen_{name}.mp4"
    json_path = f"/Users/bernoulli_hermes/projects/cad/detect/logs/log_{name}.json"
    output_dir = f"{name}_output"

    process_video(video_path, json_path, output_dir)