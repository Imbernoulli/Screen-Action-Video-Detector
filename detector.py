import tkinter as tk
from tkinter import filedialog
from threading import Thread, Timer
import os
from detect import Recorder  # 确保 recorder.py 文件和这个文件在同一个目录下


class RecorderGUI:
    def __init__(self, master):
        self.master = master
        self.recorder = Recorder(os.getcwd())
        self.recording_thread = None
        self.timer = None
        self.recording_duration = 300  # 默认录制时长,单位为秒

        self.master.title("Screen Recorder")

        self.duration_frame = tk.Frame(master)
        self.duration_frame.pack()

        self.duration_label = tk.Label(
            self.duration_frame, text="Recording Duration (seconds):"
        )
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

        self.selected_folder = tk.StringVar()
        self.selected_folder.set(os.getcwd())
        self.folder_label = tk.Label(master, textvariable=self.selected_folder)
        self.folder_label.pack()

    def start_recording(self):
        duration = self.duration_entry.get()
        if duration.isdigit():
            self.recording_duration = int(duration)
        else:
            self.recording_duration = 300  # 如果输入无效,使用默认值

        self.recorder.init(self.selected_folder.get())
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
