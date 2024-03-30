import tkinter as tk
from tkinter import filedialog
from threading import Thread
import os
from detect import Recorder  # 确保 recorder.py 文件和这个文件在同一个目录下

class RecorderGUI:
    def __init__(self, master):
        self.master = master
        self.recorder = None
        self.recording_thread = None

        self.master.title("Screen Recorder")

        self.start_button = tk.Button(master, text="Start Recording", command=self.start_recording)
        self.start_button.pack()

        self.stop_button = tk.Button(master, text="Stop Recording", command=self.stop_recording, state=tk.DISABLED)
        self.stop_button.pack()

        self.select_folder_button = tk.Button(master, text="Select Folder", command=self.select_folder)
        self.select_folder_button.pack()

        self.selected_folder = tk.StringVar()
        self.selected_folder.set(os.getcwd())
        self.folder_label = tk.Label(master, textvariable=self.selected_folder)
        self.folder_label.pack()

    def start_recording(self):
        if self.recorder is not None:
            self.recorder.stop_recording()
        self.recorder = Recorder(self.selected_folder.get())
        self.recording_thread = Thread(target=self.recorder.start_recording)
        self.recording_thread.start()
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

    def stop_recording(self):
        if self.recorder is not None:
            self.recorder.stop_recording()
        if self.recording_thread is not None:
            self.recording_thread.join()
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.recorder = None
        self.recording_thread = None

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.selected_folder.set(folder)

def main():
    root = tk.Tk()
    gui = RecorderGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
