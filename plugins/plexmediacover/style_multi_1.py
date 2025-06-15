from typing import List
import io
import math
import random
from typing import List

from PIL import Image, ImageDraw, ImageFont, ImageFilter


def generate_multi_cover(images: List[bytes], title: str = None) -> bytes:
    """
    生成多图封面
    :param images: 图片二进制数据列表
    :param title: 标题
    :return: 封面图片二进制数据
    """
    if not images:
        raise ValueError("No images provided")
    
    # 最多使用4张图片
    images = images[:4]
    count = len(images)
    
    # 创建画布
    canvas_width = 800
    canvas_height = 1000  # 增加高度以容纳标题
    canvas = Image.new('RGB', (canvas_width, canvas_height), (45, 45, 45))
    
    # 图片区域高度
    img_area_height = canvas_height - 120  # 为标题预留空间
    
    # 处理图片并添加到画布
    processed_images = []
    for img_data in images:
        img = Image.open(io.BytesIO(img_data))
        if img.mode != 'RGB':
            img = img.convert('RGB')
        processed_images.append(img)
    
    # 根据图片数量选择布局
    if count == 1:
        # 单图居中显示
        img = processed_images[0]
        # 保持宽高比，适应画布
        img.thumbnail((canvas_width - 40, img_area_height - 40), Image.Resampling.LANCZOS)
        x = (canvas_width - img.width) // 2
        y = (img_area_height - img.height) // 2 + 20
        canvas.paste(img, (x, y))
        
    elif count == 2:
        # 左右分布
        img_width = (canvas_width - 60) // 2  # 减去间距
        for i, img in enumerate(processed_images):
            # 调整图片尺寸
            img_ratio = img.width / img.height
            if img_ratio > 1:
                # 横图
                new_height = img_area_height - 40
                new_width = int(new_height * img_ratio)
                if new_width > img_width:
                    new_width = img_width
                    new_height = int(new_width / img_ratio)
            else:
                # 竖图
                new_width = img_width
                new_height = int(new_width / img_ratio)
                if new_height > img_area_height - 40:
                    new_height = img_area_height - 40
                    new_width = int(new_height * img_ratio)
            
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 计算位置
            x = 20 + i * (img_width + 20) + (img_width - new_width) // 2
            y = 20 + (img_area_height - 40 - new_height) // 2
            canvas.paste(img, (x, y))
            
    elif count == 3:
        # 上1下2布局
        # 上方大图
        top_img = processed_images[0]
        top_img.thumbnail((canvas_width - 40, (img_area_height - 60) // 2), Image.Resampling.LANCZOS)
        x = (canvas_width - top_img.width) // 2
        y = 20
        canvas.paste(top_img, (x, y))
        
        # 下方两张小图
        bottom_y = 20 + (img_area_height - 60) // 2 + 20
        bottom_height = img_area_height - bottom_y
        img_width = (canvas_width - 60) // 2
        
        for i, img in enumerate(processed_images[1:]):
            img.thumbnail((img_width, bottom_height - 20), Image.Resampling.LANCZOS)
            x = 20 + i * (img_width + 20) + (img_width - img.width) // 2
            y = bottom_y + (bottom_height - 20 - img.height) // 2
            canvas.paste(img, (x, y))
            
    else:  # count >= 4
        # 四宫格布局
        img_width = (canvas_width - 60) // 2
        img_height = (img_area_height - 60) // 2
        
        positions = [
            (20, 20),  # 左上
            (20 + img_width + 20, 20),  # 右上
            (20, 20 + img_height + 20),  # 左下
            (20 + img_width + 20, 20 + img_height + 20)  # 右下
        ]
        
        for i, img in enumerate(processed_images[:4]):
            # 裁剪为正方形
            size = min(img.width, img.height)
            left = (img.width - size) // 2
            top = (img.height - size) // 2
            img = img.crop((left, top, left + size, top + size))
            
            # 调整尺寸
            img = img.resize((img_width, img_height), Image.Resampling.LANCZOS)
            
            # 添加圆角效果
            mask = Image.new('L', img.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle((0, 0) + img.size, radius=15, fill=255)
            
            rounded_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
            rounded_img.paste(img, (0, 0))
            rounded_img.putalpha(mask)
            
            # 粘贴到画布
            canvas.paste(rounded_img, positions[i], rounded_img)
    
    # 添加渐变遮罩和标题
    if title:
        # 创建底部渐变遮罩
        gradient = Image.new('RGBA', (canvas_width, 120), (0, 0, 0, 0))
        for y in range(120):
            alpha = int(255 * (y / 120) * 0.7)
            for x in range(canvas_width):
                gradient.putpixel((x, y), (0, 0, 0, alpha))
        
        # 应用遮罩
        canvas_rgba = canvas.convert('RGBA')
        canvas_rgba = Image.alpha_composite(canvas_rgba, 
                                          Image.new('RGBA', canvas.size, (0, 0, 0, 0)))
        
        # 在底部添加遮罩
        mask_y = canvas_height - 120
        canvas_rgba.paste(gradient, (0, mask_y), gradient)
        canvas = canvas_rgba.convert('RGB')
        
        # 添加标题文字
        draw = ImageDraw.Draw(canvas)
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 42)
        except:
            font = ImageFont.load_default()
        
        # 计算文字位置（底部居中）
        bbox = draw.textbbox((0, 0), title, font=font)
        text_width = bbox[2] - bbox[0]
        text_x = (canvas_width - text_width) // 2
        text_y = canvas_height - 70
        
        # 添加文字描边效果
        for dx in [-2, -1, 0, 1, 2]:
            for dy in [-2, -1, 0, 1, 2]:
                if dx != 0 or dy != 0:
                    draw.text((text_x + dx, text_y + dy), title, fill=(0, 0, 0), font=font)
        
        # 添加主文字
        draw.text((text_x, text_y), title, fill=(255, 255, 255), font=font)
    
    # 返回处理后的图片
    img_byte_arr = io.BytesIO()
    canvas.save(img_byte_arr, format='JPEG', quality=95)
    return img_byte_arr.getvalue()