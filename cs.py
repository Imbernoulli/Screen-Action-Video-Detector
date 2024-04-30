import json
import threading
from pynput import mouse
from datetime import datetime
import subprocess
import os
import pyautogui
import time
import platform
import re

class Recorder:
    def __init__(self, selected_folder, resolution):
        self.init(selected_folder, resolution)

    def init(self, selected_folder, resolution):
        self.resolution_string = f"scale=-1:{resolution}"
        self.video_folder = os.path.join(selected_folder, "videos")
        self.log_folder = os.path.join(selected_folder, "logs")
        self.current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.video_start_time = datetime.now()
        self.action_log = []
        self.record_thread = None
        self.stop_event = threading.Event()
        self.mouse_listener = None
        self.screen_device = None

        # Initialize record folders
        os.makedirs(self.video_folder, exist_ok=True)
        os.makedirs(self.log_folder, exist_ok=True)

    def relative_time(self):
        return (datetime.now() - self.video_start_time).total_seconds()

    def record_screen(self):
        filename = os.path.join(self.video_folder, f"screen_{self.current_time}.mp4")

        # 根据操作系统确定屏幕捕捉方法和命令行参数
        if platform.system() == "Windows":
            command = [
                "ffmpeg",
                "-f",
                "gdigrab",
                "-framerate",
                "30",
                "-i",
                "desktop",
                "-vf",
                self.resolution_string,
                "-vcodec",
                "libx264",
                "-r",
                "30",
                "-crf",
                "30",
                "-preset",
                "ultrafast",
                "-y",
                filename,
            ]
        elif platform.system() == "Darwin":
            # 在 macOS 上自动选择屏幕捕捉设备
            if not self.screen_device:
                process = subprocess.Popen(
                    [
                        "ffmpeg",
                        "-f",
                        "avfoundation",
                        "-list_devices",
                        "true",
                        "-i",
                        '""',
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                )
                devices_output, _ = process.communicate()
                devices_output = devices_output.decode("utf-8")
                lines = devices_output.split("\n")
                for line in lines:
                    if "Capture screen" in line:
                        self.screen_device = re.findall(r"\[(.*?)\]", line)[1]
                        print(f"Screen capture device found: {self.screen_device}")
                        break

                if self.screen_device is None:
                    raise RuntimeError("No screen capture device found.")

            command = [
                "ffmpeg",
                "-f",
                "avfoundation",
                "-framerate",
                "30",
                "-capture_cursor",
                "1",
                "-i",
                self.screen_device,
                "-vf",
                self.resolution_string,
                "-vcodec",
                "h264_videotoolbox",
                "-r",
                "30",
                "-crf",
                "30",
                "-preset",
                "ultrafast",
                "-y",
                filename,
            ]
        else:  # 假定为 Linux
            command = [
                "ffmpeg",
                "-f",
                "x11grab",
                "-framerate",
                "30",
                "-capture_cursor",
                "1",
                "-i",
                ":0.0",
                "-vf",
                self.resolution_string,
                "-vcodec",
                "libx264",
                "-r",
                "30",
                "-crf",
                "30",
                "-preset",
                "ultrafast",
                "-y",
                filename,
            ]

        process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

        # 等待录制开始
        while True:
            line = process.stderr.readline().decode("utf-8")
            if "frame" in line:
                print("Recording started.")
                video_start_time = datetime.now()
                self.video_start_time = video_start_time
                break

        # 等待录制停止的信号
        while not self.stop_event.is_set():
            time.sleep(1)

        # 发送 'q' 信号给 ffmpeg 进程,正常结束录制
        process.communicate(input="q".encode())

        # 等待 ffmpeg 进程完成
        process.wait()

        print("Recording stopped.")

    def on_move(self, x, y):
        action_time = self.relative_time()
        width, height = pyautogui.size()
        self.action_log.append(
            {
                "time": action_time,
                "type": "mouse_move",
                "position": {"x": x / width, "y": y / height},
            }
        )

    def save_log(self):
        filename = os.path.join(self.log_folder, f"mouse_log_{self.current_time}.json")
        with open(filename, "w") as f:
            json.dump(self.action_log, f, indent=4)

    def start_recording(self):
        self.mouse_listener = mouse.Listener(on_move=self.on_move)
        self.mouse_listener.start()

        self.record_thread = threading.Thread(target=self.record_screen)
        self.record_thread.start()

        # 等待5分钟
        self.record_thread.join(timeout=10)

        # 如果录制线程还在运行,则停止录制
        if self.record_thread.is_alive():
            self.stop_recording()

    def stop_recording(self):
        self.stop_event.set()  # Set stop event
        self.stop_listener()  # Stop mouse listener
        if self.record_thread is not None:
            self.record_thread.join()  # Ensure the recording thread has finished
        self.save_log()  # Save log file
        print("Recording stopped and log saved.")

    def stop_listener(self):
        if self.mouse_listener is not None:
            self.mouse_listener.stop()
        if self.mouse_listener is not None:
            self.mouse_listener.join()

def main(selected_folder, resolution):
    recorder = Recorder(selected_folder, resolution)
    print("Recording screen and mouse movement for 5 minutes...")
    recorder.start_recording()
    print("Recording completed.")

if __name__ == "__main__":
    main(os.getcwd(), 720)