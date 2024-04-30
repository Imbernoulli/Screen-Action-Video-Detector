import json
import os
import cv2
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, SubsetRandomSampler
from torchvision import transforms
import numpy as np

# 定义自定义数据集
class MouseMoveDataset(Dataset):
    def __init__(self, video_folder, log_folder, transform=None):
        self.video_folder = video_folder
        self.log_folder = log_folder
        self.transform = transform

        self.video_files = [f for f in os.listdir(video_folder) if f.endswith(".mp4")]
        self.log_files = [f for f in os.listdir(log_folder) if f.endswith(".json")]

        self.mouse_move_events = []
        for log_file in self.log_files:
            print(log_file)
            with open(os.path.join(self.log_folder, log_file), "r") as f:
                log_data = json.load(f)
            self.mouse_move_events.extend(
                [
                    (log_file[:-5], event)
                    for event in log_data
                    if event["type"] == "mouse_move"
                ]
            )

    def __len__(self):
        return len(self.mouse_move_events)

    def __getitem__(self, idx):
        video_name, event = self.mouse_move_events[idx]
        video_path = os.path.join(self.video_folder, f"{video_name.replace("log","screen")}.mp4")
        
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")
        
        video_duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)
        frame_time = min(event["time"], video_duration)
        
        # 找到最接近事件时间戳的帧
        cap.set(cv2.CAP_PROP_POS_MSEC, frame_time * 1000)
        ret, frame = cap.read()
        
        if not ret:
            # 如果无法读取指定帧,尝试读取上一帧
            cap.set(cv2.CAP_PROP_POS_FRAMES, cap.get(cv2.CAP_PROP_POS_FRAMES) - 1)
            ret, frame = cap.read()
        
        cap.release()

        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            if self.transform:
                frame = self.transform(frame)
        else:
            print(f"Could not read frame at time {frame_time} from video {video_name}")
            # 如果仍然无法读取帧,返回默认的黑色图像
            frame = np.zeros((480, 480, 3), dtype=np.uint8)
            frame = self.transform(frame) if self.transform else frame

        mouse_position = torch.tensor(
            [event["position"]["x"], event["position"]["y"]], dtype=torch.float32
        )

        return frame, mouse_position

# 定义模型架构
class MousePositionPredictor(nn.Module):
    def __init__(self):
        super(MousePositionPredictor, self).__init__()
        self.conv1 = nn.Conv2d(3, 16, kernel_size=3, stride=1, padding=1)
        self.relu1 = nn.ReLU(inplace=True)
        self.pool1 = nn.MaxPool2d(kernel_size=2, stride=2)
        self.conv2 = nn.Conv2d(16, 32, kernel_size=3, stride=1, padding=1)
        self.relu2 = nn.ReLU(inplace=True)
        self.pool2 = nn.MaxPool2d(kernel_size=2, stride=2)
        self.fc1 = nn.Linear(32 * 120 * 120, 256)
        self.relu3 = nn.ReLU(inplace=True)
        self.fc2 = nn.Linear(256, 2)

    def forward(self, x):
        x = self.conv1(x)
        x = self.relu1(x)
        x = self.pool1(x)
        x = self.conv2(x)
        x = self.relu2(x)
        x = self.pool2(x)
        x = x.view(x.size(0), -1)
        x = self.fc1(x)
        x = self.relu3(x)
        x = self.fc2(x)
        return x
# 训练函数
def train(model, dataloader, criterion, optimizer, device):
    model.train()
    running_loss = 0.0
    for images, mouse_positions in dataloader:
        images = images.to(device)
        mouse_positions = mouse_positions.to(device)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, mouse_positions)
        loss.backward()
        optimizer.step()

        running_loss += loss.item() * images.size(0)
    return running_loss / len(dataloader.dataset)

# 测试函数
def test(model, dataloader, criterion, device):
    model.eval()
    running_loss = 0.0
    with torch.no_grad():
        for images, mouse_positions in dataloader:
            images = images.to(device)
            mouse_positions = mouse_positions.to(device)

            outputs = model(images)
            loss = criterion(outputs, mouse_positions)

            running_loss += loss.item() * images.size(0)
    return running_loss / len(dataloader.dataset)

# 主函数
def main():
    # 设置参数
    video_folder = "cursor_data"
    log_folder = "cursor_data"
    batch_size = 32
    num_epochs = 10
    learning_rate = 0.001
    num_splits = 5  # k折交叉验证的折数
    save_path = "path/to/save/model.pth"

    # 设置设备
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # 创建数据集和数据加载器
    transform = transforms.Compose(
        [
            transforms.ToPILImage(),
            transforms.Resize((480, 480)),
            transforms.ToTensor(),
            transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)),
        ]
    )
    
    dataset = MouseMoveDataset(video_folder, log_folder, transform=transform)

    # 划分数据集为训练集和验证集
    dataset_size = len(dataset)
    indices = list(range(dataset_size))
    split_size = dataset_size // num_splits

    best_loss = float("inf")
    best_model_state_dict = None

    for fold in range(num_splits):
        print(f"Fold [{fold+1}/{num_splits}]")

        val_start = fold * split_size
        val_end = (fold + 1) * split_size if fold < num_splits - 1 else dataset_size
        train_indices = indices[:val_start] + indices[val_end:]
        val_indices = indices[val_start:val_end]

        train_sampler = SubsetRandomSampler(train_indices)
        val_sampler = SubsetRandomSampler(val_indices)

        train_loader = DataLoader(dataset, batch_size=batch_size, sampler=train_sampler)
        val_loader = DataLoader(dataset, batch_size=batch_size, sampler=val_sampler)

        # 创建模型、损失函数和优化器
        model = MousePositionPredictor().to(device)
        criterion = nn.MSELoss()
        optimizer = optim.Adam(model.parameters(), lr=learning_rate)

        # 训练模型
        for epoch in range(num_epochs):
            train_loss = train(model, train_loader, criterion, optimizer, device)
            val_loss = test(model, val_loader, criterion, device)
            print(f"Epoch [{epoch+1}/{num_epochs}], Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}")

        # 保存最佳模型
        if val_loss < best_loss:
            best_loss = val_loss
            best_model_state_dict = model.state_dict()

    # 保存最佳模型参数
    torch.save(best_model_state_dict, save_path)
    print(f"Best model saved to {save_path} with validation loss {best_loss:.4f}")

if __name__ == "__main__":
    main()