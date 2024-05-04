import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, SubsetRandomSampler
from torchvision import models, transforms
import numpy as np
import cv2
import os
import json

class MouseMoveDataset(Dataset):
    def __init__(self, video_folder, log_folder, transform=None):
        self.video_folder = video_folder
        self.log_folder = log_folder
        self.transform = transform

        self.video_files = [f for f in os.listdir(video_folder) if f.endswith(".mp4")]
        self.log_files = [f for f in os.listdir(log_folder) if f.endswith(".json")]

        self.mouse_move_events = []
        for log_file in self.log_files:
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
        video_path = os.path.join(self.video_folder, f"{video_name.replace('log','screen')}.mp4")
        
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")
        
        video_duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)
        frame_time = min(event["time"], video_duration)
        
        cap.set(cv2.CAP_PROP_POS_MSEC, frame_time * 1000)
        ret, frame = cap.read()
        cap.release()

        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        else:
            frame = np.zeros((480, 480, 3), dtype=np.uint8)

        if self.transform:
            frame = self.transform(frame)

        mouse_position = [event["position"]["x"], event["position"]["y"]]

        return frame, mouse_position

def create_model(num_classes):
    # Load a pre-trained SSD model
    model = models.detection.ssd300_vgg16(pretrained=True)
    
    # Replace the classifier head with a new one
    num_anchors = model.anchor_generator.num_anchors_per_location()[0]
    model.head.classification_head = nn.Conv2d(512, num_anchors * num_classes, kernel_size=3, padding=1)
    model.head.regression_head = nn.Conv2d(512, num_anchors * 4, kernel_size=3, padding=1)
    
    return model

def train(model, dataloader, criterion, optimizer, device):
    model.train()
    running_loss = 0.0
    for images, targets in dataloader:
        images = images.to(device)
        targets = [{'boxes': torch.tensor([t], dtype=torch.float32, device=device),
                    'labels': torch.tensor([1], dtype=torch.int64, device=device)} 
                   for t in targets]
        
        optimizer.zero_grad()
        loss_dict = model(images, targets)
        losses = sum(loss for loss in loss_dict.values())
        
        losses.backward()
        optimizer.step()

        running_loss += losses.item() * images.size(0)
    return running_loss / len(dataloader.dataset)

import torchvision.transforms as T

def main():
    # 设置数据集文件夹和日志文件夹路径
    video_folder = "cursor_data"
    log_folder = "cursor_data"
        
    # 设置数据转换
    transform = T.Compose([
        T.ToPILImage(),
        T.Resize((300, 300)),  # 根据SSD300的输入大小调整
        T.ToTensor(),
        T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    # 初始化数据集
    dataset = MouseMoveDataset(video_folder, log_folder, transform=transform)
    
    # 创建数据加载器
    dataloader = DataLoader(dataset, batch_size=4, shuffle=True)
    
    # 创建模型
    num_classes = 2  # 包括背景类
    model = create_model(num_classes)
    
    # 将模型发送到GPU
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    
    # 定义损失函数和优化器
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.SGD(model.parameters(), lr=0.005, momentum=0.9)
    
    # 训练模型
    num_epochs = 10
    for epoch in range(num_epochs):
        print(f"Epoch {epoch+1}/{num_epochs}")
        train_loss = train(model, dataloader, criterion, optimizer, device)
        print(f"Training loss: {train_loss:.4f}")
    
    # 保存模型
    torch.save(model.state_dict(), 'mouse_detection_model.pth')
    print("Model saved to mouse_detection_model.pth")

if __name__ == "__main__":
    main()