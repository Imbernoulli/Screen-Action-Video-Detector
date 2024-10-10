```bash
conda create -n det python=3.12
conda activate det
pip install pynput pyautogui
python detector.py
```

To install `ffmpeg`.

MAC: `brew install ffmpeg`

Win: [Download](https://ffmpeg.org/download.html)

`detector.py`是`detect.py`的前端

`check.py`是用来检查是否对上的，可以在`test.pdf`中点击。`check.py`可以设置offset来保证对齐。

有关对齐：极早期数据会有offset，log中的相对时差没有问题，只要添加一个offset就没有问题了。

```bash
pip install opencv-python
```

Welcome to [Upload](https://cloud.tsinghua.edu.cn/u/d/94e37566dc6c4bc0afcd/)!
