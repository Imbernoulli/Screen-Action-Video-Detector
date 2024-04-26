import requests

url = "https://cloud.tsinghua.edu.cn/94e37566dc6c4bc0afcd/upload"
file_path = "test.py"

with open(file_path, "rb") as f:
    files = {"file": f}
    response = requests.post(url, files=files)
    print(response.text)