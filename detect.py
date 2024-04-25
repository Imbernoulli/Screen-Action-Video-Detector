import json
import threading
from pynput import keyboard, mouse
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
        self.keyboard_buffer = ""
        self.last_key_time = None
        self.keyboard_start_time = None
        self.mouse_pressed = False
        self.scroll_amount = 0
        self.scroll_buffer = []
        self.scroll_position = None
        self.scroll_direction = None
        self.last_scroll_time = None
        self.scroll_start_time = None
        self.record_thread = None
        self.stop_event = threading.Event()
        self.keyboard_listener = None
        self.mouse_listener = None
        self.screen_device = None
        self.drag_start = None

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
                "-thread_queue_size",
                "256",
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
                self.renew_time(self.video_start_time, video_start_time)
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

    def renew_time(self, old_time, new_time):
        for action in self.action_log:
            if "time" in action:
                action["time"] = action["time"] - (old_time - new_time).total_seconds()
            else:
                action["start_time"] = (
                    action["start_time"] - (old_time - new_time).total_seconds()
                )
                action["end_time"] = (
                    action["end_time"] - (old_time - new_time).total_seconds()
                )

    def clean_buffer(self, buffer_type):
        action_time = self.relative_time()
        if buffer_type == "keyboard":
            if (
                self.last_key_time
                and (datetime.now() - self.last_key_time).total_seconds() > 5
                and self.keyboard_buffer
            ):
                self.action_log.append(
                    {
                        "start_time": self.keyboard_start_time,
                        "end_time": action_time,
                        "type": "keypress",
                        "keys": self.keyboard_buffer,
                    }
                )
                self.keyboard_buffer = ""
                self.keyboard_start_time = None
        elif buffer_type == "scroll":
            if (
                self.last_scroll_time
                and (datetime.now() - self.last_scroll_time).total_seconds() > 5
                and self.scroll_buffer
            ):
                self.action_log.append(
                    {
                        "start_time": self.scroll_start_time,
                        "end_time": action_time,
                        "type": "scroll",
                        "amount": sum(self.scroll_buffer),
                        "position": self.scroll_position,
                    }
                )
                self.scroll_buffer = []
                self.scroll_position = None
                self.scroll_direction = None
                self.scroll_start_time = None

    def on_press(self, key):
        action_time = self.relative_time()
        # print("\nKey pressed: {0}\n".format(str(key)))
        try:
            # print("Key.char: {0}".format(key.char))
            self.clean_buffer("keyboard")
            if not self.keyboard_start_time:
                self.keyboard_start_time = action_time
            self.keyboard_buffer += key.char
            self.last_key_time = datetime.now()
        except AttributeError:
            # print("Special key {0} pressed".format(key))
            self.clean_buffer("keyboard")
            if self.keyboard_buffer:
                self.action_log.append(
                    {
                        "start_time": self.keyboard_start_time,
                        "end_time": action_time,
                        "type": "keypress",
                        "keys": self.keyboard_buffer,
                    }
                )
                self.keyboard_buffer = ""
                self.keyboard_start_time = None
            self.action_log.append(
                {
                    "time": action_time,
                    "type": "special_key",
                    "key": str(key),
                }
            )
            self.last_key_time = datetime.now()

    def on_click(self, x, y, button, pressed):
        action_time = self.relative_time()
        self.clean_buffer("keyboard")
        self.clean_buffer("scroll")
        # print("\nMouse clicked: {0}, {1}, {2}, {3}\n".format(x, y, button, pressed))
        width, height = pyautogui.size()
        action_time = action_time

        if pressed:
            self.mouse_pressed = True
            self.click_start_time = action_time
            self.drag_start = {
                "x": x / width,
                "y": y / height,
                "start_time": action_time,
            }
        else:
            self.mouse_pressed = False
            if self.drag_start:
                drag_end = {"x": x / width, "y": y / height, "end_time": action_time}
                if (
                    abs(self.drag_start["x"] - drag_end["x"]) > 0.01
                    or abs(self.drag_start["y"] - drag_end["y"]) > 0.01
                ):
                    self.action_log.append(
                        {
                            "start_time": self.drag_start["start_time"],
                            "end_time": drag_end["end_time"],
                            "type": "drag",
                            "start": self.drag_start,
                            "end": drag_end,
                        }
                    )
                else:
                    self.action_log.append(
                        {
                            "time": action_time,
                            "type": "click",
                            "button": str(button),
                            "position": {"x": x / width, "y": y / height},
                        }
                    )
                self.drag_start = None
                self.click_start_time = None

    def on_scroll(self, x, y, dx, dy):
        action_time = self.relative_time()
        # print("\nMouse scrolled: {0}, {1}, {2}, {3}\n".format(x, y, dx, dy))
        self.clean_buffer("keyboard")
        width, height = pyautogui.size()
        current_position = {"x": x / width, "y": y / height}
        current_direction = 1 if dy > 0 else -1

        if self.scroll_position is None or self.scroll_direction is None:
            self.scroll_position = current_position
            self.scroll_direction = current_direction
            self.scroll_start_time = action_time
        elif (
            abs(self.scroll_position["x"] - current_position["x"]) > 0.01
            or abs(self.scroll_position["y"] - current_position["y"]) > 0.01
            or self.scroll_direction != current_direction
        ):
            self.clean_buffer("scroll")
            self.scroll_position = current_position
            self.scroll_direction = current_direction
            self.scroll_start_time = action_time

        self.scroll_buffer.append(dy)
        self.last_scroll_time = datetime.now()
        threading.Timer(0.5, self.log_scroll_event).start()

    def log_scroll_event(self):
        action_time = self.relative_time()
        if (
            self.last_scroll_time
            and (datetime.now() - self.last_scroll_time).total_seconds() > 0.5
        ):
            total_scroll = sum(self.scroll_buffer)
            if total_scroll != 0:
                self.action_log.append(
                    {
                        "start_time": self.scroll_start_time,
                        "end_time": action_time,
                        "type": "scroll",
                        "amount": total_scroll,
                        "position": self.scroll_position,
                    }
                )
            self.scroll_buffer = []
            self.scroll_position = None
            self.scroll_direction = None
            self.scroll_start_time = None

    def save_log(self):
        filename = os.path.join(self.log_folder, f"log_{self.current_time}.json")
        with open(filename, "w") as f:
            json.dump(self.action_log, f, indent=4)

    def start_recording(self):
        self.keyboard_listener = keyboard.Listener(on_press=self.on_press)
        self.mouse_listener = mouse.Listener(
            on_click=self.on_click, on_scroll=self.on_scroll
        )

        with self.keyboard_listener as kl, self.mouse_listener as ml:
            self.record_thread = threading.Thread(target=self.record_screen)
            self.record_thread.start()
            kl.join()
            ml.join()

        print("Recording and logging stopped. Log saved.")

    def stop_recording(self):
        self.stop_event.set()  # 设置停止事件,让录制线程可以优雅地结束
        self.stop_listeners()  # 停止键盘和鼠标监听器
        if self.record_thread is not None:
            self.record_thread.join()  # Ensure the recording thread has finished
        self.save_log()  # Save log file
        print("Recording stopped and log saved.")

    def stop_listeners(self):
        # 显式地停止键盘和鼠标监听器
        if self.keyboard_listener is not None:
            self.keyboard_listener.stop()
        if self.mouse_listener is not None:
            self.mouse_listener.stop()
        # 确保监听器的线程已经结束
        if self.keyboard_listener is not None:
            self.keyboard_listener.join()
        if self.mouse_listener is not None:
            self.mouse_listener.join()


def main(selected_folder):
    recorder = Recorder(selected_folder)
    try:
        recorder.start_recording()
    except KeyboardInterrupt:
        # print("Recording stopped by user.")
        recorder.stop_recording()


if __name__ == "__main__":
    main(os.getcwd())
