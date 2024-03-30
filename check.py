import json
import os
import cv2

def draw_marker(frame, action, width, height):
    if action['type'] == 'click':
        x = int(action['position']['x'] * width)
        y = int(action['position']['y'] * height)
        cv2.circle(frame, (x, y), 20, (0, 255, 255), -1)  # Bigger circle with bright yellow color
        cv2.putText(frame, 'Click', (x + 25, y + 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 3)  # Larger text with pink color
    elif action['type'] == 'drag':
        start_x = int(action['start']['x'] * width)
        start_y = int(action['start']['y'] * height)
        end_x = int(action['end']['x'] * width)
        end_y = int(action['end']['y'] * height)
        cv2.line(frame, (start_x, start_y), (end_x, end_y), (255, 255, 0), 4)  # Thicker line with cyan color
        cv2.putText(frame, 'Drag', (end_x + 25, end_y + 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 3)  # Larger text with yellow color
    elif action['type'] == 'scroll':
        x = int(action['position']['x'] * width)
        y = int(action['position']['y'] * height)
        cv2.arrowedLine(frame, (x, y), (x, y - 40), (0, 255, 0), 4)  # Bigger arrow
        cv2.putText(frame, 'Scroll', (x + 25, y + 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)  # Larger text
    return frame

def mark_video(log_file, video_file, output_file, time_offset):
    with open(log_file, 'r') as f:
        actions = json.load(f)

    cap = cv2.VideoCapture(video_file)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_file, fourcc, fps, (width, height))

    current_frame = 0
    action_index = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        while action_index < len(actions) and actions[action_index]['time'] + time_offset <= current_frame / fps:
            frame = draw_marker(frame, actions[action_index], width, height)
            action_index += 1

        out.write(frame)
        current_frame += 1

    cap.release()
    out.release()

def main(selected_folder, time_offset=0):
    log_folder = os.path.join(selected_folder, 'logs')
    video_folder = os.path.join(selected_folder, 'videos')
    output_folder = os.path.join(selected_folder, 'marked_videos')
    os.makedirs(output_folder, exist_ok=True)

    for log_filename in os.listdir(log_folder):
        if log_filename.endswith('.json'):
            log_file = os.path.join(log_folder, log_filename)
            video_filename = log_filename.replace('log_', 'screen_').replace('.json', '.mp4')
            video_file = os.path.join(video_folder, video_filename)
            output_file = os.path.join(output_folder, video_filename.replace('.mp4', '_marked.mp4'))

            if os.path.exists(video_file):
                mark_video(log_file, video_file, output_file, time_offset)
                print(f'Marked video saved to {output_file}')
            else:
                print(f'Video file {video_file} does not exist.')

if __name__ == '__main__':
    main(os.getcwd(), time_offset=0)
