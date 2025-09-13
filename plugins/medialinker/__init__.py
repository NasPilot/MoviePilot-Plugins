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


class MediaLinker(_PluginBase):
    # 插件名称
    plugin_name = "MediaLinker"
    # 插件描述
    plugin_desc = "Plex媒体服务器中间件：优化播放Strm文件、提供直链功能、支持Alist集成。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/jxxghp/MoviePilot-Plugins/refs/heads/main/icons/link.png"
    # 插件版本
    plugin_version = "1.0.0"
    # 插件作者
    plugin_author = "thsrite"
    # 作者主页
    author_url = "https://github.com/thsrite"
    # 插件配置项ID前缀
    plugin_config_prefix = "medialinker_"
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
    _alist_addr = None
    _alist_token = None
    _alist_sign_enable = False
    _alist_sign_expire_time = None
    _alist_public_addr = None
    _auto_update = False

    def __init__(self):
        """
        初始化
        """
        super().__init__()
        # 类名小写
        class_name = self.__class__.__name__.lower()
        # MediaLinker程序路径
        self.__medialinker_path = settings.PLUGIN_DATA_PATH / class_name / "MediaLinker"
        # 配置文件路径
        self.__config_path = settings.PLUGIN_DATA_PATH / class_name / "config"
        # 日志路径
        self.__logs_dir = settings.PLUGIN_DATA_PATH / class_name / "logs"
        # Nginx配置路径
        self.__nginx_conf_path = settings.PLUGIN_DATA_PATH / class_name / "nginx"
        # SSL证书路径
        self.__ssl_path = settings.PLUGIN_DATA_PATH / class_name / "ssl"
        # 版本文件路径
        self.__version_path = settings.PLUGIN_DATA_PATH / class_name / "version.txt"
        # MediaLinker版本
        self.__medialinker_version = self.__get_current_version()
        
        # 创建必要的目录
        self.__medialinker_path.mkdir(parents=True, exist_ok=True)
        self.__config_path.mkdir(parents=True, exist_ok=True)
        self.__logs_dir.mkdir(parents=True, exist_ok=True)
        self.__nginx_conf_path.mkdir(parents=True, exist_ok=True)
        self.__ssl_path.mkdir(parents=True, exist_ok=True)

    def __get_current_version(self) -> str:
        """
        获取当前MediaLinker版本
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
    
    def __need_update(self) -> bool:
        """
        检查是否需要更新
        """
        try:
            if not self.__version_path.exists():
                return True
            
            current_version = self.__get_current_version()
            # 这里可以添加更复杂的版本比较逻辑
            # 目前简单地检查是否为latest
            return current_version != "latest"
        except Exception:
            return True
    
    def __get_latest_version(self) -> str:
        """
        获取最新版本信息
        """
        try:
            # 可以通过GitHub API获取最新版本
            # 这里简化为返回latest
            return "latest"
        except Exception:
            return "latest"

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
            self._alist_addr = config.get("alist_addr")
            self._alist_token = config.get("alist_token")
            self._alist_sign_enable = config.get("alist_sign_enable")
            self._alist_sign_expire_time = config.get("alist_sign_expire_time") or 12
            self._alist_public_addr = config.get("alist_public_addr")
            self._auto_update = config.get("auto_update")

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
            logger.info("MediaLinker 服务启动中...")
            self._scheduler.add_job(
                func=self.__run_service,
                trigger="date",
                run_date=datetime.now(tz=pytz.timezone(settings.TZ))
                + timedelta(seconds=2),
                name="MediaLinker启动服务",
            )

            if self._scheduler.get_jobs():
                self._scheduler.print_jobs()
                self._scheduler.start()
        
        # 注册事件监听
        eventmanager.register(EventType.PluginAction, self.__handle_event)

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
                "alist_addr": self._alist_addr,
                "alist_token": self._alist_token,
                "alist_sign_enable": self._alist_sign_enable,
                "alist_sign_expire_time": self._alist_sign_expire_time,
                "alist_public_addr": self._alist_public_addr,
                "auto_update": self._auto_update,
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
                "cmd": "/medialinker_status",
                "event": EventType.PluginAction,
                "desc": "MediaLinker状态",
                "category": "MediaLinker",
                "data": {"action": "status"},
            },
            {
                "cmd": "/medialinker_restart",
                "event": EventType.PluginAction,
                "desc": "重启MediaLinker",
                "category": "MediaLinker",
                "data": {"action": "restart"},
            },
        ]

    def get_api(self) -> List[Dict[str, Any]]:
        """
        获取插件API
        """
        return [
            {
                "path": "/medialinker/status",
                "endpoint": self.get_status,
                "methods": ["GET"],
                "summary": "获取MediaLinker状态",
                "description": "获取MediaLinker服务运行状态",
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
                                                            "model": "alist_addr",
                                                            "label": "Alist地址",
                                                            "hint": "Alist服务地址，如：http://localhost:5244",
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
                                                            "model": "alist_token",
                                                            "label": "Alist Token",
                                                            "hint": "Alist API Token",
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
                                                            "hint": "rclone挂载的媒体库路径",
                                                            "persistent-hint": True,
                                                        },
                                                    },
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
                "props": {"variant": "outlined"},
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
                                                            "hint": "重启时自动更新MediaLinker",
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
                                                            "model": "alist_sign_enable",
                                                            "label": "Alist签名",
                                                            "hint": "是否启用Alist签名验证",
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
                                                            "model": "alist_sign_expire_time",
                                                            "label": "签名过期时间",
                                                            "hint": "Alist签名过期时间（小时）",
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
                                                            "hint": "Alist公网访问地址，用于客户端直接访问",
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
        ], {
            "enabled": False,
            "nginx_port": 8091,
            "nginx_ssl_port": 8095,
            "ssl_enable": False,
            "ssl_domain": "",
            "mediaservers": [],
            "media_mount_path": "",
            "alist_addr": "",
            "alist_token": "",
            "alist_sign_enable": False,
            "alist_sign_expire_time": 12,
            "alist_public_addr": "",
            "auto_update": False,
        }

    def __run_service(self):
        """
        运行MediaLinker服务
        """
        try:
            # 验证配置
            if not self.__validate_config():
                logger.error("配置验证失败，无法启动服务")
                return
            
            # 生成配置文件
            self.__generate_config()
            
            # 下载或更新MediaLinker
            if self._auto_update or not self.__medialinker_path.exists():
                if not self.__download_medialinker():
                    logger.error("下载MediaLinker程序失败")
                    return
            
            # 启动服务
            if self.__start_medialinker():
                logger.info("MediaLinker 服务启动成功")
            else:
                logger.error("MediaLinker 服务启动失败")
            
        except Exception as e:
            logger.error(f"MediaLinker 服务启动失败: {str(e)}")

    def __validate_config(self) -> bool:
        """
        验证配置并自动修复
        """
        try:
            # 检查必要的配置项
            if not self._nginx_port:
                logger.warning("Nginx端口未配置，使用默认值8091")
                self._nginx_port = 8091
                self.__update_config()
            
            if not self._nginx_ssl_port:
                logger.warning("Nginx SSL端口未配置，使用默认值8095")
                self._nginx_ssl_port = 8095
                self.__update_config()
            
            # 验证端口范围
            if not (1024 <= self._nginx_port <= 65535):
                logger.warning(f"Nginx端口{self._nginx_port}不在有效范围内，重置为8091")
                self._nginx_port = 8091
                self.__update_config()
            
            if not (1024 <= self._nginx_ssl_port <= 65535):
                logger.warning(f"Nginx SSL端口{self._nginx_ssl_port}不在有效范围内，重置为8095")
                self._nginx_ssl_port = 8095
                self.__update_config()
            
            # 检查端口冲突
            if self._nginx_port == self._nginx_ssl_port:
                logger.warning("HTTP和HTTPS端口冲突，调整SSL端口")
                self._nginx_ssl_port = self._nginx_port + 1
                self.__update_config()
            
            # 验证Plex配置
            if not self._plex_host or not self._plex_token:
                logger.warning("Plex服务器配置不完整，请检查媒体服务器设置")
            
            # 验证Alist配置
            if self._alist_addr and not self._alist_addr.startswith(('http://', 'https://')):
                logger.warning("Alist地址格式不正确，自动添加http://前缀")
                self._alist_addr = 'http://' + self._alist_addr
                self.__update_config()
            
            # 验证SSL配置
            if self._ssl_enable and not self._ssl_domain:
                logger.warning("启用SSL但未配置域名，SSL功能可能无法正常工作")
            
            # 验证签名过期时间
            if self._alist_sign_expire_time and not (1 <= self._alist_sign_expire_time <= 168):
                logger.warning(f"签名过期时间{self._alist_sign_expire_time}不在有效范围内，重置为12小时")
                self._alist_sign_expire_time = 12
                self.__update_config()
            
            # 创建必要的目录
            self.__create_required_directories()
            
            logger.info("配置验证通过")
            return True
            
        except Exception as e:
            logger.error(f"配置验证失败: {str(e)}")
            return False
    
    def __create_required_directories(self):
        """
        创建必要的目录
        """
        try:
            directories = [
                self.__medialinker_path,
                self.__config_path,
                self.__logs_dir,
                self.__nginx_conf_path,
                self.__ssl_path
            ]
            
            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)
                
            logger.debug("必要目录创建完成")
        except Exception as e:
            logger.error(f"创建目录失败: {str(e)}")
            raise

    def __generate_config(self):
        """
        生成MediaLinker配置文件
        """
        try:
            # 生成constant.js配置文件
            config_content = self.__generate_constant_js()
            config_file = self.__config_path / "constant.js"
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(config_content)
            
            # 设置配置目录结构
            self.__setup_config_directory()
            
            logger.info("MediaLinker配置文件生成成功")
        except Exception as e:
            logger.error(f"生成MediaLinker配置文件失败: {str(e)}")

    def __generate_constant_js(self) -> str:
        """
        生成constant.js配置内容
        """
        # 处理媒体挂载路径
        mount_paths = []
        if self._media_mount_path:
            mount_paths = [path.strip() for path in self._media_mount_path.split('\n') if path.strip()]
        
        mount_paths_str = str(mount_paths).replace("'", '"')
        
        config_template = f'''// MediaLinker配置文件 - 由MoviePilot插件自动生成

// Plex服务器地址
const plexHost = "{self._plex_host or 'http://localhost:32400'}";

// rclone挂载目录
const mediaMountPath = {mount_paths_str};

// Alist地址
const alistAddr = "{self._alist_addr or 'http://localhost:5244'}";

// Alist Token
const alistToken = "{self._alist_token or ''}";

// Alist签名设置
const alistSignEnable = {str(self._alist_sign_enable).lower()};
const alistSignExpireTime = {self._alist_sign_expire_time or 12};

// Alist公网地址
const alistPublicAddr = "{self._alist_public_addr or ''}";

// 字符串头配置
const strHead = {{
  lanIp: ["172.", "10.", "192.", "[fd00:"],
  xEmbyClients: {{
    seekBug: ["Emby for iOS"],
  }},
  xUAs: {{
    seekBug: ["Infuse", "VidHub", "SenPlayer"],
    clientsPC: ["EmbyTheater"],
    clients3rdParty: ["Fileball", "Infuse", "SenPlayer", "VidHub"],
    player3rdParty: ["dandanplay", "VLC", "MXPlayer", "PotPlayer"],
    blockDownload: ["Infuse-Download"],
    infuse: {{
      direct: "Infuse-Direct",
      download: "Infuse-Download",
    }},
  }},
  "115": "115.com",
  ali: "aliyundrive.net",
  userIds: {{
    mediaPathMappingGroup01: [],
    allowInteractiveSearch: [],
  }},
  filePaths: {{
    mediaMountPath: [],
    redirectStrmLastLinkRule: [],
    mediaPathMappingGroup01: [],
  }},
}};

// 路由缓存配置
const routeCacheConfig = {{
  enable: true,
  enableL2: false,
  keyExpression: "r.uri:r.args.path:r.args.mediaIndex:r.args.partIndex",
}};

// 符号链接规则
const symlinkRule = [];

// 路由规则
const routeRule = [];

// 路径映射
const mediaPathMapping = [];

// Alist原始URL映射
const alistRawUrlMapping = [];

// 重定向Strm最后链接规则
const redirectStrmLastLinkRule = [
  [0, strHead.lanIp.map(s => "http://" + s)],
];

// 客户端自请求Alist规则
const clientSelfAlistRule = [
  [2, strHead["115"], alistPublicAddr],
];

// 导出配置
module.exports = {{
  plexHost,
  mediaMountPath,
  alistAddr,
  alistToken,
  alistSignEnable,
  alistSignExpireTime,
  alistPublicAddr,
  strHead,
  routeCacheConfig,
  symlinkRule,
  routeRule,
  mediaPathMapping,
  alistRawUrlMapping,
  redirectStrmLastLinkRule,
  clientSelfAlistRule,
}};
'''
        return config_template

    def __download_medialinker(self) -> bool:
        """
        下载MediaLinker程序
        """
        try:
            # 检查是否需要更新
            if self.__medialinker_path.exists() and not self._auto_update:
                current_version = self.__get_current_version()
                if current_version == "latest":
                    logger.info("MediaLinker已是最新版本，跳过下载")
                    return True
            
            repo_url = "https://github.com/chen3861229/embyExternalUrl"
            logger.info(f"正在下载MediaLinker程序...")
            
            # 创建临时目录
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # 下载源码
                archive_url = f"{repo_url}/archive/refs/heads/main.zip"
                response = requests.get(archive_url, timeout=30, proxies=settings.PROXY)
                response.raise_for_status()
                
                # 保存压缩包
                zip_file = temp_path / "medialinker.zip"
                with open(zip_file, 'wb') as f:
                    f.write(response.content)
                
                # 解压到临时目录
                with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                    zip_ref.extractall(temp_path)
                
                # 查找解压后的目录
                extracted_dirs = [d for d in temp_path.iterdir() if d.is_dir()]
                if not extracted_dirs:
                    raise Exception("解压失败，未找到程序目录")
                
                source_dir = extracted_dirs[0]
                
                # 备份现有目录
                if self.__medialinker_path.exists():
                    backup_path = self.__medialinker_path.parent / f"MediaLinker_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    shutil.move(str(self.__medialinker_path), str(backup_path))
                    logger.info(f"已备份现有版本到: {backup_path}")
                
                # 创建目标目录
                self.__medialinker_path.mkdir(parents=True, exist_ok=True)
                
                # 复制文件到目标目录
                for item in source_dir.rglob('*'):
                    if item.is_file():
                        relative_path = item.relative_to(source_dir)
                        target_path = self.__medialinker_path / relative_path
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, target_path)
                
                # 设置执行权限
                start_script = self.__medialinker_path / "start_server"
                if start_script.exists():
                    os.chmod(start_script, 0o755)
                
                entrypoint_script = self.__medialinker_path / "entrypoint"
                if entrypoint_script.exists():
                    os.chmod(entrypoint_script, 0o755)
            
            # 保存版本信息
            self.__save_version("latest")
            
            # 清理旧备份
            self.__cleanup_old_backups()
            
            logger.info("MediaLinker程序下载完成")
            return True
            
        except Exception as e:
            logger.error(f"下载MediaLinker程序失败: {str(e)}")
            # 如果有备份，尝试恢复
            backup_dirs = [d for d in self.__medialinker_path.parent.glob("MediaLinker_backup_*")]
            if backup_dirs:
                latest_backup = max(backup_dirs, key=lambda x: x.stat().st_mtime)
                if self.__medialinker_path.exists():
                    shutil.rmtree(self.__medialinker_path)
                shutil.move(str(latest_backup), str(self.__medialinker_path))
                logger.info(f"已从备份恢复: {latest_backup}")
            return False

    def __start_medialinker(self) -> bool:
        """
        启动MediaLinker服务
        """
        try:
            # 检查是否已经在运行
            if self.process and hasattr(self.process, 'is_running') and self.process.is_running():
                logger.info("MediaLinker服务已在运行中")
                return True
            
            # 停止现有进程
            self.stop_service()
            
            # 检查必要文件是否存在
            start_script = self.__medialinker_path / "start_server"
            if not start_script.exists():
                logger.error("start_server脚本不存在，请检查MediaLinker程序是否正确下载")
                return False
            
            # 创建必要的目录
            self.__logs_dir.mkdir(parents=True, exist_ok=True)
            
            # 构建环境变量
            env = os.environ.copy()
            env.update({
                "SERVER": "plex",
                "NGINX_PORT": str(self._nginx_port),
                "NGINX_SSL_PORT": str(self._nginx_ssl_port),
                "SSL_ENABLE": str(self._ssl_enable).lower(),
                "AUTO_UPDATE": str(self._auto_update).lower(),
            })
            
            if self._ssl_domain:
                env["SSL_DOMAIN"] = self._ssl_domain
            
            # 使用psutil启动进程，更好的进程管理
            self.process = psutil.Popen(
                ["./start_server"],
                env=env,
                cwd=str(self.__medialinker_path)
            )
            
            # 等待一小段时间检查进程是否成功启动
            import time
            time.sleep(2)
            
            if self.process.is_running():
                logger.info(f"MediaLinker服务启动成功，PID: {self.process.pid}，端口: {self._nginx_port}")
                return True
            else:
                logger.error("MediaLinker服务启动失败")
                return False
            
        except Exception as e:
            logger.error(f"启动MediaLinker服务失败: {str(e)}")
            return False

    def __check_service_health(self) -> bool:
        """
        检查服务健康状态
        """
        try:
            if not self.process or self.process.poll() is not None:
                return False
            
            # 检查端口是否监听
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', self._nginx_port))
            sock.close()
            
            return result == 0
        except Exception:
            return False
    
    def __setup_config_directory(self):
        """
        设置配置目录结构
        """
        try:
            # 创建nginx配置目录
            nginx_conf_d = self.__nginx_conf_path / "conf.d"
            nginx_conf_d.mkdir(parents=True, exist_ok=True)
            
            # 复制配置文件到nginx配置目录
            config_source = self.__config_path / "constant.js"
            config_target = nginx_conf_d / "constant.js"
            
            if config_source.exists():
                shutil.copy2(config_source, config_target)
                logger.info("配置文件已复制到nginx配置目录")
        except Exception as e:
            logger.error(f"设置配置目录失败: {str(e)}")

    def stop_service(self):
        """
        停止服务
        """
        try:
            # 停止调度器
            if self._scheduler:
                self._scheduler.remove_all_jobs()
                if self._scheduler.running:
                    self._scheduler.shutdown()
                self._scheduler = None
                
            # 停止MediaLinker进程
            if self.process:
                try:
                    if hasattr(self.process, 'is_running') and self.process.is_running():
                        # 优雅停止
                        self.process.terminate()
                        # 等待进程结束
                        try:
                            self.process.wait(timeout=10)
                        except psutil.TimeoutExpired:
                            # 强制杀死进程
                            logger.warning("进程未在规定时间内停止，强制终止")
                            self.process.kill()
                            self.process.wait(timeout=5)
                        
                        logger.info("MediaLinker服务已停止")
                    self.process = None
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # 进程已经不存在或无权限访问
                    self.process = None
                    logger.info("MediaLinker进程已清理")
                    
        except Exception as e:
            logger.error(f"停止MediaLinker服务失败: {str(e)}")

    def get_status(self) -> Tuple[bool, str]:
        """
        获取插件状态
        """
        try:
            if not self._enabled:
                return False, "插件未启用"
            
            if not self.process:
                return False, "MediaLinker服务未启动"
            
            # 检查进程是否还在运行
            try:
                if hasattr(self.process, 'is_running'):
                    if not self.process.is_running():
                        return False, "MediaLinker进程已停止"
                elif hasattr(self.process, 'poll'):
                    if self.process.poll() is not None:
                        return False, "MediaLinker进程已停止"
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return False, "MediaLinker进程不存在或无权限访问"
            
            # 检查服务健康状态
            health_status = self.__check_service_health()
            if health_status:
                status_msg = f"MediaLinker服务运行正常\n"
                status_msg += f"• HTTP端口: {self._nginx_port}\n"
                if self._ssl_enable:
                    status_msg += f"• HTTPS端口: {self._nginx_ssl_port}\n"
                status_msg += f"• 进程ID: {self.process.pid}\n"
                status_msg += f"• 媒体服务器: {self._plex_server or 'plex'}\n"
                if self._alist_addr:
                    status_msg += f"• Alist地址: {self._alist_addr}"
                return True, status_msg.strip()
            else:
                return False, f"MediaLinker服务端口 {self._nginx_port} 无响应"
                
        except Exception as e:
            return False, f"检查服务状态失败: {str(e)}"

    def __handle_event(self, event: Event):
        """
        处理事件
        """
        if not event.event_data:
            return
        
        action = event.event_data.get("action")
        if not action:
            return
        
        if action == "status":
            status, message = self.get_status()
            logger.info(f"MediaLinker状态查询: {message}")
        elif action == "restart":
            logger.info("收到重启MediaLinker命令")
            self.stop_service()
            if self._enabled:
                self.__run_service()

    def __cleanup_old_backups(self, keep_count: int = 3):
        """
        清理旧的备份文件，只保留最新的几个
        """
        try:
            backup_dirs = list(self.__medialinker_path.parent.glob("MediaLinker_backup_*"))
            if len(backup_dirs) > keep_count:
                # 按修改时间排序，保留最新的
                backup_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                for old_backup in backup_dirs[keep_count:]:
                    shutil.rmtree(old_backup, ignore_errors=True)
                    logger.info(f"已清理旧备份: {old_backup.name}")
        except Exception as e:
            logger.error(f"清理备份文件失败: {str(e)}")
    
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