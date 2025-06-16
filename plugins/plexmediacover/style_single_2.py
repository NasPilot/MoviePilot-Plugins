from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import base64

def generate_single_cover(images, title, zh_font_path=None, en_font_path=None, 
                         zh_font_size_multiplier=1.0, en_font_size_multiplier=1.0,
                         blur_size=20, color_ratio=0.3, use_primary=True, use_blur=True):
    """
    生成单图样式2封面 - 简约风格，带渐变遮罩
    
    Args:
        images: 图片二进制数据列表
        title: 标题文本
        zh_font_path: 中文字体路径
        en_font_path: 英文字体路径
        zh_font_size_multiplier: 中文字体大小倍数
        en_font_size_multiplier: 英文字体大小倍数
        blur_size: 模糊大小
        color_ratio: 颜色比例
        use_primary: 是否使用主要图片
        use_blur: 是否使用模糊效果
    
    Returns:
        bytes: 生成的封面图片二进制数据
    """
    if not images:
        return None
        
    try:
        # 使用第一张图片作为背景
        background_image = Image.open(io.BytesIO(images[0]))
        
        # 设置目标尺寸
        target_width = 600
        target_height = 900
        
        # 调整背景图片尺寸
        background_image = background_image.resize((target_width, target_height), Image.Resampling.LANCZOS)
        
        # 转换为RGB模式
        if background_image.mode != 'RGB':
            background_image = background_image.convert('RGB')
        
        # 应用模糊效果（如果启用）
        if use_blur and blur_size > 0:
            background_image = background_image.filter(ImageFilter.GaussianBlur(radius=blur_size/4))
        
        # 创建渐变遮罩
        overlay = Image.new('RGBA', (target_width, target_height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # 创建从上到下的渐变遮罩
        for y in range(target_height):
            alpha = int(255 * (y / target_height) * color_ratio)
            overlay_draw.rectangle([(0, y), (target_width, y+1)], fill=(0, 0, 0, alpha))
        
        # 将遮罩应用到背景图片
        background_image = background_image.convert('RGBA')
        background_image = Image.alpha_composite(background_image, overlay)
        background_image = background_image.convert('RGB')
        
        # 创建绘图对象
        draw = ImageDraw.Draw(background_image)
        
        # 获取字体
        try:
            if zh_font_path:
                font = ImageFont.truetype(zh_font_path, int(48 * zh_font_size_multiplier))
            else:
                font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()
        
        # 计算文字位置（底部居中）
        text_bbox = draw.textbbox((0, 0), title, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        text_x = (target_width - text_width) // 2
        text_y = target_height - text_height - 60  # 距离底部60像素
        
        # 添加文字描边
        stroke_width = 2
        for dx in range(-stroke_width, stroke_width + 1):
            for dy in range(-stroke_width, stroke_width + 1):
                if dx != 0 or dy != 0:
                    draw.text((text_x + dx, text_y + dy), title, font=font, fill=(0, 0, 0, 180))
        
        # 添加主文字
        draw.text((text_x, text_y), title, font=font, fill=(255, 255, 255, 255))
        
        # 保存为字节数据
        output_buffer = io.BytesIO()
        background_image.save(output_buffer, format='JPEG', quality=95)
        return output_buffer.getvalue()
        
    except Exception as e:
        print(f"生成单图样式2封面时出错: {e}")
        return None