from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.core.config import settings
from app.log import logger
from app.plugins import _PluginBase


class PlexWarp(_PluginBase):
    # 插件名称
    plugin_name = "PlexWarp"
    # 插件描述
    plugin_desc = "Plex 302重定向中间件：专注于STRM文件的302重定向播放功能，支持路径映射和符号链接处理。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/NasPilot/MoviePilot-Plugins/main/icons/plexwarp.png"
    # 插件版本
    plugin_version = "2.0.0"
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

    # 私有属性
    _enabled = False
    _port = None
    _media_mount_paths = None
    _mediaservers = None
    _path_mapping = None
    _symlink_rules = None
    _check_link_validity = False
    _scheduler = None
    _mediaserver_helper = None
    _mediaserver = None
    _server_type = None
    _server_host = None
    _server_apikey = None
    process = None

    def __init__(self):
        """
        初始化
        """
        super().__init__()
        from app.helper.mediaserver import MediaServerHelper
        self._mediaserver_helper = MediaServerHelper()

    def init_plugin(self, config: dict = None):
        from app.helper.mediaserver import MediaServerHelper
        from apscheduler.schedulers.background import BackgroundScheduler
        import pytz
        from datetime import datetime, timedelta
        
        if not self._mediaserver_helper:
            self._mediaserver_helper = MediaServerHelper()
        self._mediaserver = None

        if config:
            self._enabled = config.get("enabled")
            self._port = config.get("port")
            self._media_mount_paths = config.get("media_mount_paths")
            self._mediaservers = config.get("mediaservers") or []
            self._path_mapping = config.get("path_mapping")
            self._symlink_rules = config.get("symlink_rules")
            self._check_link_validity = config.get("check_link_validity")

            # 获取媒体服务器
            if self._mediaservers:
                self._mediaserver = [self._mediaservers[0]]

        # 获取Plex服务器信息
        if self._mediaserver:
            logger.info(f"PlexWarp: 尝试获取Plex服务器信息，配置的服务器: {self._mediaserver}")
            media_servers = self._mediaserver_helper.get_services(
                name_filters=self._mediaserver
            )
            logger.info(f"PlexWarp: 找到的媒体服务器: {list(media_servers.keys())}")

            if not media_servers:
                logger.warning(f"PlexWarp: 未找到配置的Plex服务器 {self._mediaserver}，将使用默认配置")
                self._server_host = "http://localhost:32400"
                self._server_apikey = ""
                self._server_type = "plex"
            else:
                for _, media_server in media_servers.items():
                    if media_server.type == "plex":
                        self._server_type = media_server.type
                        self._server_apikey = media_server.config.config.get("apikey") or media_server.config.config.get("token")
                        self._server_host = media_server.config.config.get("host")
                        logger.info(f"PlexWarp: 获取到Plex服务器信息 - 地址: {self._server_host}, API密钥: {'已设置' if self._server_apikey else '未设置'}")
                        if self._server_host and self._server_host.endswith("/"):
                            self._server_host = self._server_host.rstrip("/")
                        if self._server_host and not self._server_host.startswith("http"):
                            self._server_host = "http://" + self._server_host
                        logger.info(f"PlexWarp: 处理后的Plex服务器地址: {self._server_host}")
                        break
                else:
                    logger.warning("PlexWarp: 未找到Plex类型的媒体服务器，将使用默认配置")
                    self._server_host = "http://localhost:32400"
                    self._server_apikey = ""
                    self._server_type = "plex"
        else:
            logger.warning("PlexWarp: 未配置媒体服务器，将使用默认Plex配置")
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
                "media_mount_paths": self._media_mount_paths,
                "mediaservers": self._mediaservers,
                "path_mapping": self._path_mapping,
                "symlink_rules": self._symlink_rules,
                "check_link_validity": self._check_link_validity,
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
                        "props": {"cols": 12},
                        "content": [
                            {
                                "component": "VSwitch",
                                "props": {
                                    "model": "check_link_validity",
                                    "label": "链接有效性检查",
                                    "hint": "启用链接有效性检查功能",
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
                                    "rows": 6,
                                    "placeholder": "/mnt/media/movies:/remote/movies\n/mnt/media/tv:/remote/tv\n/local/path:/remote/path",
                                    "hint": "配置本地路径到远程路径的映射，一行一个映射，格式：本地路径:远程路径",
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
                                    "model": "symlink_rules",
                                    "label": "符号链接规则",
                                    "rows": 4,
                                    "placeholder": "/symlink/path:/target/path\n/another/symlink:/another/target",
                                    "hint": "配置符号链接处理规则，一行一个规则，格式：符号链接路径:目标路径",
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
                        "text": "• 路径映射：将本地媒体库路径映射到远程存储路径",
                    },
                    {
                        "component": "div",
                        "text": "• 符号链接：处理符号链接指向的实际路径",
                    },
                    {
                        "component": "div",
                        "text": "• 格式：源路径:目标路径，每行一个映射关系",
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
                                                            "label": "Plex服务器",
                                                            "items": [
                                                                {
                                                                    "title": config.name,
                                                                    "value": config.name,
                                                                }
                                                                for config in self._mediaserver_helper.get_configs().values()
                                                                if config.type == "plex"
                                                            ],
                                                            "hint": "选择要使用的Plex服务器",
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
                                                    "model": "media_mount_paths",
                                                    "label": "媒体挂载路径",
                                                    "rows": 5,
                                                    "placeholder": "/media/strm/movie\n/media/strm/tv",
                                                    "hint": "媒体文件挂载的路径，用于302重定向，一行一个路径",
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
            "media_mount_paths": "",
            "mediaservers": [],
            "path_mapping": "",
            "symlink_rules": "",
            "check_link_validity": True,
            "tab": "web-ui",
        }

    def get_page(self) -> List[dict]:
        pass

    def __run_service(self):
        """
        运行服务
        """
        if not self._enabled:
            return

        logger.info("PlexWarp插件已启用，专注于Plex 302重定向功能")
        # 这里可以添加302重定向相关的初始化逻辑
        # 例如：验证路径映射配置、检查符号链接等







    def stop_service(self):
        """
        停止服务
        """
        logger.info("PlexWarp插件已停止")