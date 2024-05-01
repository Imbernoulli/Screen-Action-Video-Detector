import tkinter as tk
from tkinter import filedialog, messagebox
from threading import Thread, Timer
import webbrowser
import os
from detect import Recorder  # 确保 recorder.py 文件和这个文件在同一个目录下
import platform


class RecorderGUI:
    def __init__(self, master):
        self.master = master
        self.recorder = Recorder(os.getcwd(), 720, None)
        self.recording_thread = None
        self.timer = None
        self.recording_duration = 300  # 默认录制时长,单位为秒

        self.master.title("Screen Recorder")

        self.resolution_frame = tk.Frame(master)
        self.resolution_frame.pack()

        self.resolution_label = tk.Label(
            self.resolution_frame, text="Vertical Resolution:"
        )
        self.resolution_label.pack(side=tk.LEFT)

        self.resolution_entry = tk.Entry(self.resolution_frame)
        self.resolution_entry.insert(0, "720")  # Default resolution
        self.resolution_entry.pack(side=tk.LEFT)

        if platform.system() == "Windows":
            self.thread_label = tk.Label(self.resolution_frame, text="Thread:")
            self.thread_label.pack(side=tk.LEFT)

            self.thread_entry = tk.Entry(self.resolution_frame)
            self.thread_entry.insert(0, "256")  # Default resolution
            self.thread_entry.pack(side=tk.LEFT)

        self.duration_frame = tk.Frame(master)
        self.duration_frame.pack()

        self.duration_label = tk.Label(self.duration_frame, text="Recording Duration:")
        self.duration_label.pack(side=tk.LEFT)

        self.duration_entry = tk.Entry(self.duration_frame)
        self.duration_entry.insert(0, str(self.recording_duration))
        self.duration_entry.pack(side=tk.LEFT)

        self.start_button = tk.Button(
            master, text="Start Recording", command=self.start_recording
        )
        self.start_button.pack()

        self.stop_button = tk.Button(
            master,
            text="Stop Recording",
            command=self.stop_recording,
            state=tk.DISABLED,
        )
        self.stop_button.pack()

        self.select_folder_button = tk.Button(
            master, text="Select Folder", command=self.select_folder
        )
        self.select_folder_button.pack()

        self.web_button = tk.Button(
            master,
            text="上传",
            command=lambda: self.open_webpage(
                "https://cloud.tsinghua.edu.cn/u/d/94e37566dc6c4bc0afcd/"
            ),
        )
        self.web_button.pack()

        self.manual_button = tk.Button(
            master, text="Show Manual", command=self.show_manual
        )
        self.manual_button.pack()

        self.selected_folder = tk.StringVar()
        self.selected_folder.set(os.getcwd())
        self.folder_label = tk.Label(master, textvariable=self.selected_folder)
        self.folder_label.pack()

    def open_webpage(
        self, url="https://cloud.tsinghua.edu.cn/u/d/94e37566dc6c4bc0afcd/"
    ):
        webbrowser.open(url)

    def show_manual(self):
        manual_text = """
        Screen Recorder Application Manual
        ----------------------------------
        This application allows you to record your screen.
        
        Instructions:
        - Enter the desired resolution and duration.
        - Click 'Start Recording' to begin recording.
        - Click 'Stop Recording' to stop and save the video.
        - Use 'Select Folder' to choose where to save the video files.
        - Click 'Open Google' to open Google in your web browser.
        
        For more information, contact support@example.com.
        """
        messagebox.showinfo("User Manual", manual_text)

    def start_recording(self):
        resolution = self.resolution_entry.get()
        try:
            resolution = int(resolution)  # Validate and convert to integer
        except ValueError:
            resolution = 720  # Default if invalid input

        duration = self.duration_entry.get()
        if duration.isdigit():
            self.recording_duration = int(duration)
        else:
            self.recording_duration = 300  # 如果输入无效,使用默认值

        thread = None
        if platform.system() == "Windows":
            thread = self.thread_entry.get()
            if thread.isdigit():
                thread = int(thread)
            else:
                thread = 256

        self.recorder.init(self.selected_folder.get(), resolution, thread)
        self.recording_thread = Thread(target=self.recorder.start_recording)
        self.recording_thread.start()
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.select_folder_button.config(state=tk.DISABLED)
        if self.timer is not None:
            self.timer.cancel()
        self.timer = Timer(self.recording_duration, self.restart_recording)
        self.timer.start()

    def stop_recording(self):
        if self.recorder is not None:
            self.recorder.stop_recording()
        if self.recording_thread is not None:
            self.recording_thread.join()
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.select_folder_button.config(state=tk.NORMAL)
        self.recording_thread = None
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.selected_folder.set(folder)

    def restart_recording(self):
        self.stop_recording()
        self.start_recording()


def main():
    root = tk.Tk()
    gui = RecorderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
