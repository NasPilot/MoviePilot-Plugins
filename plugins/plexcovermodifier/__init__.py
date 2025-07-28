import base64
import os
from pathlib import Path
from typing import Any, List, Dict, Tuple, Optional

from app.core.event import eventmanager, Event
from app.log import logger
from app.plugins import _PluginBase
from app.schemas.types import EventType
from app.modules.plex import PlexModule
from app import schemas


class PlexCoverModifier(_PluginBase):
    # 插件名称
    plugin_name = "Plex封面修改器"
    # 插件描述
    plugin_desc = "修改Plex媒体库封面，支持自定义封面图片替换。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/NasPilot/MoviePilot-Plugins/main/icons/plexcover.png"
    # 插件版本
    plugin_version = "1.0.0"
    # 插件作者
    plugin_author = "jxxghp"
    # 作者主页
    author_url = "https://github.com/jxxghp"
    # 插件配置项ID前缀
    plugin_config_prefix = "plexcovermodifier_"
    # 加载顺序
    plugin_order = 1
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _enabled = False
    _cover_path = ""
    _library_covers = {}
    _original_method = None

    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled")
            self._cover_path = config.get("cover_path", "")
            
            # 加载自定义封面配置
            self._load_custom_covers()
            
            # Hook Plex模块的方法
            if self._enabled:
                self._hook_plex_module()
                logger.info("Plex封面修改器已启用")
            else:
                self._unhook_plex_module()

    def _load_custom_covers(self):
        """加载自定义封面配置"""
        if not self._cover_path or not os.path.exists(self._cover_path):
            return
            
        self._library_covers = {}
        cover_dir = Path(self._cover_path)
        
        # 扫描封面目录
        for cover_file in cover_dir.glob("*"):
            if cover_file.is_file() and cover_file.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                # 文件名作为媒体库名称
                library_name = cover_file.stem
                try:
                    # 读取图片并转换为Base64
                    with open(cover_file, "rb") as f:
                        image_data = f.read()
                    
                    # 获取MIME类型
                    mime_type = self._get_mime_type(cover_file.suffix.lower())
                    base64_image = base64.b64encode(image_data).decode('utf-8')
                    data_url = f"data:{mime_type};base64,{base64_image}"
                    
                    self._library_covers[library_name] = data_url
                    logger.info(f"已加载自定义封面：{library_name}")
                    
                except Exception as e:
                    logger.error(f"加载封面文件 {cover_file} 失败：{str(e)}")

    def _get_mime_type(self, suffix: str) -> str:
        """根据文件后缀获取MIME类型"""
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp"
        }
        return mime_types.get(suffix, "image/jpeg")

    def _hook_plex_module(self):
        """
        Hook Plex模块的mediaserver_librarys方法
        """
        try:
            from app.core.module import ModuleManager
            plex_module = ModuleManager().get_running_module("PlexModule")
            if plex_module and hasattr(plex_module, 'mediaserver_librarys'):
                # 保存原始方法
                self._original_method = plex_module.mediaserver_librarys
                # 替换为我们的方法
                plex_module.mediaserver_librarys = self._modified_mediaserver_librarys
                logger.info("已成功Hook Plex模块的mediaserver_librarys方法")
            else:
                logger.warning("未找到Plex模块或mediaserver_librarys方法")
        except Exception as e:
            logger.error(f"Hook Plex模块失败: {e}")
    
    def _unhook_plex_module(self):
        """
        取消Hook Plex模块
        """
        try:
            if self._original_method:
                from app.modules import ModuleManager
                plex_module = ModuleManager().get_running_module("PlexModule")
                if plex_module:
                    plex_module.mediaserver_librarys = self._original_method
                    logger.info("已取消Hook Plex模块")
                self._original_method = None
        except Exception as e:
            logger.error(f"取消Hook Plex模块失败: {e}")
    
    def _modified_mediaserver_librarys(self, server: Optional[str] = None, hidden: Optional[bool] = False, **kwargs) -> Optional[List[schemas.MediaServerLibrary]]:
        """
        修改后的mediaserver_librarys方法
        """
        # 调用原始方法获取媒体库列表
        libraries = self._original_method(server, hidden, **kwargs) if self._original_method else None
        
        # 如果原始方法返回None，直接返回None
        if libraries is None:
            return None
            
        # 修改封面
        for library in libraries:
            if library.name in self._library_covers:
                custom_cover = self._library_covers[library.name]
                if custom_cover:
                    # 替换image_list（生成4张相同的封面）
                    library.image_list = [custom_cover] * 4
                    # 替换主封面
                    library.image = custom_cover
                    logger.debug(f"已为媒体库 {library.name} 应用自定义封面")
        
        return libraries

    def stop_plugin(self):
        """
        停止插件
        """
        self._unhook_plex_module()
        logger.info("Plex封面修改器已停止")

    def get_state(self) -> bool:
        """
        获取插件状态
        """
        return self._enabled

    def get_api(self) -> List[Dict[str, Any]]:
        """
        获取插件API
        """
        return [
            {
                "path": "/reload_covers",
                "endpoint": self.reload_covers,
                "methods": ["POST"],
                "summary": "重新加载自定义封面",
                "description": "重新扫描封面目录并加载自定义封面配置",
            }
        ]

    def reload_covers(self) -> Dict[str, Any]:
        """
        重新加载封面API端点
        """
        try:
            self._load_custom_covers()
            return {
                "success": True,
                "message": f"成功加载 {len(self._library_covers)} 个自定义封面",
                "covers": list(self._library_covers.keys())
            }
        except Exception as e:
            logger.error(f"重新加载封面失败: {e}")
            return {
                "success": False,
                "message": f"加载失败: {str(e)}"
            }

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据
        """
        return [
            {
                'component': 'VForm',
                'content': [
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'enabled',
                                            'label': '启用插件',
                                            'hint': '开启后将修改Plex媒体库封面显示',
                                            'persistent-hint': True
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'cover_path',
                                            'label': '自定义封面目录',
                                            'placeholder': '/path/to/covers',
                                            'hint': '存放自定义封面图片的目录路径，图片文件名应与媒体库名称对应',
                                            'persistent-hint': True
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12
                                },
                                'content': [
                                    {
                                        'component': 'VAlert',
                                        'props': {
                                            'type': 'info',
                                            'variant': 'tonal',
                                            'text': '使用说明：\n1. 在指定目录中放置与Plex媒体库名称相同的图片文件\n2. 支持jpg、png、webp等格式\n3. 图片将自动转换为Base64格式用于显示\n4. 重启插件或调用API可重新加载封面配置'
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ], {
            "enabled": self._enabled,
            "cover_path": self._cover_path
        }

    def stop_service(self):
        """
        停止插件服务
        """
        self._unhook_plex_module()
        logger.info("Plex封面修改器服务已停止")

    def get_page(self) -> Optional[List[dict]]:
        """插件详情页面"""
        return [
            {
                'component': 'VRow',
                'content': [
                    {
                        'component': 'VCol',
                        'props': {
                            'cols': 12
                        },
                        'content': [
                            {
                                'component': 'VAlert',
                                'props': {
                                    'type': 'info',
                                    'variant': 'tonal',
                                    'text': f'当前状态：{"已启用" if self._enabled else "已禁用"}'
                                }
                            }
                        ]
                    }
                ]
            },
            {
                'component': 'VRow',
                'content': [
                    {
                        'component': 'VCol',
                        'props': {
                            'cols': 12
                        },
                        'content': [
                            {
                                'component': 'VAlert',
                                'props': {
                                    'type': 'success',
                                    'variant': 'tonal',
                                    'text': f'已加载自定义封面数量：{len(self._library_covers)}'
                                }
                            }
                        ]
                    }
                ]
            }
        ]