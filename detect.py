import json
import threading
from pynput import keyboard, mouse
from datetime import datetime, timedelta
import os
import pyautogui
import time
import ffmpeg
import platform
import re

class Recorder:
    def __init__(self, selected_folder):
        self.video_folder = os.path.join(selected_folder, "videos")
        self.log_folder = os.path.join(selected_folder, "logs")
        self.current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.video_start_time = None
        self.action_log = []
        self.keyboard_buffer = ""
        self.last_key_time = None
        self.mouse_pressed = False
        self.scroll_amount = 0
        self.scroll_buffer = []
        self.scroll_position = None
        self.scroll_direction = None
        self.last_scroll_time = None
        self.record_thread = None
        self.stop_event = threading.Event()
        self.keyboard_listener = None
        self.mouse_listener = None

        # Initialize record folders
        os.makedirs(self.video_folder, exist_ok=True)
        os.makedirs(self.log_folder, exist_ok=True)

    def relative_time(self):
        return (datetime.now() - self.video_start_time).total_seconds()

    def record_screen(self):
        print("\nRecording started.\n")
        filename = f"{self.video_folder}/screen_{self.current_time}.mp4"

        time.sleep(1)  # Add a short delay to ensure the capture device is ready

        # Determine the screen capture method based on the operating system
        if platform.system() == "Windows":
            capture_input = ffmpeg.input("desktop", format="gdigrab", framerate=60, capture_cursor=1)
        elif platform.system() == "Darwin":
            capture_input = ffmpeg.input("2:1", format="avfoundation", pix_fmt="uyvy422", framerate=60, capture_cursor=1)
        else:
            capture_input = ffmpeg.input(":0.0", format="x11grab", framerate=60, capture_cursor=1)

        # Start the recording using ffmpeg-python
        process = (
            capture_input
            .output(filename, vcodec="libx264", r=30, crf=30, preset="fast")
            .overwrite_output()
            .run_async(pipe_stdin=True)
        )
        
        self.video_start_time = datetime.now() + timedelta(seconds=0.32)  # Add a delay to account for ffmpeg startup

        # Wait while recording is active, check every second for a stop signal
        while not self.stop_event.is_set():
            time.sleep(1)

        # Stop the recording by sending a quit signal to ffmpeg
        process.stdin.write("q".encode("utf-8"))
        process.stdin.flush()
        process.wait()

        # Close stdin to make sure the process ends
        process.stdin.close()
    
    def clean_buffer(self, buffer_type):
        if buffer_type == "keyboard":
            if (self.last_key_time and (datetime.now() - self.last_key_time).total_seconds() > 5
                and self.keyboard_buffer):
                    self.action_log.append(
                        {
                            "time": self.relative_time(),
                            "type": "keypress",
                            "keys": self.keyboard_buffer,
                        }
                    )
                    self.keyboard_buffer = ""
        elif buffer_type == "scroll":
            if (self.last_scroll_time and (datetime.now() - self.last_scroll_time).total_seconds() > 5
                and self.scroll_buffer):
                    self.action_log.append(
                        {
                            "time": self.relative_time(),
                            "type": "scroll",
                            "amount": sum(self.scroll_buffer),
                            "position": self.scroll_position,
                        }
                    )
                    self.scroll_buffer = []
                    self.scroll_position = None
                    self.scroll_direction = None

    def on_press(self, key):
        print("\nKey pressed: {0}\n".format(str(key)))
        try:
            print("Key.char: {0}".format(key.char))
            self.clean_buffer("keyboard")
            self.keyboard_buffer += key.char
            self.last_key_time = datetime.now()
        except AttributeError:
            print("Special key {0} pressed".format(key))
            self.clean_buffer("keyboard")
            if self.keyboard_buffer:
                self.action_log.append(
                    {
                        "time": self.relative_time(),
                        "type": "keypress",
                        "keys": self.keyboard_buffer,
                    }
                )
                self.keyboard_buffer = ""
            self.action_log.append(
                {
                    "time": self.relative_time(),
                    "type": "special_key",
                    "key": str(key),
                }
            )
            self.last_key_time = datetime.now()

    def on_click(self, x, y, button, pressed):
        self.clean_buffer("keyboard")
        self.clean_buffer("scroll")
        print("\nMouse clicked: {0}, {1}, {2}, {3}\n".format(x, y, button, pressed))
        width, height = pyautogui.size()
        action_time = self.relative_time()

        if pressed:
            self.mouse_pressed = True
            self.click_start_time = action_time
            self.drag_start = {
                "x": x / width,
                "y": y / height,
                "start_time": action_time
            }
        else:
            self.mouse_pressed = False
            if self.drag_start:
                drag_end = {
                    "x": x / width,
                    "y": y / height,
                    "end_time": action_time
                }
                if (
                    abs(self.drag_start["x"] - drag_end["x"]) > 0.01 or
                    abs(self.drag_start["y"] - drag_end["y"]) > 0.01
                ):
                    self.action_log.append({
                        "time": action_time,
                        "type": "drag",
                        "start": self.drag_start,
                        "end": drag_end,
                    })
                else:
                    self.action_log.append({
                        "time": action_time,
                        "type": "click",
                        "button": str(button),
                        "position": {"x": x / width, "y": y / height},
                    })
                self.drag_start = None
                self.click_start_time = None

    def on_scroll(self, x, y, dx, dy):
        print("\nMouse scrolled: {0}, {1}, {2}, {3}\n".format(x, y, dx, dy))
        self.clean_buffer("keyboard")
        width, height = pyautogui.size()
        current_position = {"x": x / width, "y": y / height}
        current_direction = 1 if dy > 0 else -1

        if self.scroll_position is None or self.scroll_direction is None:
            self.scroll_position = current_position
            self.scroll_direction = current_direction
        elif (
            abs(self.scroll_position["x"] - current_position["x"]) > 0.01 or
            abs(self.scroll_position["y"] - current_position["y"]) > 0.01 or
            self.scroll_direction != current_direction
        ):
            self.clean_buffer("scroll")
            self.scroll_position = current_position
            self.scroll_direction = current_direction

        self.scroll_buffer.append(dy)
        self.last_scroll_time = datetime.now()
        threading.Timer(0.5, self.log_scroll_event).start()

    def log_scroll_event(self):
            if self.last_scroll_time and (datetime.now() - self.last_scroll_time).total_seconds() > 0.5:
                total_scroll = sum(self.scroll_buffer)
                if total_scroll != 0:
                    self.action_log.append(
                        {
                            "time": self.relative_time(),
                            "type": "scroll",
                            "amount": total_scroll,
                            "position": self.scroll_position,
                        }
                    )
                self.scroll_buffer = []
                self.scroll_position = None
                self.scroll_direction = None

    def save_log(self):
        filename = f"{self.log_folder}/log_{self.current_time}.json"
        with open(filename, "w") as f:
            json.dump(self.action_log, f, indent=4)

    def start_recording(self):
        self.keyboard_listener = keyboard.Listener(on_press=self.on_press)
        self.mouse_listener = mouse.Listener(on_click=self.on_click, on_scroll=self.on_scroll)

        with self.keyboard_listener as kl, self.mouse_listener as ml:
            screen_record_thread = threading.Thread(target=self.record_screen)
            screen_record_thread.start()
            kl.join()
            ml.join()
            screen_record_thread.join()
        self.save_log()
        print("Recording and logging stopped. Log saved.")

    def stop_recording(self):
        self.stop_event.set()  # 设置停止事件，让录制线程可以优雅地结束
        self.stop_listeners()  # 停止键盘和鼠标监听器
        if self.record_thread is not None:
            self.record_thread.join()  # 确保录制线程已经结束
        self.save_log()  # 保存日志文件
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
        print("Recording stopped by user.")
        recorder.stop_recording()

if __name__ == "__main__":
    main(os.getcwd())
