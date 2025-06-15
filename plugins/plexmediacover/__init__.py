from typing import Optional, List, Dict, Any
import os
from PIL import Image, ImageDraw, ImageFont
import io
import requests
from datetime import datetime

from app import schemas
from app.core.config import settings
from app.log import logger
from app.chain.mediaserver import MediaServerChain
from app.plugins import _PluginBase


class PlexMediaCover(_PluginBase):
    """
    Plex媒体库封面插件
    """
    plugin_name = "Plex媒体库封面"
    plugin_desc = "自动更新Plex媒体库封面"
    plugin_icon = "https://raw.githubusercontent.com/NasPilot/MoviePilot-Plugins/main/icons/plexcover.png"
    plugin_version = "1.0.0"
    plugin_author = "NasPilot"
    plugin_config_prefix = "plexmediacover_"
    
    # 封面样式配置
    _style_config = {
        "single": {
            "width": 800,
            "height": 800,
            "bg_color": (0, 0, 0),
            "text_color": (255, 255, 255),
            "font_size": 40
        },
        "multi": {
            "width": 800,
            "height": 800,
            "bg_color": (0, 0, 0),
            "text_color": (255, 255, 255),
            "font_size": 40,
            "image_count": 4
        }
    }

    def __init__(self):
        super().__init__()
        self._mediaserver = None
        self._style = "single"  # 默认单图样式
        self._enabled = False

    def init_plugin(self, config: dict = None):
        """初始化插件"""
        # 加载配置
        if config:
            self._style = config.get("style", "single")
            self._enabled = config.get("enabled", False)
            
        if not self._enabled:
            return False
            
        try:
            self._mediaserver = MediaServerChain()
            # 检查是否有Plex服务器配置
            plex_servers = self._mediaserver.get_servers("plex")
            if not plex_servers:
                logger.error("未找到Plex服务器配置！")
                return False
            logger.info(f"Plex媒体库封面插件初始化成功，样式：{self._style}")
            return True
        except Exception as e:
            logger.error(f"Plex媒体库封面插件初始化失败：{str(e)}")
            return False

    def update_cover(self):
        """更新媒体库封面"""
        if not self._mediaserver or not self._enabled:
            logger.warning("插件未启用或媒体服务器未配置")
            return False
            
        try:
            # 获取Plex媒体库列表
            libraries = self._mediaserver.get_librarys("plex")
            if not libraries:
                logger.error("未获取到Plex媒体库列表")
                return False
                
            success_count = 0
            for library in libraries:
                logger.info(f"正在处理媒体库：{library.name}")
                
                # 获取媒体库图片
                if hasattr(library, 'image_list') and library.image_list:
                    image_list = library.image_list
                else:
                    logger.warning(f"媒体库 {library.name} 无可用图片")
                    continue
                    
                # 生成封面
                cover_image = self._generate_cover(image_list, library.name)
                if not cover_image:
                    continue
                    
                # 保存封面
                cover_path = os.path.join(self.get_data_path(), f"library_{library.id}_{library.name}.jpg")
                try:
                    os.makedirs(os.path.dirname(cover_path), exist_ok=True)
                    with open(cover_path, "wb") as f:
                        f.write(cover_image)
                    logger.info(f"成功保存媒体库 {library.name} 封面到 {cover_path}")
                    success_count += 1
                except Exception as e:
                    logger.error(f"保存媒体库 {library.name} 封面失败：{str(e)}")
                    
            logger.info(f"媒体库封面更新完成，成功处理 {success_count} 个媒体库")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"更新媒体库封面失败：{str(e)}")
            return False

    def _generate_cover(self, image_urls: list, title: str) -> bytes:
        """生成封面图片"""
        try:
            # 下载图片
            images = []
            max_images = 1 if self._style == "single" else 4
            
            for url in image_urls[:max_images]:
                try:
                    response = requests.get(url, timeout=10, headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    })
                    if response.status_code == 200:
                        images.append(response.content)
                        logger.debug(f"成功下载图片：{url}")
                    else:
                        logger.warning(f"下载图片失败，状态码：{response.status_code}，URL：{url}")
                except Exception as e:
                    logger.warning(f"下载图片异常：{str(e)}，URL：{url}")
                    continue
            
            if not images:
                logger.error(f"未能下载到任何图片，媒体库：{title}")
                return None
                
            # 根据样式生成封面
            if self._style == "single":
                return self._generate_single_cover(images[0], title)
            else:
                return self._generate_multi_cover(images, title)
                
        except Exception as e:
            logger.error(f"生成封面失败：{str(e)}")
            return None

    def _generate_single_cover(self, image: bytes, title: str) -> bytes:
        """生成单图封面"""
        try:
            # 打开原始图片
            img = Image.open(io.BytesIO(image))
            
            # 转换为RGB模式
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 调整大小，保持宽高比
            target_size = (self._style_config["single"]["width"], self._style_config["single"]["height"])
            img.thumbnail(target_size, Image.Resampling.LANCZOS)
            
            # 创建画布
            canvas = Image.new(
                "RGB", 
                target_size,
                self._style_config["single"]["bg_color"]
            )
            
            # 居中粘贴图片
            x = (target_size[0] - img.width) // 2
            y = (target_size[1] - img.height) // 2
            canvas.paste(img, (x, y))
            
            # 添加半透明遮罩和文字
            overlay = Image.new('RGBA', target_size, (0, 0, 0, 128))
            canvas = Image.alpha_composite(canvas.convert('RGBA'), overlay).convert('RGB')
            
            # 添加文字
            draw = ImageDraw.Draw(canvas)
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", self._style_config["single"]["font_size"])
            except:
                font = ImageFont.load_default()
                
            # 计算文字位置（底部居中）
            bbox = draw.textbbox((0, 0), title, font=font)
            text_width = bbox[2] - bbox[0]
            text_x = (target_size[0] - text_width) // 2
            text_y = target_size[1] - 80
            
            draw.text(
                (text_x, text_y), 
                title, 
                fill=self._style_config["single"]["text_color"], 
                font=font
            )
            
            # 保存为字节流
            img_byte_arr = io.BytesIO()
            canvas.save(img_byte_arr, format='JPEG', quality=95)
            return img_byte_arr.getvalue()
            
        except Exception as e:
            logger.error(f"生成单图封面失败：{str(e)}")
            return None

    def _generate_multi_cover(self, images: list, title: str) -> bytes:
        """生成多图封面"""
        try:
            target_size = (self._style_config["multi"]["width"], self._style_config["multi"]["height"])
            
            # 创建画布
            canvas = Image.new("RGB", target_size, self._style_config["multi"]["bg_color"])
            
            # 计算每张图片的位置和大小
            count = min(len(images), self._style_config["multi"]["image_count"])
            
            if count == 1:
                # 单图居中显示
                img = Image.open(io.BytesIO(images[0]))
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img.thumbnail(target_size, Image.Resampling.LANCZOS)
                x = (target_size[0] - img.width) // 2
                y = (target_size[1] - img.height) // 2
                canvas.paste(img, (x, y))
            elif count == 2:
                # 左右分布
                img_width = target_size[0] // 2
                for i in range(2):
                    img = Image.open(io.BytesIO(images[i]))
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    img = img.resize((img_width, target_size[1]), Image.Resampling.LANCZOS)
                    canvas.paste(img, (i * img_width, 0))
            else:
                # 四宫格布局
                img_width = target_size[0] // 2
                img_height = target_size[1] // 2
                
                positions = [
                    (0, 0),  # 左上
                    (img_width, 0),  # 右上
                    (0, img_height),  # 左下
                    (img_width, img_height)  # 右下
                ]
                
                # 添加图片
                for i in range(min(count, 4)):
                    img = Image.open(io.BytesIO(images[i]))
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    img = img.resize((img_width, img_height), Image.Resampling.LANCZOS)
                    canvas.paste(img, positions[i])
            
            # 添加半透明遮罩和文字
            overlay = Image.new('RGBA', target_size, (0, 0, 0, 100))
            canvas = Image.alpha_composite(canvas.convert('RGBA'), overlay).convert('RGB')
            
            # 添加文字
            draw = ImageDraw.Draw(canvas)
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", self._style_config["multi"]["font_size"])
            except:
                font = ImageFont.load_default()
            # 计算文字位置（底部居中）
            bbox = draw.textbbox((0, 0), title, font=font)
            text_width = bbox[2] - bbox[0]
            text_x = (target_size[0] - text_width) // 2
            text_y = target_size[1] - 80
            
            draw.text(
                (text_x, text_y), 
                title, 
                fill=self._style_config["multi"]["text_color"], 
                font=font
            )
            
            # 保存为字节流
            img_byte_arr = io.BytesIO()
            canvas.save(img_byte_arr, format='JPEG', quality=95)
            return img_byte_arr.getvalue()
            
        except Exception as e:
            logger.error(f"生成多图封面失败：{str(e)}")
            return None

    def stop(self):
        """停止插件"""
        self._enabled = False
        logger.info("Plex媒体库封面插件已停止")

    def get_state(self) -> bool:
        """获取插件状态"""
        return self._enabled and self._mediaserver is not None

    @staticmethod
    def get_command() -> list:
        """获取插件命令"""
        return []

    def get_api(self) -> list:
        """获取插件API"""
        return []

    def get_form(self) -> tuple:
        """获取插件配置表单"""
        return [
            {
                "component": "VForm",
                "content": [
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "enabled",
                                            "label": "启用插件",
                                            "hint": "开启后将自动生成Plex媒体库封面"
                                        }
                                    }
                                ]
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VSelect",
                                        "props": {
                                            "model": "style",
                                            "label": "封面样式",
                                            "items": [
                                                {"title": "单图样式", "value": "single"},
                                                {"title": "多图样式", "value": "multi"}
                                            ],
                                            "hint": "选择封面生成样式"
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12},
                                "content": [
                                    {
                                        "component": "VAlert",
                                        "props": {
                                            "type": "info",
                                            "variant": "tonal",
                                            "text": "插件将自动获取Plex媒体库的海报图片，生成自定义封面并保存到插件数据目录。单图样式使用一张图片，多图样式最多使用4张图片组合。"
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ], {
            "enabled": False,
            "style": "single"
        }

    def get_page(self) -> list:
        """获取插件页面"""
        return []

    def get_service(self) -> List[Dict[str, Any]]:
        """获取插件服务"""
        if not self._enabled:
            return []
            
        return [
            {
                "id": "PlexMediaCover.update_cover",
                "name": "更新Plex媒体库封面",
                "trigger": "cron",
                "func": self.update_cover,
                "kwargs": {"hour": 2, "minute": 0}  # 每天凌晨2点执行
            }
        ]

    def get_dashboard_meta(self) -> Optional[schemas.DashboardMeta]:
        """获取仪表盘元数据"""
        return None