import os
import platform
import subprocess
import tempfile
import shutil
import zipfile
from typing import Any, List, Dict, Tuple
from pathlib import Path
from datetime import datetime, timedelta

import pytz
import psutil
import requests
from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.core.event import eventmanager, Event
from app.helper.mediaserver import MediaServerHelper
from app.log import logger
from app.plugins import _PluginBase
from app.schemas.types import EventType


class PlexWarp(_PluginBase):
    # 插件名称
    plugin_name = "PlexWarp"
    # 插件描述
    plugin_desc = "Plex媒体服务器中间件：基于新版PlexWarp，提供302重定向、路径映射、缓存优化等功能，专为Plex设计。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/NasPilot/MoviePilot-Plugins/main/icons/plexwarp.png"
    # 插件版本
    plugin_version = "1.0.0"
    # 插件作者
    plugin_author = "NasPilot"
    # 作者主页
    author_url = "https://github.com/NasPilot/MoviePilot-Plugins"
    # 插件配置项ID前缀
    plugin_config_prefix = "plexwarp_"
    # 加载顺序
    plugin_order = 15
    # 可使用的用户级别
    auth_level = 1

    _mediaserver_helper = None
    _mediaserver = None
    _mediaservers = None
    _plex_server = None
    _plex_host = None
    _plex_token = None
    # 私有属性
    _scheduler = None
    process = None
    _enabled = False
    _nginx_port = None
    _nginx_ssl_port = None
    _ssl_enable = False
    _ssl_domain = None
    _media_mount_path = None
    _auto_update = False
    _custom_server_url = None
    _redirect_type = None
    _direct_play = None
    _route_cache = None
    _base_url = None

    def __init__(self):
        """
        初始化
        """
        super().__init__()
        # 类名小写
        class_name = self.__class__.__name__.lower()
        # PlexWarp程序路径
        self.__plexwarp_path = settings.PLUGIN_DATA_PATH / class_name / "PlexWarp"
        # 配置文件路径
        self.__config_path = settings.PLUGIN_DATA_PATH / class_name / "config"
        # 日志路径
        self.__logs_dir = settings.PLUGIN_DATA_PATH / class_name / "logs"
        # 版本文件路径
        self.__version_path = settings.PLUGIN_DATA_PATH / class_name / "version.txt"
        # PlexWarp版本
        self.__plexwarp_version = self.__get_current_version()
        
        # 创建必要的目录
        self.__plexwarp_path.mkdir(parents=True, exist_ok=True)
        self.__config_path.mkdir(parents=True, exist_ok=True)
        self.__logs_dir.mkdir(parents=True, exist_ok=True)

    def __get_current_version(self) -> str:
        """
        获取当前PlexWarp版本
        """
        try:
            if self.__version_path.exists():
                with open(self.__version_path, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            return "latest"
        except Exception:
            return "latest"

    def __save_version(self, version: str):
        """
        保存版本信息
        """
        try:
            self.__version_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.__version_path, 'w', encoding='utf-8') as f:
                f.write(version)
        except Exception as e:
            logger.error(f"保存版本信息失败: {str(e)}")

    def init_plugin(self, config: dict = None):
        self._mediaserver_helper = MediaServerHelper()
        self._mediaserver = None

        if config:
            self._enabled = config.get("enabled")
            self._nginx_port = config.get("nginx_port") or 8091
            self._nginx_ssl_port = config.get("nginx_ssl_port") or 8095
            self._ssl_enable = config.get("ssl_enable")
            self._ssl_domain = config.get("ssl_domain")
            self._mediaservers = config.get("mediaservers") or []
            self._media_mount_path = config.get("media_mount_path")
            self._auto_update = config.get("auto_update")
            self._custom_server_url = config.get("custom_server_url")
            self._redirect_type = config.get("redirect_type") or "302"
            self._direct_play = config.get("direct_play", True)
            self._route_cache = config.get("route_cache", True)
            self._base_url = config.get("base_url") or ""

            # 获取媒体服务器
            if self._mediaservers:
                self._mediaserver = [self._mediaservers[0]]

        # 获取Plex服务信息
        if self._mediaserver:
            plex_servers = self._mediaserver_helper.get_services(
                name_filters=self._mediaserver
            )

            for _, plex_server in plex_servers.items():
                if plex_server.type == "plex":
                    self._plex_server = plex_server.type
                    self._plex_token = plex_server.config.config.get("token")
                    self._plex_host = plex_server.config.config.get("host")
                    if self._plex_host and self._plex_host.endswith("/"):
                        self._plex_host = self._plex_host.rstrip("/")
                    if self._plex_host and not self._plex_host.startswith("http"):
                        self._plex_host = "http://" + self._plex_host

        self.stop_service()

        if self._enabled:
            self._scheduler = BackgroundScheduler(timezone=settings.TZ)
            logger.info("PlexWarp 服务启动中...")
            self._scheduler.add_job(
                func=self.__run_service,
                trigger="date",
                run_date=datetime.now(tz=pytz.timezone(settings.TZ))
                + timedelta(seconds=2),
                name="PlexWarp启动服务",
            )

            if self._scheduler.get_jobs():
                self._scheduler.print_jobs()
                self._scheduler.start()
        
        # 注册事件监听
        eventmanager.register(EventType.PluginAction, self.__handle_event)

    def __handle_event(self, event: Event):
        """
        处理插件动作事件
        """
        if not event.event_data:
            return
        
        action = event.event_data.get("action")
        if action == "status":
            status, message = self.get_status()
            self.post_message(
                channel=event.event_data.get("channel"),
                title="PlexWarp状态",
                text=f"状态: {'运行中' if status else '未运行'}\n{message}",
                userid=event.event_data.get("user")
            )
        elif action == "restart":
            self.stop_service()
            if self._enabled:
                self.__run_service()
            self.post_message(
                channel=event.event_data.get("channel"),
                title="PlexWarp重启",
                text="PlexWarp服务已重启",
                userid=event.event_data.get("user")
            )

    def __update_config(self):
        self.update_config(
            {
                "enabled": self._enabled,
                "nginx_port": self._nginx_port,
                "nginx_ssl_port": self._nginx_ssl_port,
                "ssl_enable": self._ssl_enable,
                "ssl_domain": self._ssl_domain,
                "mediaservers": self._mediaservers,
                "media_mount_path": self._media_mount_path,
                "auto_update": self._auto_update,
                "custom_server_url": self._custom_server_url,
                "redirect_type": self._redirect_type,
                "direct_play": self._direct_play,
                "route_cache": self._route_cache,
                "base_url": self._base_url,
            }
        )

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        """
        定义远程控制命令
        """
        return [
            {
                "cmd": "/plexwarp_status",
                "event": EventType.PluginAction,
                "desc": "PlexWarp状态",
                "category": "PlexWarp",
                "data": {"action": "status"},
            },
            {
                "cmd": "/plexwarp_restart",
                "event": EventType.PluginAction,
                "desc": "重启PlexWarp",
                "category": "PlexWarp",
                "data": {"action": "restart"},
            },
        ]

    def get_api(self) -> List[Dict[str, Any]]:
        """
        获取插件API
        """
        return [
            {
                "path": "/plexwarp/status",
                "endpoint": self.get_status,
                "methods": ["GET"],
                "summary": "获取PlexWarp状态",
                "description": "获取PlexWarp服务运行状态",
            }
        ]

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据结构
        """
        return [
            {
                "component": "VCard",
                "props": {"variant": "outlined", "class": "mb-3"},
                "content": [
                    {
                        "component": "VCardTitle",
                        "props": {"class": "d-flex align-center"},
                        "content": [
                            {
                                "component": "VIcon",
                                "props": {
                                    "icon": "mdi-cog",
                                    "color": "primary",
                                    "class": "mr-2",
                                },
                            },
                            {"component": "span", "text": "基础设置"},
                        ],
                    },
                    {"component": "VDivider"},
                    {
                        "component": "VCardText",
                        "content": [
                            {
                                "component": "VForm",
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
                                                            "label": "启用插件",
                                                            "hint": "基于新版PlexWarp项目，提供更好的性能和稳定性",
                                                            "persistent-hint": True,
                                                        },
                                                    }
                                                ],
                                            },
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "md": 4},
                                                "content": [
                                                    {
                                                        "component": "VTextField",
                                                        "props": {
                                                            "model": "nginx_port",
                                                            "label": "Nginx端口",
                                                            "hint": "Nginx HTTP端口，默认8091",
                                                            "persistent-hint": True,
                                                            "type": "number",
                                                        },
                                                    }
                                                ],
                                            },
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "md": 4},
                                                "content": [
                                                    {
                                                        "component": "VSelect",
                                                        "props": {
                                                            "multiple": True,
                                                            "chips": True,
                                                            "clearable": True,
                                                            "model": "mediaservers",
                                                            "label": "媒体服务器",
                                                            "items": [
                                                                {
                                                                    "title": config.name,
                                                                    "value": config.name,
                                                                }
                                                                for config in self._mediaserver_helper.get_configs().values()
                                                                if config.type == "plex"
                                                            ],
                                                            "hint": "选择Plex媒体服务器",
                                                            "persistent-hint": True,
                                                        },
                                                    }
                                                ],
                                            },
                                        ],
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
                                                            "model": "plex_host",
                                                            "label": "Plex服务器地址",
                                                            "placeholder": "http://localhost:32400",
                                                            "hint": "Plex服务器完整地址，留空自动检测",
                                                            "persistent-hint": True,
                                                        },
                                                    }
                                                ],
                                            },
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "md": 6},
                                                "content": [
                                                    {
                                                        "component": "VTextField",
                                                        "props": {
                                                            "model": "redirect_type",
                                                            "label": "重定向类型",
                                                            "placeholder": "302",
                                                            "hint": "HTTP重定向类型，默认302",
                                                            "persistent-hint": True,
                                                        },
                                                    }
                                                ],
                                            },
                                        ],
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
                                                            "model": "media_mount_path",
                                                            "label": "媒体挂载路径",
                                                            "rows": 3,
                                                            "placeholder": "一行一个路径，如：/mnt",
                                                            "hint": "媒体文件挂载路径，用于路径映射",
                                                            "persistent-hint": True,
                                                        },
                                                    },
                                                ],
                                            },
                                        ],
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
                                                            "model": "custom_server_url",
                                                            "label": "自定义服务器访问URL",
                                                            "hint": "在Plex设置>网络中填写的自定义服务器访问URL",
                                                            "persistent-hint": True,
                                                        },
                                                    }
                                                ],
                                            },
                                        ],
                                    },
                                ],
                            },
                        ],
                    },
                ],
            },
            {
                "component": "VCard",
                "props": {"variant": "outlined", "class": "mb-3"},
                "content": [
                    {
                        "component": "VCardTitle",
                        "props": {"class": "d-flex align-center"},
                        "content": [
                            {
                                "component": "VIcon",
                                "props": {
                                    "icon": "mdi-security",
                                    "color": "primary",
                                    "class": "mr-2",
                                },
                            },
                            {"component": "span", "text": "SSL设置"},
                        ],
                    },
                    {"component": "VDivider"},
                    {
                        "component": "VCardText",
                        "content": [
                            {
                                "component": "VForm",
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
                                                            "model": "ssl_enable",
                                                            "label": "启用SSL",
                                                            "hint": "是否启用HTTPS",
                                                            "persistent-hint": True,
                                                        },
                                                    }
                                                ],
                                            },
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "md": 4},
                                                "content": [
                                                    {
                                                        "component": "VTextField",
                                                        "props": {
                                                            "model": "nginx_ssl_port",
                                                            "label": "SSL端口",
                                                            "hint": "Nginx HTTPS端口，默认8095",
                                                            "persistent-hint": True,
                                                            "type": "number",
                                                        },
                                                    }
                                                ],
                                            },
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "md": 4},
                                                "content": [
                                                    {
                                                        "component": "VTextField",
                                                        "props": {
                                                            "model": "ssl_domain",
                                                            "label": "SSL域名",
                                                            "hint": "SSL证书域名",
                                                            "persistent-hint": True,
                                                        },
                                                    }
                                                ],
                                            },
                                        ],
                                    },
                                ],
                            },
                        ],
                    },
                ],
            },
            {
                "component": "VCard",
                "props": {"variant": "outlined", "class": "mb-3"},
                "content": [
                    {
                        "component": "VCardTitle",
                        "props": {"class": "d-flex align-center"},
                        "content": [
                            {
                                "component": "VIcon",
                                "props": {
                                    "icon": "mdi-tune",
                                    "color": "primary",
                                    "class": "mr-2",
                                },
                            },
                            {"component": "span", "text": "高级设置"},
                        ],
                    },
                    {"component": "VDivider"},
                    {
                        "component": "VCardText",
                        "content": [
                            {
                                "component": "VForm",
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
                                                            "model": "auto_update",
                                                            "label": "自动更新",
                                                            "hint": "重启时自动更新plexwarp",
                                                            "persistent-hint": True,
                                                        },
                                                    }
                                                ],
                                            },
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "md": 4},
                                                "content": [
                                                    {
                                                        "component": "VSwitch",
                                                        "props": {
                                                            "model": "direct_play",
                                                            "label": "直接播放",
                                                            "hint": "启用直接播放模式",
                                                            "persistent-hint": True,
                                                        },
                                                    }
                                                ],
                                            },
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "md": 4},
                                                "content": [
                                                    {
                                                        "component": "VSwitch",
                                                        "props": {
                                                            "model": "route_cache",
                                                            "label": "路由缓存",
                                                            "hint": "启用路由缓存优化",
                                                            "persistent-hint": True,
                                                        },
                                                    }
                                                ],
                                            },
                                        ],
                                    },
                                ],
                            },
                        ],
                    },
                ],
            },
            {
                "component": "VCard",
                "props": {"variant": "outlined"},
                "content": [
                    {
                        "component": "VCardTitle",
                        "props": {"class": "d-flex align-center"},
                        "content": [
                            {
                                "component": "VIcon",
                                "props": {
                                    "icon": "mdi-information",
                                    "color": "info",
                                    "class": "mr-2",
                                },
                            },
                            {"component": "span", "text": "使用说明"},
                        ],
                    },
                    {"component": "VDivider"},
                    {
                        "component": "VCardText",
                        "content": [
                            {
                                "component": "VAlert",
                                "props": {"type": "info", "variant": "tonal"},
                                "content": [
                                    {
                                        "component": "div",
                                        "props": {"class": "text-subtitle-2 mb-2"},
                                        "text": "重要配置说明（基于新版PlexWarp项目）：",
                                    },
                                    {
                                        "component": "div",
                                        "text": "1. 在Plex服务器设置中禁用'远程访问'",
                                    },
                                    {
                                        "component": "div",
                                        "text": "2. 在设置>网络中取消'启用中转'的勾选",
                                    },
                                    {
                                        "component": "div",
                                        "text": "3. 填写'自定义服务器访问URL'为PlexWarp的地址",
                                    },
                                    {
                                        "component": "div",
                                        "text": "4. 确保Strm文件路径与媒体挂载路径匹配",
                                    },
                                    {
                                        "component": "div",
                                        "text": "5. 支持302/301重定向、路径映射和缓存优化",
                                    },
                                    {
                                        "component": "div",
                                        "text": "6. 新版本提供更好的性能和稳定性",
                                    },
                                ],
                            },
                        ],
                    },
                ],
            },
        ], {
            "enabled": False,
            "nginx_port": 8091,
            "nginx_ssl_port": 8095,
            "ssl_enable": False,
            "ssl_domain": "",
            "mediaservers": [],
            "media_mount_path": "",
            "auto_update": True,
            "custom_server_url": "",
            "plex_host": "",
            "redirect_type": "302",
            "direct_play": True,
            "route_cache": True,
            "base_url": "",
        }

    def get_status(self) -> Tuple[bool, str]:
        """
        获取插件状态
        """
        try:
            if not self.process or not self.process.is_running():
                return False, "PlexWarp服务未运行"
            
            # 检查服务健康状态
            if self.__check_service_health():
                status_info = []
                if self._nginx_port:
                    status_info.append(f"HTTP端口: {self._nginx_port}")
                if self._ssl_enable and self._nginx_ssl_port:
                    status_info.append(f"HTTPS端口: {self._nginx_ssl_port}")
                if self._plex_host:
                    status_info.append(f"Plex服务器: {self._plex_host}")
                if self._custom_server_url:
                    status_info.append(f"自定义URL: {self._custom_server_url}")
                
                return True, f"PlexWarp服务运行中 (PID: {self.process.pid})\n" + "\n".join(status_info)
            else:
                return False, "PlexWarp服务异常"
        except Exception as e:
            logger.error(f"获取PlexWarp状态失败: {str(e)}")
            return False, f"状态检查失败: {str(e)}"

    def __check_service_health(self) -> bool:
        """
        检查服务健康状态
        """
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex(('localhost', self._nginx_port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def __run_service(self):
        """
        运行服务
        """
        try:
            # 配置验证和自动修复
            if not self.__validate_config():
                logger.error("PlexWarp配置验证失败")
                return
            
            # 版本更新检查
            if self._auto_update and self.__need_update():
                logger.info("检测到新版本，开始更新...")
                if not self.__download_plexwarp():
                    logger.error("PlexWarp更新失败")
                    return
            
            # 下载PlexWarp程序
            if not self.__plexwarp_path.exists() or not any(self.__plexwarp_path.iterdir()):
                logger.info("PlexWarp程序不存在，开始下载...")
                if not self.__download_plexwarp():
                    logger.error("PlexWarp程序下载失败")
                    return
            
            # 生成配置文件
            if not self.__generate_config():
                logger.error("PlexWarp配置文件生成失败")
                return
            
            # 启动PlexWarp服务
            if not self.__start_plexwarp():
                logger.error("PlexWarp服务启动失败")
                return
            
            logger.info("PlexWarp服务启动成功")
            
        except Exception as e:
            logger.error(f"PlexWarp服务启动异常: {str(e)}")

    def __need_update(self) -> bool:
        """
        检查是否需要更新
        """
        try:
            if not self.__version_path.exists():
                return True
            
            current_version = self.__get_current_version()
            return current_version != "latest"
        except Exception:
            return True

    def __validate_config(self) -> bool:
        """
        验证配置
        """
        try:
            # 检查端口范围
            if not (1024 <= self._nginx_port <= 65535):
                logger.error(f"Nginx端口 {self._nginx_port} 超出有效范围")
                return False
            
            if self._ssl_enable and not (1024 <= self._nginx_ssl_port <= 65535):
                logger.error(f"SSL端口 {self._nginx_ssl_port} 超出有效范围")
                return False
            
            # 检查端口冲突
            if self._ssl_enable and self._nginx_port == self._nginx_ssl_port:
                logger.error("HTTP端口和SSL端口不能相同")
                return False
            
            # 检查Plex配置
            if not self._plex_host or not self._plex_token:
                logger.error("Plex服务器配置不完整")
                return False
            
            return True
        except Exception as e:
            logger.error(f"配置验证失败: {str(e)}")
            return False

    def __download_plexwarp(self) -> bool:
        """
        下载PlexWarp程序
        """
        try:
            # 检查版本
            if not self._auto_update and self.__get_current_version() == "latest":
                logger.info("PlexWarp已是最新版本，跳过下载")
                return True
            
            # 备份现有版本
            if self.__plexwarp_path.exists() and any(self.__plexwarp_path.iterdir()):
                backup_path = self.__plexwarp_path.parent / f"PlexWarp_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.copytree(self.__plexwarp_path, backup_path)
                logger.info(f"已备份现有版本到: {backup_path}")
            
            # 下载URL（这里需要替换为实际的PlexWarp下载地址）
            download_url = self.__get_download_url()
            if not download_url:
                logger.error("无法获取PlexWarp下载地址")
                return False
            
            # 下载文件
            logger.info(f"开始下载PlexWarp: {download_url}")
            response = requests.get(download_url, timeout=300, proxies=settings.PROXY)
            response.raise_for_status()
            
            # 确定文件类型和临时文件后缀
            file_suffix = ".tar.gz" if download_url.endswith(".tar.gz") else ".zip"
            
            # 保存到临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_suffix) as tmp_file:
                tmp_file.write(response.content)
                tmp_path = tmp_file.name
            
            try:
                # 清空目标目录
                if self.__plexwarp_path.exists():
                    shutil.rmtree(self.__plexwarp_path)
                self.__plexwarp_path.mkdir(parents=True, exist_ok=True)
                
                # 根据文件类型解压
                if file_suffix == ".tar.gz":
                    import tarfile
                    with tarfile.open(tmp_path, 'r:gz') as tar_ref:
                        tar_ref.extractall(self.__plexwarp_path)
                else:
                    with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                        zip_ref.extractall(self.__plexwarp_path)
                
                # 设置执行权限
                for file_path in self.__plexwarp_path.rglob("*"):
                    if file_path.is_file() and not file_path.suffix:
                        file_path.chmod(0o755)
                
                # 保存版本信息
                self.__save_version("latest")
                
                # 清理旧备份
                self.__cleanup_old_backups()
                
                logger.info("PlexWarp程序下载完成")
                return True
                
            finally:
                # 清理临时文件
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                    
        except Exception as e:
            logger.error(f"PlexWarp程序下载失败: {str(e)}")
            # 尝试从备份恢复
            try:
                backup_dirs = list(self.__plexwarp_path.parent.glob("PlexWarp_backup_*"))
                if backup_dirs:
                    latest_backup = max(backup_dirs, key=lambda x: x.stat().st_mtime)
                    if self.__plexwarp_path.exists():
                        shutil.rmtree(self.__plexwarp_path)
                    shutil.copytree(latest_backup, self.__plexwarp_path)
                    logger.info(f"已从备份恢复: {latest_backup}")
            except Exception as restore_error:
                logger.error(f"从备份恢复失败: {str(restore_error)}")
            return False

    def __cleanup_old_backups(self, keep_count: int = 3):
        """
        清理旧的备份文件，只保留最新的几个
        """
        try:
            backup_dirs = list(self.__plexwarp_path.parent.glob("PlexWarp_backup_*"))
            if len(backup_dirs) > keep_count:
                # 按修改时间排序，保留最新的
                backup_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                for old_backup in backup_dirs[keep_count:]:
                    shutil.rmtree(old_backup, ignore_errors=True)
                    logger.info(f"已清理旧备份: {old_backup.name}")
        except Exception as e:
            logger.error(f"清理备份文件失败: {str(e)}")

    def __get_download_url(self) -> str:
        """
        获取PlexWarp下载地址
        """
        try:
            # 使用新的PlexWarp项目二进制文件
            system = platform.system().lower()
            machine = platform.machine().lower()
            
            base_url = "https://github.com/NasPilot/PlexWarp/releases/latest/download"
            
            if system == "linux":
                if "aarch64" in machine or "arm64" in machine:
                    return f"{base_url}/PlexWarp-linux-arm64.tar.gz"
                else:
                    return f"{base_url}/PlexWarp-linux-amd64.tar.gz"
            elif system == "darwin":
                if "arm64" in machine:
                    return f"{base_url}/PlexWarp-darwin-arm64.tar.gz"
                else:
                    return f"{base_url}/PlexWarp-darwin-amd64.tar.gz"
            elif system == "windows":
                return f"{base_url}/PlexWarp-windows-amd64.zip"
            else:
                logger.error(f"不支持的系统: {system}")
                return None
        except Exception as e:
            logger.error(f"获取下载地址失败: {str(e)}")
            return None

    def __ensure_config_structure(self) -> bool:
        """
        确保配置目录结构正确
        """
        try:
            # 创建必要的目录
            self.__config_path.mkdir(parents=True, exist_ok=True)
            self.__logs_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建nginx配置目录（如果需要）
            nginx_conf_dir = self.__config_path / "nginx" / "conf.d"
            nginx_conf_dir.mkdir(parents=True, exist_ok=True)
            
            return True
        except Exception as e:
            logger.error(f"创建配置目录结构失败: {str(e)}")
            return False
    
    def __generate_config(self) -> bool:
        """
        生成配置文件
        """
        try:
            # 确保配置目录结构正确
            if not self.__ensure_config_structure():
                return False
                
            config_file = self.__config_path / "config.yaml"
            
            # 根据容器环境自动选择Plex地址
            plex_host = self._plex_host or "http://localhost:32400"
            
            # 如果是容器环境且使用默认地址，优先使用容器网关地址
            if plex_host == "http://localhost:32400":
                # 容器环境下使用网关地址
                plex_host = "http://172.17.0.1:32400"
                logger.info("检测到容器环境，使用容器网关地址: 172.17.0.1:32400")
            
            # 处理媒体挂载路径映射
            mount_paths = []
            if self._media_mount_path:
                mount_paths = [path.strip() for path in self._media_mount_path.split('\n') if path.strip()]
            if not mount_paths:
                mount_paths = ["/mnt"]
            
            # 生成新PlexWarp的YAML配置文件
            config_content = f"""# PlexWarp 配置文件
# 自动生成，请勿手动修改
# 基于新版PlexWarp项目

# 服务器配置
server:
  port: {self._nginx_port}
  ssl:
    enabled: {str(self._ssl_enable).lower()}
    port: {self._nginx_ssl_port if self._ssl_enable else 8443}
    cert_file: ""
    key_file: ""
    domain: "{self._ssl_domain or ''}"

# Plex配置
plex:
  url: "{plex_host}"
  token: ""

# 重定向配置
redirect:
  type: "{self._redirect_type}"
  enabled: true
  direct_play: {str(self._direct_play).lower()}

# 路径映射配置
path_mappings:"""
            
            # 添加路径映射
            for i, path in enumerate(mount_paths):
                config_content += f"""
  - name: "mapping_{i+1}"
    from: "{path}"
    to: "{path}"""
            
            config_content += f"""

# 日志配置
logging:
  level: "info"
  file: "logs/plexwarp.log"
  max_size: 100
  max_backups: 5
  max_age: 30

# CORS配置
cors:
  enabled: true
  allowed_origins:
    - "*"
  allowed_methods:
    - "GET"
    - "POST"
    - "PUT"
    - "DELETE"
    - "OPTIONS"
  allowed_headers:
    - "*"

# 缓存配置
cache:
  enabled: {str(self._route_cache).lower()}
  ttl: 300
  max_size: 1000

# 基础URL路径
base_url: "{self._base_url or ''}"
"""
            
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(config_content)
            
            logger.info(f"PlexWarp配置文件已生成: {config_file}")
            logger.info(f"Plex服务器地址: {plex_host}")
            return True
            
        except Exception as e:
            logger.error(f"生成配置文件失败: {str(e)}")
            return False

    def __start_plexwarp(self) -> bool:
        """
        启动PlexWarp服务
        """
        try:
            # 检查是否已经运行
            if self.process and self.process.is_running():
                logger.info("PlexWarp服务已在运行中")
                return True
            
            # 创建日志目录
            self.__logs_dir.mkdir(parents=True, exist_ok=True)
            
            # 查找可执行文件（plexwarp）
            executable = None
            for file_path in self.__plexwarp_path.rglob("*"):
                if file_path.is_file() and (
                    file_path.name.lower().startswith("plexwarp") or 
                    file_path.name.lower() == "plexwarp"
                ):
                    executable = file_path
                    break
            
            if not executable:
                logger.error("未找到PlexWarp可执行文件")
                return False
            
            # 确保可执行文件有执行权限
            import stat
            executable.chmod(executable.stat().st_mode | stat.S_IEXEC)
            
            # 启动命令（新PlexWarp使用-config参数指定配置文件）
            config_file = self.__config_path / "config.yaml"
            cmd = [str(executable), "-config", str(config_file)]
            
            logger.info(f"启动命令: {' '.join(cmd)}")
            logger.info(f"工作目录: {self.__plexwarp_path}")
            logger.info(f"配置文件: {config_file}")
            
            # 启动进程
            self.process = psutil.Popen(
                cmd,
                cwd=str(self.__plexwarp_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 等待启动
            import time
            time.sleep(3)
            
            # 检查进程是否成功启动
            if self.process.is_running():
                logger.info(f"PlexWarp服务启动成功 (PID: {self.process.pid})")
                logger.info(f"服务地址: http://localhost:{self._nginx_port}")
                return True
            else:
                # 获取错误信息
                try:
                    stdout, stderr = self.process.communicate(timeout=1)
                    if stderr:
                        logger.error(f"PlexWarp启动错误: {stderr}")
                    if stdout:
                        logger.info(f"PlexWarp输出: {stdout}")
                except:
                    pass
                logger.error("PlexWarp服务启动失败")
                return False
                
        except Exception as e:
            logger.error(f"启动PlexWarp服务失败: {str(e)}")
            return False

    def stop_service(self):
        """
        停止服务
        """
        try:
            # 停止调度器
            if self._scheduler and self._scheduler.running:
                self._scheduler.shutdown(wait=False)
                self._scheduler = None
                logger.info("PlexWarp调度器已停止")
            
            # 停止PlexWarp进程
            if self.process:
                try:
                    if self.process.is_running():
                        # 尝试优雅停止
                        self.process.terminate()
                        
                        # 等待进程结束
                        import time
                        for _ in range(10):  # 等待最多10秒
                            if not self.process.is_running():
                                break
                            time.sleep(1)
                        
                        # 如果进程仍在运行，强制终止
                        if self.process.is_running():
                            self.process.kill()
                            logger.warning("PlexWarp进程被强制终止")
                        else:
                            logger.info("PlexWarp进程已优雅停止")
                except psutil.NoSuchProcess:
                    logger.info("PlexWarp进程已不存在")
                except psutil.AccessDenied:
                    logger.warning("无权限访问PlexWarp进程")
                finally:
                    self.process = None
                    
        except Exception as e:
            logger.error(f"停止PlexWarp服务失败: {str(e)}")

    def get_dashboard_meta(self) -> dict:
        """
        获取仪表板元数据
        """
        status, message = self.get_status()
        return {
            "name": self.plugin_name,
            "status": status,
            "message": message,
            "icon": self.plugin_icon,
            "version": self.plugin_version,
            "author": self.plugin_author,
            "url": f"http://localhost:{self._nginx_port}" if status and self._nginx_port else None
        }

    def __del__(self):
        """
        析构函数
        """
        self.stop_service()