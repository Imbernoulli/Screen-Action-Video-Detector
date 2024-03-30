```bash
conda create -n det python=3.12
conda activate det
conda install -c conda-forge pynput pyautogui ffmpeg-python
```



`detector.py`是`detect.py`的前端,`detector`是没有依赖的可执行文件。

`detect.py`和`recorder.py`本质上没有区别，都是可以直接运行，然后`Ctrl + C`停止并保存。

现在`detector.py`还有概率会视频保存失败，正在尝试调整。