from typing import List
import io
import math
import random
from typing import List

from PIL import Image, ImageDraw, ImageFont, ImageFilter


def generate_single_cover(images: List[bytes], title: str = None) -> bytes:
    """
    生成单图封面
    :param images: 图片二进制数据列表
    :param title: 标题
    :return: 封面图片二进制数据
    """
    # 加载第一张图片
    if not images:
        raise ValueError("No images provided")
    
    img = Image.open(io.BytesIO(images[0]))
    
    # 转换为RGB模式
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # 设置目标尺寸
    target_size = (800, 1200)  # 宽高比2:3，适合海报
    
    # 裁剪为目标比例
    img_ratio = img.width / img.height
    target_ratio = target_size[0] / target_size[1]
    
    if img_ratio > target_ratio:
        # 图片太宽，裁剪左右
        new_width = int(img.height * target_ratio)
        left = (img.width - new_width) // 2
        img = img.crop((left, 0, left + new_width, img.height))
    else:
        # 图片太高，裁剪上下
        new_height = int(img.width / target_ratio)
        top = (img.height - new_height) // 2
        img = img.crop((0, top, img.width, top + new_height))
    
    # 调整到目标尺寸
    img = img.resize(target_size, Image.Resampling.LANCZOS)
    
    # 添加圆角效果
    def add_rounded_corners(image, radius=20):
        mask = Image.new('L', image.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle((0, 0) + image.size, radius=radius, fill=255)
        
        # 创建带圆角的图片
        rounded_img = Image.new('RGBA', image.size, (0, 0, 0, 0))
        rounded_img.paste(image, (0, 0))
        rounded_img.putalpha(mask)
        
        # 转换回RGB，添加白色背景
        final_img = Image.new('RGB', image.size, (255, 255, 255))
        final_img.paste(rounded_img, (0, 0), rounded_img)
        return final_img
    
    img = add_rounded_corners(img, 30)
    
    # 添加阴影效果
    shadow = Image.new('RGBA', (img.width + 20, img.height + 20), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle((10, 10, img.width + 10, img.height + 10), 
                                 radius=30, fill=(0, 0, 0, 100))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=5))
    
    # 创建最终画布
    canvas = Image.new('RGB', (img.width + 40, img.height + 100), (240, 240, 240))
    canvas.paste(shadow, (10, 10), shadow)
    canvas.paste(img, (20, 20))
    
    # 添加标题文字
    if title:
        draw = ImageDraw.Draw(canvas)
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 36)
        except:
            font = ImageFont.load_default()
        
        # 计算文字位置（底部居中）
        bbox = draw.textbbox((0, 0), title, font=font)
        text_width = bbox[2] - bbox[0]
        text_x = (canvas.width - text_width) // 2
        text_y = canvas.height - 60
        
        # 添加文字阴影
        draw.text((text_x + 2, text_y + 2), title, fill=(128, 128, 128), font=font)
        # 添加主文字
        draw.text((text_x, text_y), title, fill=(50, 50, 50), font=font)
    
    # 返回处理后的图片
    img_byte_arr = io.BytesIO()
    canvas.save(img_byte_arr, format='JPEG', quality=95)
    return img_byte_arr.getvalue()