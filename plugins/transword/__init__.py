import re
from typing import Any, List, Dict, Tuple, Optional
from pathlib import Path

from app.core.config import settings
from app.core.plugin import PluginBase, _PluginBase
from app.log import logger
from app.schemas import NotificationType
from app.schemas.types import EventType


class TransWordPlugin(_PluginBase):
    # 插件名称
    plugin_name = "识别词生成器"
    # 插件描述
    plugin_desc = "根据手动整理时填写的电视剧参数生成自定义识别词，支持集数偏移、替换词等功能。"
    # 插件图标
    plugin_icon = "words.png"
    # 插件版本
    plugin_version = "0.1"
    # 插件作者
    plugin_author = "NasPilot"
    # 作者主页
    author_url = "https://github.com/NasPilot"
    # 插件配置项ID前缀
    plugin_config_prefix = "transword_"
    # 加载顺序
    plugin_order = 20
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _enabled = False
    _auto_generate = False
    _custom_words = []

    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled")
            self._auto_generate = config.get("auto_generate")
            self._custom_words = config.get("custom_words") or []

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        """
        定义远程控制命令
        :return: 命令关键字、事件、描述、附带数据
        """
        return [
            {
                "cmd": "/transword",
                "event": EventType.PluginAction,
                "desc": "生成识别词",
                "category": "",
                "data": {
                    "action": "generate_word"
                }
            }
        ]

    def get_api(self) -> List[Dict[str, Any]]:
        return [
            {
                "path": "/generate_word",
                "endpoint": self.generate_word,
                "methods": ["POST"],
                "summary": "生成识别词",
                "description": "根据电视剧参数生成自定义识别词",
            }
        ]

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据结构
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
                                            'model': 'auto_generate',
                                            'label': '自动生成识别词',
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
                                        'component': 'VTextarea',
                                        'props': {
                                            'model': 'custom_words',
                                            'label': '自定义识别词',
                                            'placeholder': '每行一个识别词，支持以下格式：\n1. 屏蔽词\n2. 被替换词 => 替换词\n3. 前定位词 <> 后定位词 >> 偏移量（EP）\n4. 被替换词 => 替换词 && 前定位词 <> 后定位词 >> 偏移量（EP）',
                                            'rows': 10
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
                                            'text': '插件功能说明：\n1. 根据手动整理时填写的电视剧参数自动生成识别词\n2. 支持集数偏移、替换词、屏蔽词等多种格式\n3. 可通过API接口或命令行生成识别词\n4. 生成的识别词可直接添加到系统自定义识别词中'
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
            "auto_generate": False,
            "custom_words": ""
        }

    def get_page(self) -> List[dict]:
        """
        拼装插件详情页面，需要返回页面配置，同时附带数据
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
                                'content': [
                                    {
                                        'component': 'VCardTitle',
                                        'props': {
                                            'text': '识别词生成器'
                                        }
                                    },
                                    {
                                        'component': 'VCardText',
                                        'content': [
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
                                                                        'component': 'VTextField',
                                                                        'props': {
                                                                            'model': 'title',
                                                                            'label': '电视剧标题',
                                                                            'placeholder': '请输入电视剧标题'
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
                                                                        'component': 'VTextField',
                                                                        'props': {
                                                                            'model': 'season',
                                                                            'label': '季号',
                                                                            'placeholder': '请输入季号',
                                                                            'type': 'number'
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
                                                                        'component': 'VTextField',
                                                                        'props': {
                                                                            'model': 'episode_format',
                                                                            'label': '集数定位格式',
                                                                            'placeholder': '如：{ep}'
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
                                                                        'component': 'VTextField',
                                                                        'props': {
                                                                            'model': 'episode_detail',
                                                                            'label': '指定集数',
                                                                            'placeholder': '如：1,2,3 或 1-10'
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
                                                                        'component': 'VTextField',
                                                                        'props': {
                                                                            'model': 'episode_part',
                                                                            'label': '分集标识',
                                                                            'placeholder': '如：Part1, Part2'
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
                                                                        'component': 'VTextField',
                                                                        'props': {
                                                                            'model': 'episode_offset',
                                                                            'label': '集数偏移',
                                                                            'placeholder': '如：+10, -5, EP*2'
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
                                                                        'component': 'VBtn',
                                                                        'props': {
                                                                            'text': '生成识别词',
                                                                            'color': 'primary',
                                                                            'variant': 'elevated',
                                                                            'onclick': 'generateWord()'
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
                                                                        'component': 'VTextarea',
                                                                        'props': {
                                                                            'model': 'result',
                                                                            'label': '生成的识别词',
                                                                            'readonly': True,
                                                                            'rows': 5
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
                        ]
                    }
                ]
            }
        ]

    def generate_word(self, **kwargs) -> Dict[str, Any]:
        """
        生成识别词API接口
        """
        try:
            # 获取参数
            title = kwargs.get('title', '')
            season = kwargs.get('season')
            episode_format = kwargs.get('episode_format', '')
            episode_detail = kwargs.get('episode_detail', '')
            episode_part = kwargs.get('episode_part', '')
            episode_offset = kwargs.get('episode_offset', '')
            
            # 生成识别词
            words = self._generate_recognition_words(
                title=title,
                season=season,
                episode_format=episode_format,
                episode_detail=episode_detail,
                episode_part=episode_part,
                episode_offset=episode_offset
            )
            
            return {
                "success": True,
                "data": {
                    "words": words
                },
                "message": "识别词生成成功"
            }
        except Exception as e:
            logger.error(f"生成识别词失败：{str(e)}")
            return {
                "success": False,
                "message": f"生成识别词失败：{str(e)}"
            }

    def _generate_recognition_words(self, title: str, season: Optional[int] = None,
                                   episode_format: str = '', episode_detail: str = '',
                                   episode_part: str = '', episode_offset: str = '') -> List[str]:
        """
        根据电视剧参数生成识别词
        """
        words = []
        
        if not title:
            return words
        
        # 基础标题处理
        base_title = title.strip()
        
        # 1. 生成季号相关的识别词
        if season:
            # 季号替换词
            season_patterns = [
                f"第{season}季",
                f"S{season:02d}",
                f"Season {season}",
                f"第{season}部"
            ]
            
            for pattern in season_patterns:
                if pattern not in base_title:
                    words.append(f"{base_title} => {base_title} {pattern}")
        
        # 2. 生成集数偏移识别词
        if episode_format and episode_offset:
            # 解析集数定位格式
            front_word, back_word = self._parse_episode_format(episode_format)
            if front_word and back_word:
                offset_word = self._format_offset(episode_offset)
                words.append(f"{front_word} <> {back_word} >> {offset_word}")
        
        # 3. 生成指定集数的识别词
        if episode_detail:
            # 处理集数范围或列表
            episodes = self._parse_episode_detail(episode_detail)
            if episodes:
                # 为每个集数生成识别词
                for ep in episodes:
                    if episode_format:
                        front_word, back_word = self._parse_episode_format(episode_format)
                        if front_word and back_word:
                            words.append(f"{front_word} <> {back_word} >> EP")
        
        # 4. 生成分集标识相关识别词
        if episode_part:
            # 分集标识替换
            part_patterns = [
                f"Part{episode_part}",
                f"part{episode_part}",
                f"第{episode_part}部分",
                f"P{episode_part}"
            ]
            
            for pattern in part_patterns:
                words.append(f"{pattern} => ")
        
        # 5. 生成常见的屏蔽词
        common_noise_words = [
            "4K", "1080P", "720P", "BluRay", "WEB-DL", "HDRip",
            "x264", "x265", "HEVC", "H264", "H265",
            "AAC", "AC3", "DTS", "Atmos",
            "中英双字", "中字", "英字", "双语",
            "完整版", "导演剪辑版", "加长版", "未删减版"
        ]
        
        for noise in common_noise_words:
            if noise.lower() in base_title.lower():
                words.append(noise)
        
        # 6. 生成标题清理识别词
        title_clean_patterns = [
            r"\[.*?\]",  # 方括号内容
            r"\(.*?\)",  # 圆括号内容
            r"【.*?】",   # 中文方括号内容
            r"（.*?）"    # 中文圆括号内容
        ]
        
        for pattern in title_clean_patterns:
            if re.search(pattern, base_title):
                words.append(f"{pattern} => ")
        
        return words
    
    def _parse_episode_format(self, episode_format: str) -> Tuple[str, str]:
        """
        解析集数定位格式，提取前后定位词
        """
        if not episode_format:
            return "", ""
        
        # 查找 {ep} 或类似的占位符
        pattern = r'(.*)\{\w+\}(.*)'
        match = re.match(pattern, episode_format)
        
        if match:
            front = match.group(1).strip()
            back = match.group(2).strip()
            return front, back
        
        return "", ""
    
    def _parse_episode_detail(self, episode_detail: str) -> List[int]:
        """
        解析集数详情，支持范围和列表
        """
        episodes = []
        
        if not episode_detail:
            return episodes
        
        # 处理逗号分隔的集数列表
        if ',' in episode_detail:
            for ep in episode_detail.split(','):
                ep = ep.strip()
                if ep.isdigit():
                    episodes.append(int(ep))
                elif '-' in ep:
                    # 处理范围
                    start, end = ep.split('-')
                    if start.strip().isdigit() and end.strip().isdigit():
                        episodes.extend(range(int(start.strip()), int(end.strip()) + 1))
        
        # 处理范围格式
        elif '-' in episode_detail:
            start, end = episode_detail.split('-')
            if start.strip().isdigit() and end.strip().isdigit():
                episodes.extend(range(int(start.strip()), int(end.strip()) + 1))
        
        # 处理单个集数
        elif episode_detail.isdigit():
            episodes.append(int(episode_detail))
        
        return episodes
    
    def _format_offset(self, episode_offset: str) -> str:
        """
        格式化集数偏移
        """
        if not episode_offset:
            return "EP"
        
        # 如果已经包含EP，直接返回
        if "EP" in episode_offset.upper():
            return episode_offset
        
        # 如果是数字偏移，添加EP前缀
        if episode_offset.startswith(('+', '-')):
            return f"EP{episode_offset}"
        elif episode_offset.isdigit():
            return f"EP+{episode_offset}"
        else:
            return f"EP{episode_offset}"
    
    def stop_service(self):
        """
        退出插件
        """
        pass