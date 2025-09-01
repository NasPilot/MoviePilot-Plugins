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
            self._port = config.get("port", "3002")
            self._mediaservers = config.get("mediaservers") or []

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
                "mediaservers": self._mediaservers,
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



        return [
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
                                    "icon": "mdi-play-network",
                                    "color": "primary",
                                    "class": "mr-2",
                                },
                            },
                            {"component": "span", "text": "PlexWarp 配置"},
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
                                                            "hint": "启用Plex 302重定向功能",
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
                                                            "model": "port",
                                                            "label": "服务端口",
                                                            "type": "number",
                                                            "hint": "Plex访问STRM文件的端口",
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
                                "component": "VAlert",
                                "props": {
                                    "type": "info",
                                    "variant": "tonal",
                                    "density": "compact",
                                    "class": "mt-3",
                                },
                                "content": [
                                    {
                                        "component": "div",
                                        "text": "💡 使用说明：配置端口后，Plex将通过该端口访问STRM文件进行302重定向播放",
                                    },
                                ],
                            },
                        ],
                    },
                ],
            },
        ], {
            "enabled": False,
            "port": "3002",
            "mediaservers": [],
        }

    def get_page(self) -> List[dict]:
        pass

    def __run_service(self):
        """
        运行服务
        """
        if not self._enabled:
            return

        logger.info("PlexWarp插件已启用，启动Plex 302重定向服务")
        
        try:
            # 启动HTTP服务器用于302重定向
            self._start_redirect_server()
        except Exception as e:
            logger.error(f"PlexWarp服务启动失败: {e}")

    def _start_redirect_server(self):
        """
        启动302重定向服务器
        """
        from flask import Flask, request, redirect, abort
        import threading
        import os
        
        app = Flask(__name__)
        
        @app.route('/<path:file_path>')
        def redirect_strm(file_path):
            """
            处理STRM文件的302重定向
            """
            try:
                # 解码文件路径
                from urllib.parse import unquote
                decoded_path = unquote(file_path)
                
                logger.info(f"PlexWarp: 收到重定向请求 - {decoded_path}")
                
                # 检查文件是否存在
                if not os.path.exists(decoded_path):
                    logger.warning(f"PlexWarp: 文件不存在 - {decoded_path}")
                    abort(404)
                
                # 读取STRM文件内容
                if decoded_path.endswith('.strm'):
                    with open(decoded_path, 'r', encoding='utf-8') as f:
                        redirect_url = f.read().strip()
                    
                    if redirect_url:
                        logger.info(f"PlexWarp: 302重定向到 - {redirect_url}")
                        return redirect(redirect_url, code=302)
                    else:
                        logger.warning(f"PlexWarp: STRM文件内容为空 - {decoded_path}")
                        abort(404)
                else:
                    # 非STRM文件，直接返回404
                    logger.warning(f"PlexWarp: 非STRM文件 - {decoded_path}")
                    abort(404)
                    
            except Exception as e:
                logger.error(f"PlexWarp: 处理重定向请求失败 - {e}")
                abort(500)
        
        # 在后台线程中启动Flask服务器
        def run_server():
            try:
                port = int(self._port) if self._port else 3002
                logger.info(f"PlexWarp: 启动HTTP服务器，端口: {port}")
                app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
            except Exception as e:
                logger.error(f"PlexWarp: HTTP服务器启动失败 - {e}")
        
        self._server_thread = threading.Thread(target=run_server, daemon=True)
        self._server_thread.start()
        logger.info(f"PlexWarp: 302重定向服务已启动，监听端口 {self._port}")







    def stop_service(self):
        """
        停止服务
        """
        try:
            if hasattr(self, '_scheduler') and self._scheduler:
                self._scheduler.shutdown()
                self._scheduler = None
                logger.info("PlexWarp: 调度器已停止")
        except Exception as e:
            logger.error(f"PlexWarp: 停止调度器失败 - {e}")
        
        logger.info("PlexWarp插件已停止")