# coding:utf-8
"""
图片主题色提取工具
使用 K-means 聚类算法提取图片的主要颜色
"""
from typing import List, Tuple, Optional
import os


class ImageColorExtractor:
    """图片颜色提取器"""
    
    def __init__(self):
        """初始化颜色提取器"""
        self.dominant_colors = []
        self.rgb_colors = []
        self.hex_colors = []
    
    def extract_colors(self, image_path: str, num_colors: int = 5, resize_width: int = 150) -> List[Tuple[int, int, int]]:
        """
        从图片中提取主要颜色
        
        Args:
            image_path: 图片路径
            num_colors: 要提取的颜色数量，默认5个
            resize_width: 为了提高性能，先将图片缩放到此宽度，默认150px
            
        Returns:
            List[Tuple[int, int, int]]: RGB颜色列表
        """
        try:
            from PIL import Image
            import numpy as np
            from sklearn.cluster import KMeans
        except ImportError as e:
            print(f"缺少必要的库: {e}")
            print("请安装: pip install Pillow scikit-learn numpy")
            return []
        
        if not os.path.exists(image_path):
            print(f"图片文件不存在: {image_path}")
            return []
        
        try:
            # 加载并缩放图片以提高性能
            img = Image.open(image_path)
            
            # 转换为RGB模式（去除透明通道）
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 缩放图片以提高处理速度
            ratio = resize_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((resize_width, new_height), Image.Resampling.LANCZOS)
            
            # 将图片转换为numpy数组
            img_array = np.array(img)
            
            # 将图片重塑为二维数组 (像素数, 3)
            pixels = img_array.reshape(-1, 3)
            
            # 使用K-means聚类找到主要颜色
            kmeans = KMeans(n_clusters=num_colors, random_state=42, n_init=10)
            kmeans.fit(pixels)
            
            # 获取聚类中心（主要颜色）
            colors = kmeans.cluster_centers_.astype(int)
            
            # 计算每个聚类的样本数量，用于排序
            labels = kmeans.labels_
            label_counts = np.bincount(labels)
            
            # 按出现频率排序
            sorted_indices = np.argsort(label_counts)[::-1]
            sorted_colors = colors[sorted_indices]
            
            # 转换为元组列表
            self.rgb_colors = [tuple(color) for color in sorted_colors]
            self.hex_colors = [self.rgb_to_hex(color) for color in self.rgb_colors]
            self.dominant_colors = list(zip(self.rgb_colors, self.hex_colors))
            
            return self.rgb_colors
            
        except Exception as e:
            print(f"提取颜色时出错: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_dominant_color(self, image_path: str) -> Optional[Tuple[int, int, int]]:
        """
        获取图片的主要颜色（出现最多的颜色）
        
        Args:
            image_path: 图片路径
            
        Returns:
            Tuple[int, int, int]: RGB颜色值，如果失败返回None
        """
        colors = self.extract_colors(image_path, num_colors=1)
        return colors[0] if colors else None
    
    def get_color_palette(self, image_path: str, num_colors: int = 5) -> List[str]:
        """
        获取图片的调色板（十六进制颜色列表）
        
        Args:
            image_path: 图片路径
            num_colors: 要提取的颜色数量
            
        Returns:
            List[str]: 十六进制颜色列表
        """
        self.extract_colors(image_path, num_colors=num_colors)
        return self.hex_colors
    
    @staticmethod
    def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
        """
        将RGB颜色转换为十六进制
        
        Args:
            rgb: (R, G, B) 元组
            
        Returns:
            str: 十六进制颜色字符串，如 "#FF5733"
        """
        return '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])
    
    @staticmethod
    def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        """
        将十六进制颜色转换为RGB
        
        Args:
            hex_color: 十六进制颜色字符串，如 "#FF5733" 或 "FF5733"
            
        Returns:
            Tuple[int, int, int]: (R, G, B) 元组
        """
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    @staticmethod
    def is_dark_color(rgb: Tuple[int, int, int]) -> bool:
        """
        判断颜色是否为深色（用于决定前景文字颜色）
        使用相对亮度公式
        
        Args:
            rgb: (R, G, B) 元组
            
        Returns:
            bool: True表示深色，False表示浅色
        """
        # 计算相对亮度 (根据 ITU-R BT.709 标准)
        r, g, b = rgb
        luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
        return luminance < 0.5
    
    def get_complementary_color(self, rgb: Tuple[int, int, int]) -> Tuple[int, int, int]:
        """
        获取补色
        
        Args:
            rgb: (R, G, B) 元组
            
        Returns:
            Tuple[int, int, int]: 补色的RGB值
        """
        return (255 - rgb[0], 255 - rgb[1], 255 - rgb[2])
    
    def get_color_info(self, image_path: str, num_colors: int = 5) -> dict:
        """
        获取图片颜色的完整信息
        
        Args:
            image_path: 图片路径
            num_colors: 要提取的颜色数量
            
        Returns:
            dict: 包含颜色信息的字典
        """
        colors = self.extract_colors(image_path, num_colors=num_colors)
        
        if not colors:
            return {}
        
        dominant = colors[0]
        
        return {
            'dominant_color': {
                'rgb': dominant,
                'hex': self.rgb_to_hex(dominant),
                'is_dark': self.is_dark_color(dominant)
            },
            'palette': [
                {
                    'rgb': color,
                    'hex': self.rgb_to_hex(color),
                    'is_dark': self.is_dark_color(color)
                }
                for color in colors
            ],
            'total_colors': len(colors)
        }