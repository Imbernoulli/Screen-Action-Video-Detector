import cv2
import numpy as np
import os
import pandas as pd


def load_templates(template_dir, negative_template_dir):
    templates = []
    negative_templates = []

    for filename in os.listdir(template_dir):
        if filename.endswith(".png"):
            path = os.path.join(template_dir, filename)
            template = cv2.imread(
                path, cv2.IMREAD_GRAYSCALE
            )  # Convert directly to grayscale
            if template is None:
                continue
            templates.append((template, filename))
            print(filename, "loaded")

    for filename in os.listdir(negative_template_dir):
        if filename.endswith(".png"):
            path = os.path.join(negative_template_dir, filename)
            template = cv2.imread(
                path, cv2.IMREAD_GRAYSCALE
            )  # Convert directly to grayscale
            if template is None:
                continue
            negative_templates.append(template)
            print(filename, "loaded as negative template")

    return templates, negative_templates


def calculate_overlap(rect1, rect2):
    x1, y1, w1, h1 = rect1
    x2, y2, w2, h2 = rect2

    overlap_x = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
    overlap_y = max(0, min(y1 + h1, y2 + h2) - max(y1, y2))
    overlap_area = overlap_x * overlap_y

    area1 = w1 * h1
    area2 = w2 * h2

    overlap_ratio = overlap_area / min(area1, area2)
    return overlap_ratio


def match_mouse(
    frame,
    templates,
    negative_templates,
    last_loc,
    search_window_size,
    threshold_min,
    threshold_max,
    overlap_threshold,
    r=0,
):
    frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    candidates = []

    # Determine the search area based on the last location
    if last_loc:
        x_center, y_center = last_loc
        x_start = max(0, x_center - search_window_size // 2)
        y_start = max(0, y_center - search_window_size // 2)
        x_end = min(frame.shape[1], x_center + search_window_size // 2)
        y_end = min(frame.shape[0], y_center + search_window_size // 2)
        search_area = frame_gray[y_start:y_end, x_start:x_end]
        search_offset = (x_start, y_start)
    else:
        search_area = frame_gray
        search_offset = (0, 0)

    for template, template_name in templates:
        res = cv2.matchTemplate(search_area, template, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= threshold_min)

        for pt in zip(*loc[::-1]):  # Convert points to full image coordinates
            full_img_pt = (pt[0] + search_offset[0], pt[1] + search_offset[1])
            candidates.append(
                (full_img_pt, template.shape[:2], template_name, res[pt[1]][pt[0]])
            )

    # Check for high-confidence matches
    for candidate in candidates:
        if candidate[3] >= threshold_max:
            return candidate  # Return early if a high-confidence match is found

    # Negative template matching and filtering
    negative_matches = []
    for negative_template in negative_templates:
        negative_res = cv2.matchTemplate(
            search_area, negative_template, cv2.TM_CCOEFF_NORMED
        )
        negative_loc = np.where(negative_res >= threshold_min)
        for neg_pt in zip(*negative_loc[::-1]):
            full_img_neg_pt = (
                neg_pt[0] + search_offset[0],
                neg_pt[1] + search_offset[1],
            )
            negative_matches.append((full_img_neg_pt, negative_template.shape[:2]))

    filtered_candidates = []
    for candidate in candidates:
        pt, size, template_name, val = candidate
        max_overlap = 0
        for neg_pt, neg_size in negative_matches:
            rect1 = (pt[0], pt[1], size[1], size[0])
            rect2 = (neg_pt[0], neg_pt[1], neg_size[1], neg_size[0])
            overlap = calculate_overlap(rect1, rect2)
            max_overlap = max(max_overlap, overlap)

        if max_overlap < overlap_threshold:
            filtered_candidates.append(candidate)

    # Select the remaining area with the highest match confidence
    if filtered_candidates:
        best_match = max(filtered_candidates, key=lambda x: x[3])
        return best_match

    if r == 1:
        return None

    return match_mouse(
        frame,
        templates,
        negative_templates,
        None,
        None,
        threshold_min,
        threshold_max,
        overlap_threshold,
        1,
    )


def process_video(
    video_path,
    template_dir,
    negative_template_dir,
    output_dir,
    threshold_min,
    threshold_max,
    overlap_threshold,
    search_window_size,
):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    templates, negative_templates = load_templates(template_dir, negative_template_dir)
    cap = cv2.VideoCapture(video_path)
    frame_count = 0
    results = []
    last_loc = None  # Initialize last known location

    while True:
        ret, frame = cap.read()

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        if not ret:
            break

        match = match_mouse(
            frame,
            templates,
            negative_templates,
            last_loc,
            search_window_size,
            threshold_min,
            threshold_max,
            overlap_threshold,
        )
        if match:
            loc, size, template_name, confidence = match
            x, y = loc
            w, h = size
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            results.append(
                {
                    "Frame": frame_count,
                    "X": x,
                    "Y": y,
                    "Width": w,
                    "Height": h,
                    "Template": template_name,
                    "Confidence": confidence,
                }
            )
            last_loc = (x + w // 2, y + h // 2)  # Update last known location

        print(f"Frame {frame_count}: {match}")
        frame_file = f"frame_{frame_count}.png"
        cv2.imwrite(os.path.join(output_dir, frame_file), frame)
        frame_count += 1

    cap.release()
    df = pd.DataFrame(results)
    df.to_csv(os.path.join(output_dir, "mouse_positions.csv"), index=False)
    print("Processing complete. Results saved to", output_dir)


# Example usage
video_path = "videos/screen_2024-04-18_16-45-08.mp4"
template_dir = "cursors/positive"
negative_template_dir = "cursors/negative"
output_dir = "output"
threshold_min = 0.68
threshold_max = 0.75
overlap_threshold = 0.6
search_window_size = 200  # Adjust this value based on expected movement between frames
process_video(
    video_path,
    template_dir,
    negative_template_dir,
    output_dir,
    threshold_min,
    threshold_max,
    overlap_threshold,
    search_window_size,
)
