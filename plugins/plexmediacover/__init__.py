from typing import Optional, List, Dict, Any
import datetime
import hashlib
import os
import re
import threading
import time
import shutil
import random
from pathlib import Path
from urllib.parse import urlparse
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict
import base64
from io import BytesIO

import pytz
import yaml

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app import schemas
from app.chain.mediaserver import MediaServerChain
from app.core.config import settings
from app.core.event import eventmanager, Event
from app.helper.mediaserver import MediaServerHelper
from app.log import logger
from app.plugins import _PluginBase
from app.schemas import MediaInfo
from app.schemas.types import EventType
from app.schemas import ServiceInfo
from app.utils.http import RequestUtils
from app.utils.url import UrlUtils

# 导入样式模块
try:
    from app.plugins.plexmediacover.style_single_1 import generate_single_cover
    from app.plugins.plexmediacover.style_multi_1 import generate_multi_cover
except ImportError:
    # 如果导入失败，使用本地导入
    from .style_single_1 import generate_single_cover
    from .style_multi_1 import generate_multi_cover


class PlexMediaCover(_PluginBase):
    """
    Plex媒体库封面插件 - 基于mediacovergenerator优化版本
    """
    # 插件名称
    plugin_name = "Plex媒体库封面"
    # 插件描述
    plugin_desc = "自动生成Plex媒体库封面，支持多种样式和自定义配置"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/NasPilot/MoviePilot-Plugins/main/icons/plexcover.png"
    # 插件版本
    plugin_version = "2.0.0"
    # 插件作者
    plugin_author = "NasPilot"
    # 作者主页
    author_url = "https://github.com/NasPilot/MoviePilot-Plugins"
    # 插件配置项ID前缀
    plugin_config_prefix = "plexmediacover_"
    # 加载顺序
    plugin_order = 2
    # 可使用的用户级别
    auth_level = 1

    # 退出事件
    _event = threading.Event()

    # 私有属性
    _scheduler = None
    mschain = None
    mediaserver_helper = None
    _enabled = False
    _onlyonce = False
    _cron = None
    _delay = 60
    _servers = None
    _selected_servers = []
    _all_libraries = []
    _exclude_libraries = []
    _sort_by = 'Random'
    _covers_output = ''
    _covers_input = ''
    _zh_font_url = ''
    _en_font_url = ''
    _zh_font_path = ''
    _en_font_path = ''
    _zh_font_path_local = ''
    _en_font_path_local = ''
    _zh_font_path_multi_1_local = ''
    _en_font_path_multi_1_local = ''
    _zh_font_url_multi_1 = ''
    _en_font_url_multi_1 = ''
    _zh_font_path_multi_1 = ''
    _en_font_path_multi_1 = ''
    _multi_1_use_main_font = False
    _title_config = ''
    _cover_style = 'single_1'
    _font_path = ''
    _covers_path = ''
    _tab = 'style-tab'
    _multi_1_blur = False
    _zh_font_size = 1
    _en_font_size = 1
    _zh_font_size_multi_1 = 1
    _en_font_size_multi_1 = 1
    _blur_size = 50
    _blur_size_multi_1 = 50
    _color_ratio = 0.8
    _color_ratio_multi_1 = 0.8
    _single_use_primary = False
    _multi_1_use_primary = True

    def __init__(self):
        super().__init__()

    def init_plugin(self, config: dict = None):
        """初始化插件"""
        self.mschain = MediaServerChain()
        self.mediaserver_helper = MediaServerHelper()   
        data_path = self.get_data_path()
        (data_path / 'fonts').mkdir(parents=True, exist_ok=True)
        (data_path / 'covers').mkdir(parents=True, exist_ok=True)
        self._covers_path = data_path / 'covers'
        self._font_path = data_path / 'fonts'
        
        if config:
            self._enabled = config.get("enabled")
            self._onlyonce = config.get("onlyonce")
            self._cron = config.get("cron")
            self._delay = config.get("delay")
            self._selected_servers = config.get("selected_servers")
            self._exclude_libraries = config.get("exclude_libraries")
            self._sort_by = config.get("sort_by")
            self._covers_output = config.get("covers_output")
            self._covers_input = config.get("covers_input")
            self._title_config = config.get("title_config")
            self._zh_font_url = config.get("zh_font_url")
            self._en_font_url = config.get("en_font_url")
            self._zh_font_path = config.get("zh_font_path")
            self._en_font_path = config.get("en_font_path")
            self._cover_style = config.get("cover_style")
            self._tab = config.get("tab")
            self._zh_font_url_multi_1 = config.get("zh_font_url_multi_1")
            self._en_font_url_multi_1 = config.get("en_font_url_multi_1")
            self._zh_font_path_multi_1 = config.get("zh_font_path_multi_1")
            self._en_font_path_multi_1 = config.get("en_font_path_multi_1")
            self._multi_1_blur = config.get("multi_1_blur")
            self._multi_1_use_main_font = config.get("multi_1_use_main_font")
            self._zh_font_path_local = config.get("zh_font_path_local")
            self._en_font_path_local = config.get("en_font_path_local")
            self._zh_font_path_multi_1_local = config.get("zh_font_path_multi_1_local")
            self._en_font_path_multi_1_local = config.get("en_font_path_multi_1_local")
            self._zh_font_size = config.get("zh_font_size")
            self._en_font_size = config.get("en_font_size")
            self._zh_font_size_multi_1 = config.get("zh_font_size_multi_1")
            self._en_font_size_multi_1 = config.get("en_font_size_multi_1")
            self._blur_size = config.get("blur_size")
            self._blur_size_multi_1 = config.get("blur_size_multi_1")
            self._color_ratio = config.get("color_ratio")
            self._color_ratio_multi_1 = config.get("color_ratio_multi_1")
            self._single_use_primary = config.get("single_use_primary")
            self._multi_1_use_primary = config.get("multi_1_use_primary")

        if self._selected_servers:
            self._servers = self.mediaserver_helper.get_services(
                name_filters=self._selected_servers
            )
            self._all_libraries = []
            for server, service in self._servers.items():
                if not service.instance.is_inactive():
                    self._all_libraries.extend(self.__get_all_libraries(server, service))
                else:
                    logger.info(f"媒体服务器 {server} 未连接")
        else:
            logger.info("未选择媒体服务器")
        
        # 停止现有任务
        self.stop_service()

        # 启动服务
        if self._onlyonce:
            self._scheduler = BackgroundScheduler(timezone=settings.TZ)
            self._scheduler.add_job(func=self.__update_all_libraries, trigger='date',
                                    run_date=datetime.datetime.now(
                                        tz=pytz.timezone(settings.TZ)) + datetime.timedelta(seconds=3)
                                    )
            logger.info(f"Plex媒体库封面更新服务启动，立即运行一次")
            # 关闭一次性开关
            self._onlyonce = False
            # 保存配置
            self.__update_config()
            # 启动服务
            if self._scheduler.get_jobs():
                self._scheduler.print_jobs()
                self._scheduler.start()

    def __update_config(self):
        """更新配置"""
        self.update_config({
            "enabled": self._enabled,
            "onlyonce": self._onlyonce,
            "cron": self._cron,
            "delay": self._delay,
            "selected_servers": self._selected_servers,
            "exclude_libraries": self._exclude_libraries,
            "sort_by": self._sort_by,
            "covers_output": self._covers_output,
            "covers_input": self._covers_input,
            "title_config": self._title_config,
            "zh_font_url": self._zh_font_url,
            "en_font_url": self._en_font_url,
            "zh_font_path": self._zh_font_path,
            "en_font_path": self._en_font_path,
            "cover_style": self._cover_style,
            "tab": self._tab,
            "zh_font_url_multi_1": self._zh_font_url_multi_1,
            "en_font_url_multi_1": self._en_font_url_multi_1,
            "zh_font_path_multi_1": self._zh_font_path_multi_1,
            "en_font_path_multi_1": self._en_font_path_multi_1,
            "multi_1_blur": self._multi_1_blur,
            "multi_1_use_main_font": self._multi_1_use_main_font,
            "zh_font_path_local": self._zh_font_path_local,
            "en_font_path_local": self._en_font_path_local,
            "zh_font_path_multi_1_local": self._zh_font_path_multi_1_local,
            "en_font_path_multi_1_local": self._en_font_path_multi_1_local,
            "zh_font_size": self._zh_font_size,
            "en_font_size": self._en_font_size,
            "zh_font_size_multi_1": self._zh_font_size_multi_1,
            "en_font_size_multi_1": self._en_font_size_multi_1,
            "blur_size": self._blur_size,
            "blur_size_multi_1": self._blur_size_multi_1,
            "color_ratio": self._color_ratio,
            "color_ratio_multi_1": self._color_ratio_multi_1,
            "single_use_primary": self._single_use_primary,
            "multi_1_use_primary": self._multi_1_use_primary
        })

    def __get_all_libraries(self, server_name: str, service: ServiceInfo) -> List[Dict[str, Any]]:
        """获取所有媒体库"""
        libraries = []
        try:
            server_libraries = service.instance.get_librarys()
            for library in server_libraries:
                libraries.append({
                    'server_name': server_name,
                    'library_id': library.id,
                    'library_name': library.name,
                    'library_type': library.type,
                    'service': service
                })
        except Exception as e:
            logger.error(f"获取媒体服务器 {server_name} 媒体库失败：{str(e)}")
        return libraries

    def __update_all_libraries(self):
        """更新所有媒体库封面"""
        if not self._enabled:
            return
            
        logger.info("开始更新Plex媒体库封面...")
        
        # 获取字体
        self.__get_fonts()
        
        success_count = 0
        for server, service in self._servers.items():
            if service.instance.is_inactive():
                logger.warning(f"媒体服务器 {server} 未连接")
                continue
                
            for library_info in self._all_libraries:
                if library_info['server_name'] != server:
                    continue
                    
                library_name = library_info['library_name']
                
                # 检查是否忽略该媒体库
                if self._exclude_libraries and library_name in self._exclude_libraries:
                    logger.info(f"忽略媒体库：{library_name}")
                    continue
                    
                try:
                    if self.__update_library(library_info):
                        success_count += 1
                        logger.info(f"成功更新媒体库 {library_name} 封面")
                    else:
                        logger.warning(f"更新媒体库 {library_name} 封面失败")
                except Exception as e:
                    logger.error(f"更新媒体库 {library_name} 封面异常：{str(e)}")
                    
        logger.info(f"Plex媒体库封面更新完成，成功处理 {success_count} 个媒体库")

    def __update_library(self, library_info: Dict[str, Any]) -> bool:
        """更新单个媒体库封面"""
        library_name = library_info['library_name']
        
        # 检查自定义图像路径
        custom_image_path = self.__check_custom_image(library_name)
        
        # 获取标题配置
        title_config = self.__get_title_from_yaml(library_name)
        
        if custom_image_path:
            # 从自定义路径生成封面
            return self.__generate_image_from_path(custom_image_path, title_config, library_info)
        else:
            # 从服务器生成封面
            return self.__generate_from_server(library_info, title_config)
    
    def __check_custom_image(self, library_name: str) -> Optional[str]:
        """检查自定义封面输入目录"""
        if not self._covers_input:
            return None
            
        custom_path = Path(self._covers_input) / library_name
        if custom_path.exists() and custom_path.is_dir():
            # 查找支持的图片文件
            for ext in ['jpg', 'jpeg', 'png', 'webp']:
                for img_file in custom_path.glob(f'*.{ext}'):
                    return str(custom_path)
        return None
    
    def __get_title_from_yaml(self, library_name: str) -> Dict[str, str]:
        """从YAML配置获取标题"""
        if not self._title_config:
            return {'zh': library_name, 'en': library_name}
            
        try:
            title_mapping = yaml.safe_load(self._title_config)
            if isinstance(title_mapping, dict) and library_name in title_mapping:
                config = title_mapping[library_name]
                if isinstance(config, dict):
                    return {
                        'zh': config.get('zh', library_name),
                        'en': config.get('en', library_name)
                    }
                else:
                    return {'zh': str(config), 'en': str(config)}
        except Exception as e:
            logger.warning(f"解析标题配置失败：{str(e)}")
            
        return {'zh': library_name, 'en': library_name}
    
    def __generate_image_from_path(self, image_path: str, title_config: Dict[str, str], library_info: Dict[str, Any]) -> bool:
        """从自定义图片路径生成封面"""
        try:
            if self._cover_style == 'single_1':
                result = generate_single_cover(
                    image_path=image_path,
                    zh_title=title_config['zh'],
                    en_title=title_config['en'],
                    zh_font_path=self._zh_font_path_local,
                    en_font_path=self._en_font_path_local,
                    zh_font_size=self._zh_font_size,
                    en_font_size=self._en_font_size,
                    blur_size=self._blur_size,
                    color_ratio=self._color_ratio,
                    use_primary=self._single_use_primary
                )
            elif self._cover_style == 'multi_1':
                result = generate_multi_cover(
                    image_path=image_path,
                    zh_title=title_config['zh'],
                    en_title=title_config['en'],
                    zh_font_path=self._zh_font_path_multi_1_local,
                    en_font_path=self._en_font_path_multi_1_local,
                    zh_font_size=self._zh_font_size_multi_1,
                    en_font_size=self._en_font_size_multi_1,
                    blur_size=self._blur_size_multi_1,
                    color_ratio=self._color_ratio_multi_1,
                    use_primary=self._multi_1_use_primary,
                    use_blur=self._multi_1_blur
                )
            else:
                logger.error(f"不支持的封面样式：{self._cover_style}")
                return False
                
            if result:
                return self.__set_library_image(library_info, result)
            else:
                logger.error(f"生成封面失败，媒体库：{library_info['library_name']}")
                return False
                
        except Exception as e:
            logger.error(f"从路径生成封面失败：{str(e)}")
            return False

    def __generate_from_server(self, library_info: Dict[str, Any], title_config: Dict[str, str]) -> bool:
        """从媒体服务器获取媒体项并生成封面"""
        try:
            service = library_info['service']
            library_id = library_info['library_id']
            library_name = library_info['library_name']
            
            # 根据封面样式确定需要的媒体项数量
            if self._cover_style == 'single_1':
                required_count = 1
            elif self._cover_style == 'multi_1':
                required_count = 9
            else:
                required_count = 4
                
            # 获取媒体项
            media_items = self.__get_media_items(service, library_id, required_count)
            if not media_items:
                logger.warning(f"媒体库 {library_name} 未获取到媒体项")
                return False
                
            # 下载图片到临时目录
            temp_dir = self._covers_path / 'temp' / library_name
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # 清理旧的临时文件
            for old_file in temp_dir.glob('*'):
                old_file.unlink()
                
            downloaded_images = []
            for i, item in enumerate(media_items[:required_count]):
                image_url = self.__get_image_url_from_media_item(item, service)
                if image_url:
                    image_path = temp_dir / f"{i+1}.jpg"
                    if self.__download_image(image_url, str(image_path)):
                        downloaded_images.append(str(image_path))
                        
            if not downloaded_images:
                logger.warning(f"媒体库 {library_name} 未下载到任何图片")
                return False
                
            # 生成封面
            if self._cover_style == 'single_1':
                result = generate_single_cover(
                    image_path=str(temp_dir),
                    zh_title=title_config['zh'],
                    en_title=title_config['en'],
                    zh_font_path=self._zh_font_path_local,
                    en_font_path=self._en_font_path_local,
                    zh_font_size=self._zh_font_size,
                    en_font_size=self._en_font_size,
                    blur_size=self._blur_size,
                    color_ratio=self._color_ratio,
                    use_primary=self._single_use_primary
                )
            elif self._cover_style == 'multi_1':
                result = generate_multi_cover(
                    image_path=str(temp_dir),
                    zh_title=title_config['zh'],
                    en_title=title_config['en'],
                    zh_font_path=self._zh_font_path_multi_1_local,
                    en_font_path=self._en_font_path_multi_1_local,
                    zh_font_size=self._zh_font_size_multi_1,
                    en_font_size=self._en_font_size_multi_1,
                    blur_size=self._blur_size_multi_1,
                    color_ratio=self._color_ratio_multi_1,
                    use_primary=self._multi_1_use_primary,
                    use_blur=self._multi_1_blur
                )
            else:
                logger.error(f"不支持的封面样式：{self._cover_style}")
                return False
                
            if result:
                return self.__set_library_image(library_info, result)
            else:
                logger.error(f"生成封面失败，媒体库：{library_name}")
                return False
                
        except Exception as e:
            logger.error(f"从服务器生成封面失败：{str(e)}")
            return False
    
    def __get_media_items(self, service: ServiceInfo, library_id: str, count: int) -> List[Any]:
        """获取媒体项"""
        try:
            # 获取媒体项列表
            items = service.instance.get_items(library_id)
            if not items:
                return []
                
            # 根据排序方式处理
            if self._sort_by == 'Random':
                random.shuffle(items)
            elif self._sort_by == 'DateAdded':
                items.sort(key=lambda x: getattr(x, 'date_added', ''), reverse=True)
            elif self._sort_by == 'PremiereDate':
                items.sort(key=lambda x: getattr(x, 'premiere_date', ''), reverse=True)
                
            return items[:count]
            
        except Exception as e:
            logger.error(f"获取媒体项失败：{str(e)}")
            return []
    
    def __get_image_url_from_media_item(self, item: Any, service: ServiceInfo) -> Optional[str]:
        """从媒体项获取图片URL"""
        try:
            # 根据封面样式选择图片类型
            if self._cover_style == 'single_1' and self._single_use_primary:
                image_type = 'Primary'
            elif self._cover_style == 'multi_1' and self._multi_1_use_primary:
                image_type = 'Primary'
            else:
                image_type = 'Backdrop'
                
            # 获取图片URL
            if hasattr(item, 'get_image_url'):
                return item.get_image_url(image_type)
            elif hasattr(service.instance, 'get_image_url'):
                return service.instance.get_image_url(item.id, image_type)
            else:
                logger.warning(f"无法获取媒体项 {item.id} 的图片URL")
                return None
                
        except Exception as e:
            logger.error(f"获取图片URL失败：{str(e)}")
            return None
    
    def __download_image(self, url: str, save_path: str, max_retries: int = 3) -> bool:
        """下载图片"""
        for attempt in range(max_retries):
            try:
                response = RequestUtils().get_res(url, timeout=30)
                if response and response.status_code == 200:
                    with open(save_path, 'wb') as f:
                        f.write(response.content)
                    return True
                else:
                    logger.warning(f"下载图片失败，状态码：{response.status_code if response else 'None'}，URL：{url}")
            except Exception as e:
                logger.warning(f"下载图片异常（尝试 {attempt + 1}/{max_retries}）：{str(e)}，URL：{url}")
                if attempt < max_retries - 1:
                    time.sleep(1)
        return False
    
    def __set_library_image(self, library_info: Dict[str, Any], image_data: str) -> bool:
        """设置媒体库封面"""
        try:
            service = library_info['service']
            library_id = library_info['library_id']
            library_name = library_info['library_name']
            
            # 解码base64图片数据
            image_bytes = base64.b64decode(image_data)
            
            # 保存到输出目录
            if self._covers_output:
                output_path = Path(self._covers_output) / f"{library_name}.jpg"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'wb') as f:
                    f.write(image_bytes)
                logger.info(f"封面已保存到：{output_path}")
            
            # 设置媒体库封面（如果服务器支持）
            if hasattr(service.instance, 'set_library_image'):
                return service.instance.set_library_image(library_id, image_bytes)
            else:
                logger.info(f"媒体服务器不支持直接设置媒体库封面，已保存到本地")
                return True
                
        except Exception as e:
            logger.error(f"设置媒体库封面失败：{str(e)}")
            return False

    def __get_fonts(self):
        """获取字体文件"""
        try:
            # 默认字体URL
            default_zh_font_url = "https://github.com/adobe-fonts/source-han-sans/releases/download/2.004R/SourceHanSansCN.zip"
            default_en_font_url = "https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Regular.ttf"
            
            # 获取主字体
            self._zh_font_path_local = self.__download_font(
                self._zh_font_url or default_zh_font_url,
                "zh_font"
            )
            self._en_font_path_local = self.__download_font(
                self._en_font_url or default_en_font_url,
                "en_font"
            )
            
            # 获取多图样式字体
            if self._multi_1_use_main_font:
                self._zh_font_path_multi_1_local = self._zh_font_path_local
                self._en_font_path_multi_1_local = self._en_font_path_local
            else:
                self._zh_font_path_multi_1_local = self.__download_font(
                    self._zh_font_url_multi_1 or default_zh_font_url,
                    "zh_font_multi_1"
                )
                self._en_font_path_multi_1_local = self.__download_font(
                    self._en_font_url_multi_1 or default_en_font_url,
                    "en_font_multi_1"
                )
                
        except Exception as e:
            logger.error(f"获取字体失败：{str(e)}")
    
    def __download_font(self, font_url: str, font_name: str) -> Optional[str]:
        """下载字体文件"""
        try:
            # 检查本地路径配置
            local_path_key = f"_{font_name}_path_local"
            if hasattr(self, local_path_key):
                local_path = getattr(self, local_path_key)
                if local_path and Path(local_path).exists():
                    logger.info(f"使用本地字体文件：{local_path}")
                    return local_path
            
            # 生成字体文件名
            font_hash = hashlib.md5(font_url.encode()).hexdigest()[:8]
            font_ext = self.__get_file_extension_from_url(font_url) or '.ttf'
            font_filename = f"{font_name}_{font_hash}{font_ext}"
            font_path = self._font_path / font_filename
            
            # 检查是否已存在
            if font_path.exists() and self.__validate_font_file(str(font_path)):
                logger.info(f"字体文件已存在：{font_path}")
                return str(font_path)
            
            # 下载字体
            logger.info(f"开始下载字体：{font_url}")
            response = RequestUtils().get_res(font_url, timeout=60)
            if response and response.status_code == 200:
                # 保存到临时文件
                temp_path = font_path.with_suffix('.tmp')
                with open(temp_path, 'wb') as f:
                    f.write(response.content)
                
                # 验证字体文件
                if self.__validate_font_file(str(temp_path)):
                    temp_path.rename(font_path)
                    logger.info(f"字体下载成功：{font_path}")
                    return str(font_path)
                else:
                    temp_path.unlink()
                    logger.error(f"字体文件验证失败：{font_url}")
            else:
                logger.error(f"字体下载失败，状态码：{response.status_code if response else 'None'}")
                
        except Exception as e:
            logger.error(f"下载字体异常：{str(e)}")
            
        return None
    
    def __get_file_extension_from_url(self, url: str) -> Optional[str]:
        """从URL获取文件扩展名"""
        try:
            parsed = urlparse(url)
            path = parsed.path
            if '.' in path:
                return '.' + path.split('.')[-1].lower()
        except:
            pass
        return None
    
    def __validate_font_file(self, font_path: str) -> bool:
        """验证字体文件"""
        try:
            if not os.path.exists(font_path):
                return False
                
            # 检查文件大小
            if os.path.getsize(font_path) < 1024:  # 小于1KB
                return False
                
            # 检查文件头
            with open(font_path, 'rb') as f:
                header = f.read(4)
                
            # 支持的字体格式
            font_signatures = [
                b'\x00\x01\x00\x00',  # TTF
                b'OTTO',              # OTF
                b'wOFF',              # WOFF
                b'wOF2',              # WOFF2
                b'<?xml',             # SVG
                b'STARTFONT'          # BDF
            ]
            
            return any(header.startswith(sig) for sig in font_signatures)
            
        except Exception as e:
            logger.error(f"验证字体文件失败：{str(e)}")
            return False

    def stop_service(self):
        """停止定时任务"""
        try:
            if self._scheduler:
                self._scheduler.remove_all_jobs()
                if self._scheduler.running:
                    self._scheduler.shutdown()
                self._scheduler = None
                self._event.clear()
        except Exception as e:
            logger.error(f"停止定时任务失败：{str(e)}")

    def get_state(self) -> bool:
        """获取插件状态"""
        return self._enabled and bool(self._servers)

    @staticmethod
    def get_command() -> list:
        """获取插件命令"""
        return []

    def get_api(self) -> list:
        """获取插件API"""
        return []

    def get_form(self) -> tuple:
        """获取插件配置表单"""
        # 获取可用的媒体服务器
        server_options = []
        try:
            servers = self.mediaserver_helper.get_services()
            for server_name in servers.keys():
                server_options.append({"title": server_name, "value": server_name})
        except:
            pass
            
        return [
            {
                "component": "VForm",
                "content": [
                    {
                        "component": "VTabs",
                        "props": {
                            "model": "tab",
                            "height": 72,
                            "fixed-tabs": True
                        },
                        "content": [
                            {
                                "component": "VTab",
                                "props": {"value": "basic-tab"},
                                "text": "基础设置"
                            },
                            {
                                "component": "VTab",
                                "props": {"value": "style-tab"},
                                "text": "样式配置"
                            },
                            {
                                "component": "VTab",
                                "props": {"value": "font-tab"},
                                "text": "字体配置"
                            },
                            {
                                "component": "VTab",
                                "props": {"value": "path-tab"},
                                "text": "路径配置"
                            }
                        ]
                    },
                    {
                        "component": "VWindow",
                        "props": {"model": "tab"},
                        "content": [
                            {
                                "component": "VWindowItem",
                                "props": {"value": "basic-tab"},
                                "content": [
                                    {
                                        "component": "VRow",
                                        "content": [
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "md": 4},
                                                "content": [
                                                    {
                                                        "component": "VSwitch",
                                                        "props": {
                                                            "model": "enabled",
                                                            "label": "启用插件"
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "md": 4},
                                                "content": [
                                                    {
                                                        "component": "VSwitch",
                                                        "props": {
                                                            "model": "onlyonce",
                                                            "label": "立即运行一次"
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "md": 4},
                                                "content": [
                                                    {
                                                        "component": "VTextField",
                                                        "props": {
                                                            "model": "delay",
                                                            "label": "入库延迟（秒）",
                                                            "type": "number",
                                                            "placeholder": "60"
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
                                                "props": {"cols": 12, "md": 6},
                                                "content": [
                                                    {
                                                        "component": "VSelect",
                                                        "props": {
                                                            "model": "selected_servers",
                                                            "label": "选择媒体服务器",
                                                            "items": server_options,
                                                            "multiple": True,
                                                            "chips": True,
                                                            "hint": "选择要处理的媒体服务器"
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
                                                            "model": "sort_by",
                                                            "label": "封面来源排序",
                                                            "items": [
                                                                {"title": "随机", "value": "Random"},
                                                                {"title": "添加日期", "value": "DateAdded"},
                                                                {"title": "首播日期", "value": "PremiereDate"}
                                                            ]
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
                                                "props": {"cols": 12, "md": 6},
                                                "content": [
                                                    {
                                                        "component": "VTextField",
                                                        "props": {
                                                            "model": "cron",
                                                            "label": "定时更新",
                                                            "placeholder": "0 2 * * *",
                                                            "hint": "使用Cron表达式设置定时任务"
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "md": 6},
                                                "content": [
                                                    {
                                                        "component": "VTextField",
                                                        "props": {
                                                            "model": "exclude_libraries",
                                                            "label": "忽略媒体库",
                                                            "placeholder": "媒体库1,媒体库2",
                                                            "hint": "用逗号分隔多个媒体库名称"
                                                        }
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                ]
                            },
                            {
                                "component": "VWindowItem",
                                "props": {"value": "style-tab"},
                                "content": [
                                    {
                                        "component": "VRow",
                                        "content": [
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12},
                                                "content": [
                                                    {
                                                        "component": "VSelect",
                                                        "props": {
                                                            "model": "cover_style",
                                                            "label": "封面样式",
                                                            "items": [
                                                                {"title": "单图样式1", "value": "single_1"},
                                                                {"title": "多图样式1", "value": "multi_1"}
                                                            ]
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
                                                "props": {"cols": 12, "md": 6},
                                                "content": [
                                                    {
                                                        "component": "VSwitch",
                                                        "props": {
                                                            "model": "single_use_primary",
                                                            "label": "单图样式使用主要图片"
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "md": 6},
                                                "content": [
                                                    {
                                                        "component": "VSwitch",
                                                        "props": {
                                                            "model": "multi_1_use_primary",
                                                            "label": "多图样式使用主要图片"
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
                                                "props": {"cols": 12, "md": 6},
                                                "content": [
                                                    {
                                                        "component": "VSlider",
                                                        "props": {
                                                            "model": "blur_size",
                                                            "label": "单图模糊大小",
                                                            "min": 0,
                                                            "max": 100,
                                                            "step": 5
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "md": 6},
                                                "content": [
                                                    {
                                                        "component": "VSlider",
                                                        "props": {
                                                            "model": "color_ratio",
                                                            "label": "单图颜色比例",
                                                            "min": 0,
                                                            "max": 1,
                                                            "step": 0.1
                                                        }
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                 ]
                             },
                             {
                                 "component": "VWindowItem",
                                 "props": {"value": "font-tab"},
                                 "content": [
                                     {
                                         "component": "VRow",
                                         "content": [
                                             {
                                                 "component": "VCol",
                                                 "props": {"cols": 12, "md": 6},
                                                 "content": [
                                                     {
                                                         "component": "VTextField",
                                                         "props": {
                                                             "model": "zh_font_url",
                                                             "label": "中文字体URL",
                                                             "placeholder": "https://example.com/font.ttf",
                                                             "hint": "留空使用默认字体"
                                                         }
                                                     }
                                                 ]
                                             },
                                             {
                                                 "component": "VCol",
                                                 "props": {"cols": 12, "md": 6},
                                                 "content": [
                                                     {
                                                         "component": "VTextField",
                                                         "props": {
                                                             "model": "en_font_url",
                                                             "label": "英文字体URL",
                                                             "placeholder": "https://example.com/font.ttf",
                                                             "hint": "留空使用默认字体"
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
                                                 "props": {"cols": 12, "md": 6},
                                                 "content": [
                                                     {
                                                         "component": "VSlider",
                                                         "props": {
                                                             "model": "zh_font_size",
                                                             "label": "中文字体大小倍数",
                                                             "min": 0.5,
                                                             "max": 2.0,
                                                             "step": 0.1
                                                         }
                                                     }
                                                 ]
                                             },
                                             {
                                                 "component": "VCol",
                                                 "props": {"cols": 12, "md": 6},
                                                 "content": [
                                                     {
                                                         "component": "VSlider",
                                                         "props": {
                                                             "model": "en_font_size",
                                                             "label": "英文字体大小倍数",
                                                             "min": 0.5,
                                                             "max": 2.0,
                                                             "step": 0.1
                                                         }
                                                     }
                                                 ]
                                             }
                                         ]
                                     }
                                 ]
                             },
                             {
                                 "component": "VWindowItem",
                                 "props": {"value": "path-tab"},
                                 "content": [
                                     {
                                         "component": "VRow",
                                         "content": [
                                             {
                                                 "component": "VCol",
                                                 "props": {"cols": 12},
                                                 "content": [
                                                     {
                                                         "component": "VTextField",
                                                         "props": {
                                                             "model": "covers_output",
                                                             "label": "封面输出目录",
                                                             "placeholder": "/path/to/covers/output",
                                                             "hint": "生成的封面保存路径，留空使用插件数据目录"
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
                                                         "component": "VTextField",
                                                         "props": {
                                                             "model": "covers_input",
                                                             "label": "自定义封面输入目录",
                                                             "placeholder": "/path/to/custom/covers",
                                                             "hint": "自定义封面图片目录，留空则从服务器获取"
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
                                                         "component": "VTextarea",
                                                         "props": {
                                                             "model": "title_config",
                                                             "label": "标题配置",
                                                             "placeholder": "library_name: 自定义标题",
                                                             "hint": "YAML格式配置媒体库标题，每行一个配置",
                                                             "rows": 5
                                                         }
                                                     }
                                                 ]
                                             }
                                         ]
                                     }
                                 ]
                             }
                        ]
                    }
                ]
            }
        ], {
            "enabled": False,
            "onlyonce": False,
            "cron": "0 2 * * *",
            "delay": 60,
            "selected_servers": [],
            "exclude_libraries": [],
            "sort_by": "Random",
            "covers_output": "",
            "covers_input": "",
            "title_config": "",
            "zh_font_url": "",
            "en_font_url": "",
            "cover_style": "single_1",
            "tab": "basic-tab",
            "single_use_primary": False,
            "multi_1_use_primary": True,
            "blur_size": 50,
            "color_ratio": 0.8,
            "zh_font_size": 1,
            "en_font_size": 1
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

    def __update_single_image(self, style: str, image_paths: List[str], title: str, font_path: str, font_size: int, blur_size: int = 50, color_ratio: float = 0.8) -> Optional[Image.Image]:
        """更新单图封面"""
        if not image_paths:
            return None
            
        try:
            # 打开第一张图片
            with Image.open(image_paths[0]) as img:
                img = img.convert('RGB')
                
                # 创建画布
                canvas_width, canvas_height = 600, 900
                canvas = Image.new('RGB', (canvas_width, canvas_height), (0, 0, 0))
                
                # 调整图片大小并居中
                img_ratio = img.width / img.height
                canvas_ratio = canvas_width / canvas_height
                
                if img_ratio > canvas_ratio:
                    # 图片更宽，以高度为准
                    new_height = canvas_height
                    new_width = int(new_height * img_ratio)
                else:
                    # 图片更高，以宽度为准
                    new_width = canvas_width
                    new_height = int(new_width / img_ratio)
                
                img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # 计算粘贴位置（居中）
                x = (canvas_width - new_width) // 2
                y = (canvas_height - new_height) // 2
                
                canvas.paste(img_resized, (x, y))
                
                # 添加模糊背景
                if blur_size > 0:
                    blurred = img_resized.filter(ImageFilter.GaussianBlur(radius=blur_size))
                    canvas.paste(blurred, (x, y))
                    
                    # 添加半透明遮罩
                    overlay = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, int(255 * (1 - color_ratio))))
                    canvas = Image.alpha_composite(canvas.convert('RGBA'), overlay).convert('RGB')
                    
                    # 再次粘贴原图（较小尺寸）
                    small_width = int(canvas_width * 0.8)
                    small_height = int(small_width / img_ratio)
                    img_small = img.resize((small_width, small_height), Image.Resampling.LANCZOS)
                    
                    x_small = (canvas_width - small_width) // 2
                    y_small = (canvas_height - small_height) // 2
                    canvas.paste(img_small, (x_small, y_small))
                
                # 添加标题文字
                if title and font_path and os.path.exists(font_path):
                    try:
                        font = ImageFont.truetype(font_path, font_size)
                        draw = ImageDraw.Draw(canvas)
                        
                        # 计算文字位置（底部居中）
                        bbox = draw.textbbox((0, 0), title, font=font)
                        text_width = bbox[2] - bbox[0]
                        text_height = bbox[3] - bbox[1]
                        
                        x_text = (canvas_width - text_width) // 2
                        y_text = canvas_height - text_height - 50
                        
                        # 添加文字阴影
                        draw.text((x_text + 2, y_text + 2), title, font=font, fill=(0, 0, 0, 128))
                        # 添加文字
                        draw.text((x_text, y_text), title, font=font, fill=(255, 255, 255, 255))
                    except Exception as e:
                        logger.warning(f"添加文字失败: {e}")
                
                return canvas
                
        except Exception as e:
            logger.error(f"生成单图封面失败: {e}")
            return None
    
    def __update_grid_image(self, style: str, image_paths: List[str], title: str, font_path: str, font_size: int) -> Optional[Image.Image]:
        """更新多图网格封面"""
        if not image_paths:
            return None
            
        try:
            # 创建画布
            canvas_width, canvas_height = 600, 900
            canvas = Image.new('RGB', (canvas_width, canvas_height), (40, 40, 40))
            
            # 根据图片数量确定布局
            num_images = len(image_paths)
            if num_images == 1:
                # 单图居中
                positions = [(0, 0, canvas_width, canvas_height)]
            elif num_images == 2:
                # 两图左右分布
                positions = [
                    (0, 0, canvas_width // 2, canvas_height),
                    (canvas_width // 2, 0, canvas_width // 2, canvas_height)
                ]
            else:
                # 四宫格布局
                positions = [
                    (0, 0, canvas_width // 2, canvas_height // 2),
                    (canvas_width // 2, 0, canvas_width // 2, canvas_height // 2),
                    (0, canvas_height // 2, canvas_width // 2, canvas_height // 2),
                    (canvas_width // 2, canvas_height // 2, canvas_width // 2, canvas_height // 2)
                ]
            
            # 处理每张图片
            for i, (image_path, (x, y, w, h)) in enumerate(zip(image_paths[:len(positions)], positions)):
                try:
                    with Image.open(image_path) as img:
                        img = img.convert('RGB')
                        
                        # 调整图片大小以适应位置
                        img_resized = img.resize((w, h), Image.Resampling.LANCZOS)
                        canvas.paste(img_resized, (x, y))
                        
                except Exception as e:
                    logger.warning(f"处理图片 {image_path} 失败: {e}")
                    continue
            
            # 添加半透明遮罩
            overlay = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 100))
            canvas = Image.alpha_composite(canvas.convert('RGBA'), overlay).convert('RGB')
            
            # 添加标题文字
            if title and font_path and os.path.exists(font_path):
                try:
                    font = ImageFont.truetype(font_path, font_size)
                    draw = ImageDraw.Draw(canvas)
                    
                    # 计算文字位置（底部居中）
                    bbox = draw.textbbox((0, 0), title, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    
                    x_text = (canvas_width - text_width) // 2
                    y_text = canvas_height - text_height - 50
                    
                    # 添加文字背景
                    padding = 10
                    bg_x1 = x_text - padding
                    bg_y1 = y_text - padding
                    bg_x2 = x_text + text_width + padding
                    bg_y2 = y_text + text_height + padding
                    draw.rectangle([bg_x1, bg_y1, bg_x2, bg_y2], fill=(0, 0, 0, 150))
                    
                    # 添加文字
                    draw.text((x_text, y_text), title, font=font, fill=(255, 255, 255, 255))
                except Exception as e:
                    logger.warning(f"添加文字失败: {e}")
            
            return canvas
            
        except Exception as e:
            logger.error(f"生成多图封面失败: {e}")
            return None
    
    def __handle_boxset_library(self, service, library, title):
        """处理合集媒体库"""
        include_types = 'BoxSet,Movie'
        if service.type == 'emby':
            library_id = library.get("Id")
        else:
            library_id = library.get("ItemId")
        parent_id = library_id
        boxsets = self.__get_media_items(service, parent_id, include_types=include_types)
        
        required_items = 1 if self._cover_style.startswith('single') else 9
        valid_items = []
        
        # 首先检查BoxSet本身是否有合适的图片
        valid_boxsets = self.__filter_valid_items(boxsets)
        valid_items.extend(valid_boxsets)
        
        # 如果BoxSet本身没有足够的图片，则获取其中的电影
        if len(valid_items) < required_items:
            for boxset in boxsets:
                if len(valid_items) >= required_items:
                    break
                    
                # 获取此BoxSet中的电影
                movies = self.__get_media_items(service, parent_id=boxset['Id'], include_types=include_types)
                
                valid_movies = self.__filter_valid_items(movies)
                valid_items.extend(valid_movies)
                
                if len(valid_items) >= required_items:
                    break
        
        # 使用获取到的有效项目更新封面
        if len(valid_items) > 0:
            if self._cover_style.startswith('single'):
                return self.__update_single_library_image(service, library, title, valid_items[0])
            else:
                return self.__update_grid_library_image(service, library, title, valid_items[:9])
        else:
            logger.warning(f"媒体库 {service.name}：{library['Name']} 无法找到有效的图片项目")
            return False
    
    def __handle_playlist_library(self, service, library, title):
        """处理播放列表媒体库"""
        include_types = 'Playlist,Movie,Series,Episode,Audio'
        if service.type == 'emby':
            library_id = library.get("Id")
        else:
            library_id = library.get("ItemId")
        parent_id = library_id
        playlists = self.__get_media_items(service, parent_id, include_types=include_types)
        
        required_items = 1 if self._cover_style.startswith('single') else 9
        valid_items = []
        
        # 首先检查 playlist 本身是否有合适的图片
        valid_playlists = self.__filter_valid_items(playlists)
        valid_items.extend(valid_playlists)
        
        # 如果 playlist 本身没有足够的图片，则获取其中的电影
        if len(valid_items) < required_items:
            for playlist in playlists:
                if len(valid_items) >= required_items:
                    break
                    
                # 获取此 playlist 中的电影
                movies = self.__get_media_items(service, parent_id=playlist['Id'], include_types=include_types)
                
                valid_movies = self.__filter_valid_items(movies)
                valid_items.extend(valid_movies)
                
                if len(valid_items) >= required_items:
                    break
        
        # 使用获取到的有效项目更新封面
        if len(valid_items) > 0:
            if self._cover_style.startswith('single'):
                return self.__update_single_library_image(service, library, title, valid_items[0])
            else:
                return self.__update_grid_library_image(service, library, title, valid_items[:9])
        else:
            logger.warning(f"警告: 无法为播放列表 {service.name}：{library['Name']} 找到有效的图片项目")
            return False
    
    def __filter_valid_items(self, items):
        """筛选有效的项目（包含所需图片的项目），并按图片标签去重"""
        valid_items = []
        seen_tags = set()

        for item in items:
            tags = []

            # 统一收集所有可能的图片 tag 字符串作为唯一标识
            if item.get("PrimaryImageTag"):
                tags.append(f"Primary:{item['PrimaryImageTag']}")
            if item.get("AlbumPrimaryImageTag"):
                tags.append(f"AlbumPrimary:{item['AlbumPrimaryImageTag']}")
            if item.get("BackdropImageTags"):
                tags.extend([f"Backdrop:{t}" for t in item["BackdropImageTags"]])
            if item.get("ParentBackdropImageTags"):
                tags.extend([f"ParentBackdrop:{t}" for t in item["ParentBackdropImageTags"]])
            if item.get("ImageTags") and item["ImageTags"].get("Primary"):
                tags.append(f"ImagePrimary:{item['ImageTags']['Primary']}")

            # 判断是否重复（所有 tag 都未见过才添加）
            if any(tag in seen_tags for tag in tags):
                continue  # 跳过已有标签的 item

            # 决定是否为有效项目
            if item['Type'] in 'MusicAlbum,Audio':
                if item.get("ParentBackdropImageTags") or item.get("AlbumPrimaryImageTag") or item.get("PrimaryImageTag"):
                    valid_items.append(item)
                    seen_tags.update(tags)
            elif self._cover_style.startswith('multi'):
                if (item.get("ImageTags") and item["ImageTags"].get("Primary")) \
                    or item.get("BackdropImageTags") \
                    or item.get("ParentBackdropImageTags"):
                    valid_items.append(item)
                    seen_tags.update(tags)
            elif self._cover_style.startswith('single'):
                if item.get("BackdropImageTags") \
                    or item.get("ParentBackdropImageTags") \
                    or (item.get("ImageTags") and item["ImageTags"].get("Primary")):
                    valid_items.append(item)
                    seen_tags.update(tags)

        return valid_items
    
    def __update_single_library_image(self, service, library, title, item):
        """更新单个媒体库的单图封面"""
        logger.info(f"媒体库 {service.name}：{library['Name']} 从媒体项获取图片")
        image_url = self.__get_image_url_from_media_item(item, service)
        if not image_url:
            return False
            
        image_path = self.__download_image(service, image_url, library['Name'], count=1)
        if not image_path:
            return False
            
        # 获取字体
        fonts = self.__get_fonts()
        if not fonts:
            logger.error("无法获取字体")
            return False
            
        font_path, font_size = fonts
        
        # 生成封面
        image_data = self.__update_single_image(self._cover_style, [image_path], title, font_path, font_size, self._blur_size, self._color_ratio)
        if not image_data:
            return False
            
        # 设置媒体库封面
        if service.type == 'emby':
            library_id = library.get("Id")
        else:
            library_id = library.get("ItemId")
            
        return self.__set_library_image(service, library_id, image_data)
    
    def __update_grid_library_image(self, service, library, title, items):
        """更新多个媒体库的网格封面"""
        logger.info(f"媒体库 {service.name}：{library['Name']} 从多个媒体项获取图片")
        image_paths = []
        
        for item in items:
            image_url = self.__get_image_url_from_media_item(item, service)
            if image_url:
                image_path = self.__download_image(service, image_url, library['Name'], count=len(image_paths) + 1)
                if image_path:
                    image_paths.append(image_path)
                    
        if not image_paths:
            return False
            
        # 获取字体
        fonts = self.__get_fonts()
        if not fonts:
            logger.error("无法获取字体")
            return False
            
        font_path, font_size = fonts
        
        # 生成封面
        image_data = self.__update_grid_image(self._cover_style, image_paths, title, font_path, font_size)
        if not image_data:
            return False
            
        # 设置媒体库封面
        if service.type == 'emby':
            library_id = library.get("Id")
        else:
            library_id = library.get("ItemId")
            
        return self.__set_library_image(service, library_id, image_data)