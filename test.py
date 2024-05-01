import cv2
import numpy as np
import matplotlib.pyplot as plt


def gradient(image):
    # 计算图像的x和y方向的梯度
    grad_x = cv2.Sobel(image, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(image, cv2.CV_32F, 0, 1, ksize=3)
    # 计算梯度的合成
    grad = cv2.magnitude(grad_x, grad_y)
    return grad


def template_matching(image_path, template_path, method=cv2.TM_CCOEFF_NORMED):
    # 读取图像和模板
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)

    # 计算图像和模板的梯度
    image_grad = gradient(image)
    template_grad = gradient(template)

    # 模板匹配
    result = cv2.matchTemplate(image_grad, template_grad, method)

    print(result)

    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    print(min_val, max_val, min_loc, max_loc)

    # 根据匹配方法选择最佳匹配位置
    if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
        top_left = min_loc
    else:
        top_left = max_loc

    # 计算模板的宽高
    h, w = template.shape

    # 标记匹配区域
    bottom_right = (top_left[0] + w, top_left[1] + h)
    cv2.rectangle(image, top_left, bottom_right, (255), 2)

    # 为了显示，将图像转换回彩色
    image_display = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    cv2.rectangle(image_display, top_left, bottom_right, (255, 0, 0), 2)

    # 显示结果
    plt.imshow(image_display)
    plt.title("Template Matching Result in Gradient Domain")
    plt.show()

    return top_left, bottom_right


# 使用示例
image_path = "/Users/bernoulli_hermes/projects/cad/detect/output/frame_178.png"
template_path = (
    "/Users/bernoulli_hermes/projects/cad/detect/cursors/positive/frame_56.png"
)
top_left, bottom_right = template_matching(image_path, template_path)

print("Match location: Top left corner", top_left, "Bottom right corner:", bottom_right)
