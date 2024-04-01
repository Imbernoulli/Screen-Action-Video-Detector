```bash
conda create -n det python=3.12
conda activate det
pip install pynput pyautogui ffmpeg-python
python detector.py
```

To install `ffmpeg`.

MAC: `brew install ffmpeg`

Win: [Download](https://ffmpeg.org/download.html)

I don't whether you need above two commands. 

`detector.py`是`detect.py`的前端

`detect.py`和`recorder.py`本质上没有区别，都是可以直接运行，然后`Ctrl + C`停止并保存。

`check.py`是用来检查是否对上的，可以在`test.pdf`中点击。`check.py`可以设置offset来保证对其。

```bash
pip install opencv-python
```

Welcome to [Upload](https://cloud.tsinghua.edu.cn/u/d/94e37566dc6c4bc0afcd/)!