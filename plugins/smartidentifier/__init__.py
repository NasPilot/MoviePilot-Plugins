import re
import threading
from typing import Any, Dict, List, Tuple, Optional
from datetime import datetime, timedelta

from app.core.context import MediaInfo
from app.core.event import Event, eventmanager
from app.core.meta.customization import CustomizationMatcher
from app.core.meta.words import WordsMatcher
from app.db.models.transferhistory import TransferHistory
from app.db.models.customwords import CustomWord
from app.db.session import get_db
from app.log import logger
from app.plugins import _PluginBase
from app.schemas.types import EventType, MediaType
from app.schemas import NotificationType

lock = threading.Lock()


class SmartIdentifier(_PluginBase):
    # 插件名称
    plugin_name = "智能识别词"
    # 插件描述
    plugin_desc = "增强媒体识别功能，从整理记录中提取识别词。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/NasPilot/MoviePilot-Plugins/main/icons/identifier.png"
    # 插件版本
    plugin_version = "1.0.0"
    # 插件作者
    plugin_author = "NasPilot"
    # 作者主页
    author_url = "https://github.com/NasPilot"
    # 插件配置项ID前缀
    plugin_config_prefix = "smartidentifier_"
    # 加载顺序
    plugin_order = 20
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _enabled: bool = False
    _notify: bool = False
    _auto_save: bool = False
    _scan_days: int = 7
    _min_count: int = 2
    _add_new_word: bool = False
    _new_word: str = ""
    _patterns: Dict[str, str] = {
        "season": r"S(\d{1,2})",
        "episode": r"E(\d{1,3})",
        "year": r"(19|20)\d{2}",
        "resolution": r"(720|1080|2160)[pP]",
        "source": r"BluRay|WEB-DL|HDTV|AMZN|NF|DSNP",
        "video_codec": r"x264|x265|H264|H265|HEVC|AVC",
        "audio_codec": r"AAC|AC3|DTS|DD|FLAC|TrueHD|Atmos"
    }
    
    # 缓存
    _history_cache = {}
    _word_cache = []

    def init_plugin(self, config: dict = None):
        """
        插件初始化
        """
        if not config:
            return
        try:
            self._enabled = config.get("enabled", False)
            self._notify = config.get("notify", False)
            self._auto_save = config.get("auto_save", False)
            self._scan_days = int(config.get("scan_days", 7))
            self._min_count = int(config.get("min_count", 2))
            self._add_new_word = config.get("add_new_word", False)
            self._new_word = config.get("new_word", "")
            
            # 更新正则表达式模式
            for key in self._patterns.keys():
                pattern = config.get(key)
                if pattern:
                    try:
                        # 验证正则表达式有效性
                        re.compile(pattern)
                        self._patterns[key] = pattern
                    except re.error as e:
                        logger.error(f"正则表达式 {key} 无效: {str(e)}")
        except Exception as e:
            logger.error(f"插件初始化出错: {str(e)}")

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        """
        注册命令
        """
        return [
            {
                "cmd": "/extract_identifiers",
                "title": "提取识别词",
                "desc": "从媒体整理记录中提取识别词",
                "category": "MEDIASERVER",
                "data": []
            },
            {
                "cmd": "/save_identifiers",
                "title": "保存识别词",
                "desc": "将提取的识别词保存到自定义识别词表",
                "category": "MEDIASERVER",
                "data": []
            }
        ]

    def get_api(self) -> List[Dict[str, Any]]:
        """
        注册API接口
        """
        return [
            {
                "path": "/extract",
                "endpoint": self.extract_identifiers,
                "methods": ["GET"],
                "summary": "提取识别词",
                "description": "从媒体整理记录中提取识别词"
            },
            {
                "path": "/save",
                "endpoint": self.save_identifiers,
                "methods": ["GET"],
                "summary": "保存识别词",
                "description": "将提取的识别词保存到自定义识别词表"
            }
        ]

    def get_service(self) -> List[Dict[str, Any]]:
        return []

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        获取配置表单
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
                                        }
                                    }
                                ]
                            },
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
                                            'model': 'notify',
                                            'label': '发送通知',
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
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'auto_save',
                                            'label': '自动保存识别词',
                                            'hint': '自动将提取的识别词保存到自定义识别词表'
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VSlider',
                                        'props': {
                                            'model': 'scan_days',
                                            'label': '扫描天数',
                                            'min': 1,
                                            'max': 30,
                                            'step': 1,
                                            'hint': '扫描最近几天的整理记录'
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
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VSlider',
                                        'props': {
                                            'model': 'min_count',
                                            'label': '最小出现次数',
                                            'min': 1,
                                            'max': 10,
                                            'step': 1,
                                            'hint': '识别词至少出现几次才会被提取'
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
                                            'model': 'season',
                                            'label': '季数匹配规则',
                                            'placeholder': '默认：S(\\d{1,2})'
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
                                            'model': 'episode',
                                            'label': '集数匹配规则',
                                            'placeholder': '默认：E(\\d{1,3})'
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
                                            'model': 'year',
                                            'label': '年份匹配规则',
                                            'placeholder': '默认：(19|20)\\d{2}'
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
                                            'model': 'resolution',
                                            'label': '分辨率匹配规则',
                                            'placeholder': '默认：(720|1080|2160)[pP]'
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
                                            'model': 'source',
                                            'label': '片源匹配规则',
                                            'placeholder': '默认：BluRay|WEB-DL|HDTV|AMZN|NF|DSNP'
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
                                            'model': 'video_codec',
                                            'label': '视频编码匹配规则',
                                            'placeholder': '默认：x264|x265|H264|H265|HEVC|AVC'
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
                                            'model': 'audio_codec',
                                            'label': '音频编码匹配规则',
                                            'placeholder': '默认：AAC|AC3|DTS|DD|FLAC|TrueHD|Atmos'
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
            "notify": True,
            "auto_save": False,
            "scan_days": 7,
            "min_count": 2,
            "season": "",
            "episode": "",
            "year": "",
            "resolution": "",
            "source": "",
            "video_codec": "",
            "audio_codec": ""
        }

    def get_page(self) -> List[dict]:
        """
        获取页面
        """
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
                                'component': 'VCard',
                                'props': {
                                    'title': '智能识别词'
                                },
                                'content': [
                                    {
                                        'component': 'VCardText',
                                        'content': [
                                            {
                                                'component': 'VBtn',
                                                'props': {
                                                    'color': 'primary',
                                                    'text': '提取识别词',
                                                    'onClick': 'extractIdentifiers'
                                                }
                                            },
                                            {
                                                'component': 'VBtn',
                                                'props': {
                                                    'color': 'success',
                                                    'text': '保存识别词',
                                                    'class': 'ml-2',
                                                    'onClick': 'saveIdentifiers'
                                                }
                                            }
                                        ]
                                    },
                                    {
                                        'component': 'VDivider'
                                    },
                                    {
                                        'component': 'VCardText',
                                        'content': [
                                            {
                                                'component': 'VTable',
                                                'props': {
                                                    'headers': [
                                                        {
                                                            'text': '识别词',
                                                            'value': 'word'
                                                        },
                                                        {
                                                            'text': '类型',
                                                            'value': 'type'
                                                        },
                                                        {
                                                            'text': '出现次数',
                                                            'value': 'count'
                                                        }
                                                    ],
                                                    'items': '{{ extractedWords }}'
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

    def get_page_data(self) -> Dict[str, Any]:
        """
        获取页面数据
        """
        return {
            "extractedWords": self._word_cache
        }

    def get_page_events(self) -> Dict[str, Any]:
        """
        获取页面事件
        """
        return {
            "extractIdentifiers": self.extract_identifiers,
            "saveIdentifiers": self.save_identifiers
        }

    @eventmanager.register(EventType.TransferComplete)
    def on_transfer_complete(self, event: Event):
        """
        监听转移完成事件，自动提取识别词
        """
        if not self._enabled:
            return
            
        try:
            # 提取识别词
            result = self.extract_identifiers()
            if result.get("code") != 0:
                logger.error(f"自动提取识别词失败: {result.get('msg')}")
                return
                
            # 自动保存识别词
            if self._auto_save:
                save_result = self.save_identifiers()
                if save_result.get("code") != 0:
                    logger.error(f"自动保存识别词失败: {save_result.get('msg')}")
        except Exception as e:
            logger.error(f"处理转移完成事件出错: {str(e)}")

    def extract_identifiers(self, *args, **kwargs) -> Dict[str, Any]:
        """
        从媒体整理记录中提取识别词
        """
        if not self._enabled:
            return {"code": 1, "msg": "插件未启用"}
            
        try:
            with lock:
                with get_db() as db:
                    # 获取最新的的一条整理记录
                    latest_history = db.query(TransferHistory).order_by(
                        TransferHistory.date.desc()
                    ).first()

                    if not latest_history:
                        return {"code": 1, "msg": "未找到整理记录"}

                    # 提取词频统计
                    word_stats = {}
                    
                    # 获取源文件名
                    src_filename = latest_history.src
                    if not src_filename:
                        return {"code": 1, "msg": "未找到源文件名"}
                        
                    # 使用正则匹配各类型识别词
                    for pattern_type, pattern in self._patterns.items():
                        matches = re.finditer(pattern, src_filename, re.IGNORECASE)
                        for match in matches:
                            word = match.group()
                            if not word:
                                continue
                                
                            # 统计词频
                            if word not in word_stats:
                                word_stats[word] = {
                                    "word": word,
                                    "type": self._get_word_type(pattern_type),
                                    "count": 1,
                                    "pattern_type": pattern_type
                                }

                    # 添加新增识别词
                    if self._add_new_word and self._new_word:
                        word_stats[self._new_word] = {
                            "word": self._new_word,
                            "type": 0,  # 其他类型
                            "count": 1,
                            "pattern_type": "custom"
                        }
                    
                    # 转换为列表
                    words_list = list(word_stats.values())
                    
                    # 更新缓存
                    self._word_cache = words_list

                    # 发送通知
                    if self._notify:
                        self.post_message(
                            mtype=NotificationType.Info,
                            title="智能识别词提取完成",
                            text=f"从最新记录中提取到 {len(words_list)} 个识别词"
                        )

                    return {"code": 0, "msg": "提取成功", "data": words_list}

        except Exception as e:
            logger.error(f"提取识别词出错: {str(e)}")
            return {"code": 1, "msg": f"提取识别词出错: {str(e)}"}

    def save_identifiers(self, *args, **kwargs) -> Dict[str, Any]:
        """
        将提取的识别词保存到自定义识别词表
        """
        if not self._enabled:
            return {"code": 1, "msg": "插件未启用"}
            
        if not self._word_cache:
            return {"code": 1, "msg": "请先提取识别词"}
            
        try:
            with lock:
                with get_db() as db:
                    # 获取现有的自定义识别词
                    existing_words = db.query(CustomWord).all()
                    existing_word_texts = [word.replaced for word in existing_words]
                    
                    # 添加新的识别词
                    added_count = 0
                    for word_info in self._word_cache:
                        word = word_info["word"]
                        if word in existing_word_texts:
                            continue
                            
                        # 创建新的自定义识别词
                        new_word = CustomWord(
                            replaced=word,
                            replace=word,  # 保持原词
                            front="",
                            back="",
                            offset=0,
                            type=word_info["type"],
                            group_id=0,
                            season=0,
                            enabled=True,
                            regex=False,
                            help=f"由智能识别词插件添加 - {word_info['pattern_type']}"
                        )
                        db.add(new_word)
                        added_count += 1
                    
                    # 提交更改
                    db.commit()
                    
                    # 发送通知
                    if self._notify:
                        self.post_message(
                            mtype=NotificationType.Info,
                            title="智能识别词保存完成",
                            text=f"成功添加 {added_count} 个自定义识别词"
                        )
                    
                    return {"code": 0, "msg": f"保存成功，新增{added_count}个识别词"}
                    
        except Exception as e:
            logger.error(f"保存识别词出错: {str(e)}")
            return {"code": 1, "msg": f"保存识别词出错: {str(e)}"}

    def _get_word_type(self, pattern_type: str) -> int:
        """
        获取识别词类型
        0: 其他, 1: 分辨率, 2: 制作组/字幕组, 3: 视频编码, 4: 音频编码
        """
        type_map = {
            "resolution": 1,
            "video_codec": 3,
            "audio_codec": 4
        }
        return type_map.get(pattern_type, 0)
