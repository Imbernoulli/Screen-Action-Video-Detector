import cv2
import json
import numpy as np
import os

names = ["2024-04-29_22-49-33"]


# 读取JSON文件
def load_json(json_path):
    with open(json_path, "r") as file:
        data = json.load(file)
    return data


# 插值计算鼠标位置
def interpolate_mouse_position(frame_time, timestamps, positions):
    if frame_time <= timestamps[0]:
        return positions[0]
    if frame_time >= timestamps[-1]:
        return positions[-1]

    for i in range(1, len(timestamps)):
        if frame_time < timestamps[i]:
            t1, t2 = timestamps[i - 1], timestamps[i]
            p1, p2 = positions[i - 1], positions[i]
            # 加权平均
            # weight = (frame_time - t1) / (t2 - t1)
            weight = 0
            interpolated_position = (1 - weight) * np.array(p1) + weight * np.array(p2)
            return interpolated_position

    return positions[-1]


# 主函数
def process_video(video_path, json_path, output_folder, positions_output_path, name):
    # 载入视频和JSON数据
    cap = cv2.VideoCapture(video_path)
    mouse_data = load_json(json_path)

    mouse_data = [item for item in mouse_data if item["type"] == "mouse_move"]

    timestamps = [item["time"] * 1000 for item in mouse_data]
    positions = [[item["position"]["x"], item["position"]["y"]] for item in mouse_data]

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # 准备输出文件夹
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    frame_index = -1
    mouse_positions = []

    # 设置输出文件
    with open(positions_output_path, "w") as pos_file:
        # 读取每一帧
        while True:
            print(f"Processing frame {frame_index}")
            frame_index += 1
            ret, frame = cap.read()

            if frame_index < 180:
                continue

            if not ret:
                break

            # 计算当前帧的时间
            frame_time = cap.get(cv2.CAP_PROP_POS_MSEC)

            # 获取插值鼠标位置
            mouse_position = interpolate_mouse_position(
                frame_time, timestamps, positions
            )
            mouse_positions.append(mouse_position)

            # 保存帧到文件夹
            cv2.circle(
                frame,
                (int(mouse_position[0] * width), int(mouse_position[1] * height)),
                5,
                (0, 0, 255),
                -1,
            )

            cv2.imwrite(os.path.join(output_folder, f"{frame_index}.png"), frame)

            # 写入鼠标位置到文件
            pos_file.write(f"{frame_index},{mouse_position[0]},{mouse_position[1]}\n")

    cap.release()


for name in names:
    # 参数配置

    video_path = f"/Users/bernoulli_hermes/projects/cad/detect/videos/screen_{name}.mp4"
    json_path = f"/Users/bernoulli_hermes/projects/cad/detect/logs/log_{name}.json"
    output_folder = f"{name}_frames"
    positions_output_path = f"{name}_positions.csv"

    process_video(video_path, json_path, output_folder, positions_output_path, name)
