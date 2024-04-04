def process_image(image_path, output_folder):
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # 高斯模糊
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    preprocessed = blurred
    
    # 自适应阈值化
    thresholded = cv2.adaptiveThreshold(preprocessed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    
    # 闭运算和膨胀
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    closed = cv2.morphologyEx(thresholded, cv2.MORPH_CLOSE, kernel)
    dilated = cv2.dilate(closed, kernel, iterations=1)
    
    # Sobel边缘检测
    sobelx = cv2.Sobel(dilated, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(dilated, cv2.CV_64F, 0, 1, ksize=3)
    sobel = cv2.bitwise_or(sobelx, sobely)
    sobel = cv2.convertScaleAbs(sobel)
    
    edges = sobel 
    
    edges = cv2.dilate(edges, None, iterations=1)
    
    # 轮廓分析
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 合并相邻轮廓
    merged_contours = merge_contours(contours, 50)
    
    for contour in merged_contours:
        area = cv2.contourArea(contour)
        
        if area < 100:
            continue
        
        x, y, w, h = cv2.boundingRect(contour)
        cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
    
    # 保存结果
    filename = os.path.splitext(os.path.basename(image_path))[0]
    output_filename = f"{filename}_result.jpg"
    cv2.imwrite(os.path.join(output_folder, output_filename), image)
