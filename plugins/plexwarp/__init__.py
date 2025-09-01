import os
import platform
import tarfile
import tempfile
import shutil
from typing import Any, List, Dict, Tuple
from pathlib import Path
from datetime import datetime, timedelta

import pytz
import psutil
import requests
from ruamel.yaml import YAML
from ruamel.yaml.representer import RoundTripRepresenter
from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.helper.mediaserver import MediaServerHelper
from app.log import logger
from app.plugins import _PluginBase


class PlexWarp(_PluginBase):
    # 插件名称
    plugin_name = "PlexWarp"
    # 插件描述
    plugin_desc = "Plex 中间件：支持STRM播放，提供302重定向、直链播放、路径映射、Alist集成等功能。支持完整的strm302重定向配置，包括媒体路径映射、Alist服务集成、客户端过滤等高级功能。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/NasPilot/MoviePilot-Plugins/main/icons/plexwarp.png"
    # 插件版本
    plugin_version = "1.3.0"
    # 插件作者
    plugin_author = "NasPilot"
    # 作者主页
    author_url = "https://github.com/NasPilot"
    # 插件配置项ID前缀
    plugin_config_prefix = "plexwarp_"
    # 加载顺序
    plugin_order = 7
    # 可使用的用户级别
    auth_level = 1

    _mediaserver_helper = None
    _mediaserver = None
    _mediaservers = None
    _server_type = None
    _server_host = None
    _server_apikey = None
    # 私有属性
    _scheduler = None
    process = None
    _enabled = False
    _port = None
    _media_strm_path = None
    _crx = False
    _actor_plus = False
    _fanart_show = False
    _external_player_url = False
    _danmaku = False
    _video_together = False
    _srt2ass = False
    _alist_addr = None
    _alist_token = None
    _alist_sign_enable = False
    _alist_sign_expire = None
    _alist_public_addr = None
    _path_mapping = None

    def __init__(self):
        """
        初始化
        """
        super().__init__()
        # 类名小写
        class_name = self.__class__.__name__.lower()
        # 二进制文件路径
        self.__plexwarp_path = settings.PLUGIN_DATA_PATH / class_name / "PlexWarp"
        # 配置文件路径
        self.__config_path = settings.PLUGIN_DATA_PATH / class_name / "config"
        # 日志路径
        self.__logs_dir = settings.PLUGIN_DATA_PATH / class_name / "logs"
        # 配置文件名
        self.__config_filename = "config.yaml"
        # 二进制文件版本
        self.__plexwarp_version = "0.1.3"
        self.__plexwarp_version_path = (
            settings.PLUGIN_DATA_PATH / class_name / "version.txt"
        )

    def init_plugin(self, config: dict = None):
        self._mediaserver_helper = MediaServerHelper()
        self._mediaserver = None

        if config:
            self._enabled = config.get("enabled")
            self._port = config.get("port")
            self._media_strm_path = config.get("media_strm_path")
            self._mediaservers = config.get("mediaservers") or []
            self._crx = config.get("crx")
            self._actor_plus = config.get("actor_plus")
            self._fanart_show = config.get("fanart_show")
            self._external_player_url = config.get("external_player_url")
            self._danmaku = config.get("danmaku")
            self._video_together = config.get("video_together")
            self._srt2ass = config.get("srt2ass")
            self._alist_addr = config.get("alist_addr")
            self._alist_token = config.get("alist_token")
            self._alist_sign_enable = config.get("alist_sign_enable")
            self._alist_sign_expire = config.get("alist_sign_expire") or "3600"
            self._alist_public_addr = config.get("alist_public_addr")
            self._path_mapping = config.get("path_mapping")

            # 获取媒体服务器
            if self._mediaservers:
                self._mediaserver = [self._mediaservers[0]]

        # 获取媒体服务信息
        if self._mediaserver:
            logger.info(f"PlexWarp: 尝试获取媒体服务器信息，配置的服务器: {self._mediaserver}")
            media_servers = self._mediaserver_helper.get_services(
                name_filters=self._mediaserver
            )
            logger.info(f"PlexWarp: 找到的媒体服务器: {list(media_servers.keys())}")

            if not media_servers:
                logger.warning(f"PlexWarp: 未找到配置的媒体服务器 {self._mediaserver}，将使用默认配置")
                self._server_host = "http://localhost:32400"
                self._server_apikey = ""
                self._server_type = "plex"
            else:
                for _, media_server in media_servers.items():
                    self._server_type = media_server.type
                    self._server_apikey = media_server.config.config.get("apikey") or media_server.config.config.get("token")
                    self._server_host = media_server.config.config.get("host")
                    logger.info(f"PlexWarp: 获取到服务器信息 - 类型: {self._server_type}, 地址: {self._server_host}, API密钥: {'已设置' if self._server_apikey else '未设置'}")
                    if self._server_host and self._server_host.endswith("/"):
                        self._server_host = self._server_host.rstrip("/")
                    if self._server_host and not self._server_host.startswith("http"):
                        self._server_host = "http://" + self._server_host
                    logger.info(f"PlexWarp: 处理后的服务器地址: {self._server_host}")
                    break
        else:
            logger.warning("PlexWarp: 未配置媒体服务器，将使用默认配置")
            self._server_host = "http://localhost:32400"
            self._server_apikey = ""
            self._server_type = "plex"

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

    def __update_config(self):
        self.update_config(
            {
                "enabled": self._enabled,
                "port": self._port,
                "media_strm_path": self._media_strm_path,
                "mediaservers": self._mediaservers,
                "crx": self._crx,
                "actor_plus": self._actor_plus,
                "fanart_show": self._fanart_show,
                "external_player_url": self._external_player_url,
                "danmaku": self._danmaku,
                "video_together": self._video_together,
                "srt2ass": self._srt2ass,
                "alist_addr": self._alist_addr,
                "alist_token": self._alist_token,
                "alist_sign_enable": self._alist_sign_enable,
                "alist_sign_expire": self._alist_sign_expire,
                "alist_public_addr": self._alist_public_addr,
                "path_mapping": self._path_mapping,
            }
        )

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        pass

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据结构
        """

        web_ui = [
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
                                    "model": "crx",
                                    "label": "CRX美化",
                                    "hint": "crx 美化",
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
                                    "model": "actor_plus",
                                    "label": "头像过滤",
                                    "hint": "过滤没有头像的演员和制作人员",
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
                                    "model": "fanart_show",
                                    "label": "显示同人图",
                                    "hint": "显示同人图（fanart 图）",
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
                        "props": {"cols": 12, "md": 4},
                        "content": [
                            {
                                "component": "VSwitch",
                                "props": {
                                    "model": "external_player_url",
                                    "label": "外置播放器",
                                    "hint": "是否开启外置播放器",
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
                                    "model": "danmaku",
                                    "label": "Web弹幕",
                                    "hint": "Web 弹幕",
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
                                    "model": "video_together",
                                    "label": "共同观影",
                                    "hint": "共同观影",
                                    "persistent-hint": True,
                                },
                            }
                        ],
                    },
                ],
            },
        ]

        path_mapping = [
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
                                    "model": "path_mapping",
                                    "label": "路径映射配置",
                                    "rows": 8,
                                    "placeholder": "/mnt/media/movies:/alist/movies\n/mnt/media/tv:/alist/tv\n/local/path:/alist/path",
                                    "hint": "配置本地路径到Alist路径的映射，一行一个映射，格式：本地路径:Alist路径",
                                    "persistent-hint": True,
                                },
                            }
                        ],
                    },
                ],
            },
            {
                "component": "VAlert",
                "props": {
                    "type": "info",
                    "variant": "tonal",
                    "density": "compact",
                    "class": "mt-2",
                },
                "content": [
                    {
                        "component": "div",
                        "text": "路径映射说明：",
                    },
                    {
                        "component": "div",
                        "text": "• 用于将本地媒体库路径映射到Alist中的对应路径",
                    },
                    {
                        "component": "div",
                        "text": "• 格式：本地路径:Alist路径，例如：/mnt/movies:/alist/movies",
                    },
                    {
                        "component": "div",
                        "text": "• 支持多个映射，每行一个映射关系",
                    },
                ],
            },
        ]

        subtitle = [
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
                                    "model": "srt2ass",
                                    "label": "SRT转ASS",
                                    "hint": "SRT 字幕转 ASS 字幕",
                                    "persistent-hint": True,
                                },
                            }
                        ],
                    },
                ],
            },
        ]

        alist = [
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
                                    "model": "alist_addr",
                                    "label": "Alist服务器地址",
                                    "placeholder": "http://localhost:5244",
                                    "hint": "Alist服务器的完整地址，包含协议和端口",
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
                                "component": "VTextField",
                                "props": {
                                    "model": "alist_token",
                                    "label": "Alist Token",
                                    "type": "password",
                                    "placeholder": "输入Alist访问令牌",
                                    "hint": "用于访问Alist API的认证令牌",
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
                                "component": "VSwitch",
                                "props": {
                                    "model": "alist_sign_enable",
                                    "label": "启用签名",
                                    "hint": "启用Alist URL签名功能",
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
                                    "model": "alist_sign_expire",
                                    "label": "签名过期时间(秒)",
                                    "type": "number",
                                    "hint": "URL签名的有效期，单位为秒",
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
                                "component": "VTextField",
                                "props": {
                                    "model": "alist_public_addr",
                                    "label": "Alist公网地址",
                                    "placeholder": "https://your-domain.com",
                                    "hint": "Alist的公网访问地址，用于生成外部可访问的链接",
                                    "persistent-hint": True,
                                },
                            }
                        ],
                    },
                ],
            },
        ]

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
                                                            "model": "port",
                                                            "label": "端口",
                                                            "hint": "反代后媒体服务器访问端口",
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
                                                                if config.type in ["plex", "jellyfin", "emby"]
                                                            ],
                                                            "hint": "同时只能选择一个",
                                                            "persistent-hint": True,
                                                        },
                                                    }
                                                ],
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
                                                "component": "VTextarea",
                                                "props": {
                                                    "model": "media_strm_path",
                                                    "label": "STRM 媒体库路径",
                                                    "rows": 5,
                                                    "placeholder": "/media/strm/movie\n/media/strm/tv",
                                                    "hint": "一行一个路径，例如：/media/strm/movie 和 /media/strm/tv",
                                                    "persistent-hint": True,
                                                },
                                            },
                                        ],
                                    }
                                ],
                            },
                            {
                                "component": "VAlert",
                                "props": {
                                    "type": "info",
                                    "variant": "tonal",
                                    "density": "compact",
                                    "class": "mt-2",
                                },
                                "content": [
                                    {
                                        "component": "div",
                                        "text": "注意事项：",
                                    },
                                    {
                                        "component": "div",
                                        "text": "• 如果 MoviePilot 容器为 bridge 模式，需要手动映射配置的端口",
                                    },
                                    {
                                        "component": "div",
                                        "text": "• 更多详细配置可以前往 MoviePilot 配置目录找到此插件的配置目录进行配置文件配置",
                                    },
                                ],
                            },
                            {
                                "component": "VAlert",
                                "props": {
                                    "type": "success",
                                    "variant": "tonal",
                                    "density": "compact",
                                    "class": "mt-2",
                                },
                                "content": [
                                    {
                                        "component": "div",
                                        "text": "支持的 STRM 文件类型：",
                                    },
                                    {
                                        "component": "div",
                                        "text": "• 115网盘STRM助手、123云盘STRM助手、CloudMediaSync",
                                    },
                                    {
                                        "component": "div",
                                        "text": "• OneStrm、Symedia、q115-strm 等软件生成的 STRM 文件",
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
                        "component": "VTabs",
                        "props": {"model": "tab", "grow": True, "color": "primary"},
                        "content": [
                            {
                                "component": "VTab",
                                "props": {"value": "web-ui"},
                                "content": [
                                    {
                                        "component": "VIcon",
                                        "props": {
                                            "icon": "mdi-file-move-outline",
                                            "start": True,
                                            "color": "#1976D2",
                                        },
                                    },
                                    {"component": "span", "text": "Web页面配置"},
                                ],
                            },
                            {
                                "component": "VTab",
                                "props": {"value": "subtitle"},
                                "content": [
                                    {
                                        "component": "VIcon",
                                        "props": {
                                            "icon": "mdi-sync",
                                            "start": True,
                                            "color": "#4CAF50",
                                        },
                                    },
                                    {"component": "span", "text": "字体相关设置"},
                                ],
                            },
                            {
                                "component": "VTab",
                                "props": {"value": "alist"},
                                "content": [
                                    {
                                        "component": "VIcon",
                                        "props": {
                                            "icon": "mdi-cloud",
                                            "start": True,
                                            "color": "#FF9800",
                                        },
                                    },
                                    {"component": "span", "text": "Alist配置"},
                                ],
                            },
                            {
                                "component": "VTab",
                                "props": {"value": "path-mapping"},
                                "content": [
                                    {
                                        "component": "VIcon",
                                        "props": {
                                            "icon": "mdi-folder-swap",
                                            "start": True,
                                            "color": "#9C27B0",
                                        },
                                    },
                                    {"component": "span", "text": "路径映射"},
                                ],
                            },
                        ],
                    },
                    {"component": "VDivider"},
                    {
                        "component": "VWindow",
                        "props": {"model": "tab"},
                        "content": [
                            {
                                "component": "VWindowItem",
                                "props": {"value": "web-ui"},
                                "content": [
                                    {
                                        "component": "VCardText",
                                        "content": web_ui,
                                    }
                                ],
                            },
                            {
                                "component": "VWindowItem",
                                "props": {"value": "subtitle"},
                                "content": [
                                    {"component": "VCardText", "content": subtitle}
                                ],
                            },
                            {
                                "component": "VWindowItem",
                                "props": {"value": "alist"},
                                "content": [
                                    {"component": "VCardText", "content": alist}
                                ],
                            },
                            {
                                "component": "VWindowItem",
                                "props": {"value": "path-mapping"},
                                "content": [
                                    {"component": "VCardText", "content": path_mapping}
                                ],
                            },
                        ],
                    },
                ],
            },
        ], {
            "enabled": False,
            "port": "3002",
            "media_strm_path": "",
            "mediaservers": [],
            "crx": False,
            "actor_plus": False,
            "fanart_show": False,
            "external_player_url": False,
            "danmaku": False,
            "video_together": False,
            "srt2ass": False,
            "alist_addr": "",
            "alist_token": "",
            "alist_sign_enable": False,
            "alist_sign_expire": "3600",
            "alist_public_addr": "",
            "path_mapping": "",
            "tab": "web-ui",
        }

    def get_page(self) -> List[dict]:
        pass

    def __run_service(self):
        """
        运行服务
        """
        if not Path(self.__plexwarp_path).exists():
            logger.info("尝试自动下载二进制文件中...")
            self.__download_and_extract()
            if not Path(self.__plexwarp_path).exists():
                logger.error("下载失败，PlexWarp 二进制文件不存在，无法启动插件")
                logger.info(
                    f"请将 PlexWarp 二进制文件放入 {settings.PLUGIN_DATA_PATH / self.__class__.__name__.lower()} 文件夹内"
                )
                self.__update_config()
                return

        if os.path.exists(self.__plexwarp_version_path):
            with open(self.__plexwarp_version_path, "r", encoding="utf-8") as f:
                version = f.read().strip()
            if version != self.__plexwarp_version:
                logger.info("尝试自动更新二进制文件中...")
                self.__download_and_extract()

        if not Path(self.__config_path / self.__config_filename).exists():
            logger.error("PlexWarp 配置文件不存在，无法启动插件")
            self.__update_config()
            return

        # 根据服务器类型生成配置
        if self._server_type == "plex":
            changes = self.__generate_plex_config()
        elif self._server_type in ["emby", "jellyfin"]:
            changes = self.__generate_emby_jellyfin_config()
        else:
            logger.error(f"不支持的媒体服务器类型: {self._server_type}，将使用 Plex 配置")
            changes = self.__generate_plex_config()
            
        self.__modify_config(Path(self.__config_path / self.__config_filename), changes)

        Path(self.__config_path).mkdir(parents=True, exist_ok=True)
        Path(self.__logs_dir).mkdir(parents=True, exist_ok=True)

        # 启动PlexWarp进程，指定配置文件路径
        config_file_path = str(Path(self.__config_path / self.__config_filename))
        self.process = psutil.Popen(
            [self.__plexwarp_path, "-config", config_file_path],
            cwd=str(self.__config_path.parent)
        )

        if self.process.is_running():
            logger.info("PlexWarp 服务成功启动！")

    def __generate_plex_config(self):
        """
        生成Plex配置
        """
        logger.info(f"PlexWarp: 生成Plex配置 - 服务器地址: {self._server_host}, API密钥: {'已设置' if self._server_apikey else '未设置'}")
        config = {
            # 基础服务配置
            "port": int(self._port) if self._port else 3002,
            "host": "0.0.0.0",
            
            # Plex服务器配置
            "plex_server": {
                "addr": self._server_host,
                "auth": self._server_apikey or ""
            },
            
            # 日志配置
            "logger": {
                "access_logger": {
                    "console": False,
                    "file": True
                },
                "service_logger": {
                    "console": True,
                    "file": True
                }
            },
            
            # Web前端配置
            "web": {
                "enable": True,
                "custom": False,
                "index": bool(Path(self.__config_path / "static" / "index.html").exists()),
                "head": "",
                "external_player_url": bool(self._external_player_url),
                "crx": bool(self._crx),
                "actor_plus": bool(self._actor_plus),
                "fanart_show": bool(self._fanart_show),
                "danmaku": bool(self._danmaku),
                "video_together": bool(self._video_together)
            },
            
            # 客户端过滤配置
            "client_filter": {
                "enable": False,
                "mode": "allow",
                "client_list": ["Plex", "PlexAmp"]
            },
            
            # HTTP Strm配置
            "http_strm": {
                "enable": True,
                "trans_code": True,
                "final_url": True,
                "prefix_list": self._media_strm_path.split("\n") if self._media_strm_path else []
            },
            
            # Alist Strm配置
            "alist_strm": {
                "enable": False,
                "trans_code": True,
                "raw_url": False
            },
            
            # 字幕配置
            "subtitle": {
                "enable": bool(self._srt2ass),
                "srt2ass": bool(self._srt2ass),
                "ass_style": [],
                "sub_set": False
            },
            
            # Strm302重定向配置 - 核心功能
            "strm302": {
                "enable": True,
                "media_mount_path": self._media_strm_path.split("\n") if self._media_strm_path else ["/mnt"],
                "transcode_enable": True,
                "fallback_original": True
            },
            
            # Alist配置
            "alist": {
                "addr": self._alist_addr or "",
                "token": self._alist_token or "",
                "sign_enable": bool(self._alist_sign_enable),
                "sign_expire_time": int(self._alist_sign_expire) if self._alist_sign_expire else 3600,
                "public_addr": self._alist_public_addr or "",
                "raw_url_mapping": {}
            },
            
            # 重定向配置
            "redirect": {
                "enable": True,
                "check_enable": False,
                "media_path_mapping": self.__parse_path_mapping(self._path_mapping) if self._path_mapping else [],
                "symlink_rules": []
            }
        }
        return config

    def __generate_emby_jellyfin_config(self):
        """
        生成Emby/Jellyfin配置
        """
        logger.info(f"PlexWarp: 生成{self._server_type.title()}配置 - 服务器地址: {self._server_host}, API密钥: {'已设置' if self._server_apikey else '未设置'}")
        config = {
            # 基础服务配置
            "port": int(self._port) if self._port else 3002,
            "host": "0.0.0.0",
            
            # Emby/Jellyfin服务器配置
             "emby_server": {
                 "addr": self._server_host,
                 "auth": self._server_apikey or ""
             },
            
            # 日志配置
            "logger": {
                "access_logger": {
                    "console": False,
                    "file": True
                },
                "service_logger": {
                    "console": True,
                    "file": True
                }
            },
            
            # Web前端配置
            "web": {
                "enable": True,
                "custom": False,
                "index": bool(Path(self.__config_path / "static" / "index.html").exists()),
                "head": "",
                "external_player_url": bool(self._external_player_url),
                "crx": bool(self._crx),
                "actor_plus": bool(self._actor_plus),
                "fanart_show": bool(self._fanart_show),
                "danmaku": bool(self._danmaku),
                "video_together": bool(self._video_together)
            },
            
            # 客户端过滤配置
            "client_filter": {
                "enable": False,
                "mode": "allow",
                "client_list": ["Emby", "Jellyfin"]
            },
            
            # HTTP Strm配置
            "http_strm": {
                "enable": True,
                "trans_code": True,
                "final_url": True,
                "prefix_list": self._media_strm_path.split("\n") if self._media_strm_path else []
            },
            
            # Alist Strm配置
            "alist_strm": {
                "enable": False,
                "trans_code": True,
                "raw_url": False
            },
            
            # 字幕配置
            "subtitle": {
                "enable": bool(self._srt2ass),
                "srt2ass": bool(self._srt2ass),
                "ass_style": [],
                "sub_set": False
            },
            
            # Strm302重定向配置 - 核心功能
            "strm302": {
                "enable": True,
                "media_mount_path": self._media_strm_path.split("\n") if self._media_strm_path else ["/mnt"],
                "transcode_enable": True,
                "fallback_original": True
            },
            
            # Alist配置
            "alist": {
                "addr": self._alist_addr or "",
                "token": self._alist_token or "",
                "sign_enable": bool(self._alist_sign_enable),
                "sign_expire_time": int(self._alist_sign_expire) if self._alist_sign_expire else 3600,
                "public_addr": self._alist_public_addr or "",
                "raw_url_mapping": {}
            },
            
            # 重定向配置
            "redirect": {
                "enable": True,
                "check_enable": False,
                "media_path_mapping": self.__parse_path_mapping(self._path_mapping) if self._path_mapping else [],
                "symlink_rules": []
            }
        }
        return config

    def __parse_path_mapping(self, path_mapping_str):
        """
        解析路径映射字符串
        """
        if not path_mapping_str:
            return []
        
        mappings = []
        for line in path_mapping_str.strip().split('\n'):
            line = line.strip()
            if line and ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    local_path = parts[0].strip()
                    alist_path = parts[1].strip()
                    if local_path and alist_path:
                        mappings.append({
                            "local_path": local_path,
                            "alist_path": alist_path
                        })
        return mappings

    def __modify_config(self, config_path, modifications):
        """
        修改配置文件

        :param config_path: 配置文件路径
        :param modifications: 要修改的配置项字典
        :return: None
        """
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.indent(mapping=2, sequence=4, offset=2)

        def represent_bool(self, data):
            if data:
                return self.represent_scalar("tag:yaml.org,2002:bool", "True")
            else:
                return self.represent_scalar("tag:yaml.org,2002:bool", "False")

        RoundTripRepresenter.add_representer(bool, represent_bool)

        with open(config_path, "r", encoding="utf-8") as file:
            config = yaml.load(file)

        for key, value in modifications.items():
            keys = key.split(".")
            current = config
            for k in keys[:-1]:
                current = current.setdefault(k, {})
            current[keys[-1]] = value

        with open(config_path, "w", encoding="utf-8") as file:
            yaml.dump(config, file)

    def __get_download_url(self):
        """
        获取下载链接
        """
        base_url = "https://github.com/NasPilot/PlexWarp/releases/download/v{version}/PlexWarp_{version}_{os}_{arch}.tar.gz"

        machine = platform.machine().lower()
        if machine == "arm64" or machine == "aarch64":
            arch = "arm64"
        else:
            arch = "amd64"

        system = platform.system().lower()
        if system == "darwin":
            os_name = "darwin"
        else:
            os_name = "linux"

        return base_url.format(arch=arch, version=self.__plexwarp_version, os=os_name)

    def __download_and_extract(self):
        """
        下载并解压
        """
        url = self.__get_download_url()
        temp_dir = tempfile.mkdtemp()
        temp_file = os.path.join(temp_dir, "PlexWarp.tar.gz")

        try:
            Path(self.__config_path).mkdir(parents=True, exist_ok=True)

            logger.info(f"正在下载: {url}")
            response = requests.get(url, stream=True, proxies=settings.PROXY)
            response.raise_for_status()

            with open(temp_file, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info("正在解压文件...")
            with tarfile.open(temp_file, "r:gz") as tar:
                plexwarp_member = [
                    m for m in tar.getmembers() if m.name.endswith("PlexWarp")
                ]
                if plexwarp_member:
                    tar.extract(member=plexwarp_member[0], path=temp_dir)
                    extracted_path = Path(temp_dir) / plexwarp_member[0].name
                    extracted_path.chmod(0o755)
                    shutil.copy2(extracted_path, Path(self.__plexwarp_path))

                config_target = Path(self.__config_path / self.__config_filename)
                if not config_target.exists():
                    config_example_member = [
                        m
                        for m in tar.getmembers()
                        if m.name.endswith("config.yaml.example")
                    ]
                    if config_example_member:
                        tar.extract(member=config_example_member[0], path=temp_dir)
                        extracted_config = (
                            Path(temp_dir) / config_example_member[0].name
                        )
                        shutil.copy2(extracted_config, config_target)
                        logger.info(f"示例配置文件已保存到 {config_target}")

            with open(self.__plexwarp_version_path, "w", encoding="utf-8") as f:
                f.write(self.__plexwarp_version)
            logger.info(f"安装完成！PlexWarp 已安装到 {self.__plexwarp_path}")
        except Exception as e:
            logger.info(f"发生错误: {e}")
        finally:
            shutil.rmtree(temp_dir)

    def stop_service(self):
        """
        退出插件
        """
        try:
            if self._scheduler:
                self._scheduler.remove_all_jobs()
                if self._scheduler.running:
                    self._scheduler.shutdown()
                self._scheduler = None
            if self.process:
                if self.process.is_running():
                    self.process.terminate()
        except Exception as e:
            logger.error(f"退出插件失败：{e}")