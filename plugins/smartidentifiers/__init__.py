import re
from typing import List, Dict, Any, Optional, Tuple

from app.core.event import eventmanager, Event
from app.db.plugindata_oper import PluginDataOper
from app.log import logger
from app.plugins import _PluginBase
from app.schemas import NotificationType
from app.schemas.types import EventType, ChainEventType


class SmartIdentifiers(_PluginBase):
    # 插件名称
    plugin_name = "智能识别词"
    # 插件描述
    plugin_desc = "自动从整理记录中提取识别词，辅助用户进行媒体识别。"
    # 插件图标
    plugin_icon = "identifiers.png"
    # 插件版本
    plugin_version = "0.0.1"
    # 插件作者
    plugin_author = "NasPilot"
    # 作者主页
    author_url = "https://github.com/NasPilot"
    # 插件配置项ID前缀
    plugin_config_prefix = "smartidentifiers_"
    # 加载顺序
    plugin_order = 200
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _enabled: bool = False
    _notify: bool = False
    _save_data: bool = False
    _auto_apply: bool = False
    _patterns: Dict[str, str] = {
        "season": r"S(\d{1,2})",
        "episode": r"E(\d{1,3})",
        "year": r"(19|20)\d{2}",
        "resolution": r"(720|1080|2160)[pP]",
        "source": r"BluRay|WEB-DL|HDTV|AMZN|NF|DSNP",
        "video_codec": r"x264|x265|H264|H265|HEVC|AVC",
        "audio_codec": r"AAC|AC3|DTS|DD|FLAC|TrueHD|Atmos"
    }
    
    # 数据库操作对象
    _db = None
    # 历史识别结果缓存
    _history_cache = {}

    def init_plugin(self, config: dict = None):
        self._db = PluginDataOper()
        if config:
            self._enabled = config.get("enabled")
            self._notify = config.get("notify")
            self._save_data = config.get("save_data")
            self._auto_apply = config.get("auto_apply")
            # 更新正则表达式模式
            for key in self._patterns.keys():
                if config.get(key):
                    self._patterns[key] = config.get(key)
        
        # 加载历史识别结果
        if self._save_data:
            self._history_cache = self._db.get_data(self.plugin_name, "history_cache") or {}

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        pass

    def get_service(self) -> List[Dict[str, Any]]:
        return []

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
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
            "save_data": False,
            "auto_apply": False,
            "season": "",
            "episode": "",
            "year": "",
            "resolution": "",
            "source": "",
            "video_codec": "",
            "audio_codec": ""
        }

    def get_page(self) -> List[dict]:
        pass

    @eventmanager.register(EventType.MediaRecognize)
    def recognize_media(self, event: Event):
        """识别媒体信息并提取关键词"""
        if not self._enabled:
            return
            
        media_info = event.event_data
        if not media_info:
            return
            
        # 提取识别词
        keywords = self._extract_keywords(media_info)
        
        # 保存识别历史
        if self._save_data and keywords:
            media_key = self._get_media_key(media_info)
            if media_key:
                self._history_cache[media_key] = keywords
                self._db.save(self.plugin_name, "history_cache", self._history_cache)
        
        # 自动应用识别词
        if self._auto_apply and keywords:
            self._apply_identifiers(keywords)
        
        # 发送通知
        if self._notify and keywords:
            self.post_message(
                mtype=NotificationType.MediaServer,
                title="【智能识别词】",
                text=f"从媒体信息中提取到识别词：{', '.join(keywords)}"
            )
            
        return keywords

    def _get_media_key(self, media_info: Dict[str, Any]) -> str:
        """
        生成媒体唯一标识
        """
        tmdb_id = media_info.get("tmdbid")
        media_type = media_info.get("type")
        season = media_info.get("season")
        
        if not tmdb_id or not media_type:
            return None
            
        key = f"{tmdb_id}_{media_type}"
        if season:
            key += f"_S{season}"
            
        return key

    def _apply_identifiers(self, identifiers: List[str]):
        """
        将识别词应用到系统配置中
        """
        try:
            # 触发识别词转换事件
            event_data = {
                "identifiers": identifiers
            }
            eventmanager.send_event(ChainEventType.MediaRecognizeConvert, event_data)
            logger.info(f"已自动应用识别词：{', '.join(identifiers)}")
        except Exception as e:
            logger.error(f"应用识别词失败：{str(e)}")

    def _generate_identifier_rules(self, media_info: Dict[str, Any]) -> List[str]:
        """生成识别词规则"""
        rules = []
        
        # 基础信息
        tmdb_id = media_info.get("tmdbid")
        media_type = media_info.get("type")
        season = media_info.get("season")
        episode = media_info.get("episode")
        title = media_info.get("title", "")
        file_name = media_info.get("file_name", "")
        year = media_info.get("year", "")
        
        if not tmdb_id or not media_type:
            return rules
            
        # 1. 生成TMDB ID规则
        rule = f"{{[tmdbid={tmdb_id};type={media_type}"
        if season:
            rule += f";s={season}"
        if episode:
            rule += f";e={episode}"
        rule += "]}"
        rules.append(rule)
        
        # 2. 生成标题替换规则
        if title:
            rule = f"{title} => {{[tmdbid={tmdb_id};type={media_type}"
            if season:
                rule += f";s={season}"
            if episode:
                rule += f";e={episode}"
            rule += "]}"
            rules.append(rule)
        
        # 3. 生成定位词规则
        if season and episode:
            # 处理常见的季集格式 (S01E01, S1E1, 第1季第1集等)
            patterns = [
                rf"S{season:02d}E{episode:02d}",
                rf"S{season}E{episode}",
                rf"第{season}季第{episode}集",
                rf"Season {season} Episode {episode}"
            ]
            
            for pattern in patterns:
                match = re.search(pattern, file_name, re.I)
                if match:
                    prefix = file_name[:match.start()].strip()
                    suffix = file_name[match.end():].strip()
                    if prefix or suffix:
                        rule = f"{prefix} <> {suffix} >> {episode}"
                        rules.append(rule)
        
        # 4. 生成年份修正规则
        year_match = re.search(r"(19|20)\d{2}", file_name)
        if year_match and year_match.group() != year:
            rules.append(f"{year_match.group()} => {year}")
        
        # 5. 生成分辨率修正规则
        if "2160" in file_name:
            rules.append("2160[pP] => 4K")
        elif "1080" in file_name:
            rules.append("1080[pP] => 1080p")
        elif "720" in file_name:
            rules.append("720[pP] => 720p")
            
        # 6. 生成来源修正规则
        sources = ["BluRay", "WEB-DL", "HDTV", "AMZN", "NF", "DSNP"]
        for source in sources:
            if source in file_name:
                rules.append(f"{source} => {source}")
                
        return rules

    def _extract_keywords(self, media_info: Dict[str, Any]) -> List[str]:
        """从媒体信息中提取识别词"""
        keywords = []
        
        # 检查历史缓存
        if self._save_data:
            media_key = self._get_media_key(media_info)
            if media_key and media_key in self._history_cache:
                logger.info(f"使用历史识别结果: {media_key}")
                return self._history_cache[media_key]
        
        # 从标题提取基本信息
        if media_info.get("title"):
            title = media_info.get("title")
            # 提取年份
            year_match = re.search(self._patterns["year"], title)
            if year_match:
                keywords.append(year_match.group())
            # 提取季数
            season_match = re.search(self._patterns["season"], title, re.I)
            if season_match:
                keywords.append(f"S{season_match.group(1)}")
            # 提取集数
            episode_match = re.search(self._patterns["episode"], title, re.I)
            if episode_match:
                keywords.append(f"E{episode_match.group(1)}")
                    
        # 从文件名提取技术信息
        if media_info.get("file_name"):
            filename = media_info.get("file_name")
            # 提取分辨率
            resolution_match = re.search(self._patterns["resolution"], filename, re.I)
            if resolution_match:
                if "2160" in resolution_match.group():
                    keywords.append("4K")
                else:
                    keywords.append(resolution_match.group())
            
            # 提取片源
            source_match = re.search(self._patterns["source"], filename, re.I)
            if source_match:
                keywords.append(source_match.group())
                
            # 提取视频编码
            video_codec_match = re.search(self._patterns["video_codec"], filename, re.I)
            if video_codec_match:
                keywords.append(video_codec_match.group())
                
            # 提取音频编码
            audio_codec_match = re.search(self._patterns["audio_codec"], filename, re.I)
            if audio_codec_match:
                keywords.append(audio_codec_match.group())
        
        # 生成识别词规则
        identifier_rules = self._generate_identifier_rules(media_info)
        keywords.extend(identifier_rules)
                
        return sorted(list(set(keywords)))

    def stop_service(self):
        """停止插件服务"""
        # 保存缓存数据
        if self._save_data and self._history_cache:
            self._db.save(self.plugin_name, "history_cache", self._history_cache)
