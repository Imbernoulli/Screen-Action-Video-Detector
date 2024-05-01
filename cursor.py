import time
import threading
import pyautogui
from datetime import datetime
import os
import platform
import subprocess
import re
import keyboard


class ScreenRecorder:
    def __init__(self, video_folder, resolution_string, thread_queue_size=512):
        self.video_folder = video_folder
        self.resolution_string = resolution_string
        self.thread_queue_size = str(thread_queue_size)
        self.stop_event = threading.Event()
        self.video_start_time = datetime.now()
        self.current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.screen_device = None

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
                "-thread_queue_size",
                self.thread_queue_size,
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
                "60",
                "-capture_cursor",
                "1",
                "-i",
                self.screen_device,
                "-vf",
                self.resolution_string,
                "-vcodec",
                "h264_videotoolbox",
                "-r",
                "60",
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

        # 在 Windows 上隐藏 ffmpeg 的控制台窗口
        if platform.system() == "Windows":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo,
            )
        else:
            process = subprocess.Popen(
                command, stdin=subprocess.PIPE, stderr=subprocess.PIPE
            )

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

    def relative_time(self):
        return (datetime.now() - self.video_start_time).total_seconds()

    def record_mouse_position(self):
        print("Recording mouse position started.")
        mouse_positions = []

        while not self.stop_event.is_set():
            x, y = pyautogui.position()
            timestamp = self.relative_time()
            mouse_positions.append(f"{timestamp},{x},{y}")
            time.sleep(0.001)  # 每毫秒记录一次鼠标位置

        print("Recording mouse position stopped.")
        self.save_mouse_positions(mouse_positions)

    def save_mouse_positions(self, mouse_positions):
        filename = os.path.join(
            self.video_folder, f"mouse_positions_{self.current_time}.csv"
        )
        with open(filename, "w") as file:
            file.write("timestamp,x,y\n")
            file.write("\n".join(mouse_positions))
        print(f"Mouse positions saved to {filename}")

    def start_recording(self):
        screen_recording_thread = threading.Thread(target=self.record_screen)
        mouse_recording_thread = threading.Thread(target=self.record_mouse_position)

        screen_recording_thread.start()
        mouse_recording_thread.start()

        print("Press 'Enter' to stop recording...")
        input()

        self.stop_event.set()

        screen_recording_thread.join()
        mouse_recording_thread.join()


if __name__ == "__main__":
    video_folder = "."
    resolution_string = "scale=1920:1080"

    recorder = ScreenRecorder(video_folder, resolution_string)
    recorder.start_recording()
