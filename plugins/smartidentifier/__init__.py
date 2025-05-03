import copy
import threading
from typing import Any, Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

from jinja2 import Template

from app.core.context import MediaInfo
from app.core.event import Event, eventmanager
from app.core.meta.customization import CustomizationMatcher
from app.core.meta.words import WordsMatcher
from app.log import logger
from app.plugins import _PluginBase
from app.schemas.event import TransferRenameEventData
from app.schemas.types import ChainEventType

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
    plugin_order = 218
    # 可使用的用户级别
    auth_level = 1

    # 线程锁
    _lock = threading.Lock()
    # 线程池
    _thread_pool = ThreadPoolExecutor(max_workers=4)
    # 缓存装饰器
    _cache = lru_cache(maxsize=1000)

    def __init__(self):
        super().__init__()
        self._enabled = False
        self._separator = None
        self._separator_types = None
        self._field_separators = None
        self._word_replacements = []
        self._template_groups = {}
        self._custom_separator = "@"
        self._cache_enabled = True
        self._cache_ttl = 3600

    def init_plugin(self, config: dict = None):
        """初始化插件"""
        if not config:
            return

        try:
            with self._lock:
                self._enabled = config.get("enabled", False)
                self._separator = config.get("separator")
                self._separator_types = config.get("separator_types")
                self._word_replacements = self.__parse_replacement_rules(config.get("word_replacements"))
                self._template_groups = self.__parse_template_groups(config.get("template_groups"))
                self._custom_separator = config.get("custom_separator", "@")
                self._cache_enabled = config.get("cache_enabled", True)
                self._cache_ttl = config.get("cache_ttl", 3600)
                
                # 初始化自定义匹配器
                CustomizationMatcher().custom_separator = self._custom_separator
                
                # 清除缓存
                self._clear_cache()
                
                logger.info("插件初始化完成")
        except Exception as e:
            logger.error(f"插件初始化失败: {str(e)}")
            raise

    def _clear_cache(self):
        """清除缓存"""
        self._cache.cache_clear()

    @_cache
    def _get_template(self, template_string: str) -> Template:
        """获取模板对象（带缓存）"""
        return Template(template_string)

    @eventmanager.register(ChainEventType.TransferRename)
    def handle_transfer_rename(self, event: Event):
        """处理重命名事件"""
        if not event or not event.event_data:
            return

        event_data: TransferRenameEventData = event.event_data
        
        if event_data.updated:
            logger.debug("该事件已被其他事件处理器处理，跳过后续操作")
            return

        try:
            # 使用线程池处理重命名任务
            future = self._thread_pool.submit(self._process_rename, event_data)
            future.add_done_callback(self._handle_rename_result)
        except Exception as e:
            logger.error(f"处理重命名事件失败: {str(e)}")

    def _process_rename(self, event_data: TransferRenameEventData) -> Tuple[bool, str]:
        """处理重命名逻辑"""
        try:
            template_string = event_data.template_string
            rename_dict = copy.deepcopy(event_data.rename_dict)
            
            # 获取媒体信息
            mediainfo: MediaInfo = rename_dict.get("__mediainfo__")
            if mediainfo:
                # 处理二级分类模板
                if category := mediainfo.category:
                    if category_template := self._template_groups.get(category):
                        template_string = category_template
                        logger.debug(f"应用二级分类模板: {category} -> {template_string}")
                
                # 处理TMDB模板
                if tmdb_id := mediainfo.tmdb_id:
                    if tmdb_template := self._template_groups.get(str(tmdb_id)):
                        template_string = tmdb_template
                        logger.debug(f"应用TMDB模板: {tmdb_id} -> {template_string}")

            # 执行重命名
            updated_str = self.rename(template_string, rename_dict) or event_data.render_str
            
            # 应用词语替换
            if self._word_replacements:
                updated_str, applied_words = WordsMatcher().prepare(
                    title=updated_str,
                    custom_words=self._word_replacements
                )
                logger.debug(f"应用词语替换: {applied_words}")

            return updated_str != event_data.render_str, updated_str
            
        except Exception as e:
            logger.error(f"处理重命名失败: {str(e)}")
            return False, event_data.render_str

    def _handle_rename_result(self, future):
        """处理重命名结果"""
        try:
            updated, new_str = future.result()
            if updated:
                event_data = future.event_data
                event_data.updated_str = new_str
                event_data.updated = True
                event_data.source = self.plugin_name
                logger.info(f"重命名完成: {event_data.render_str} -> {new_str}")
        except Exception as e:
            logger.error(f"处理重命名结果失败: {str(e)}")

    def rename(self, template_string: str, rename_dict: dict) -> Optional[str]:
        """执行重命名"""
        if not self._separator_types or not self._separator:
            return None

        try:
            # 更新字段值
            updated = False
            for field, value in rename_dict.items():
                if field not in self._separator_types:
                    continue
                    
                if new_value := self.modify_field(field, value, self._separator_types):
                    rename_dict[field] = new_value
                    updated = True
                    logger.debug(f"更新字段: {field} -> {new_value}")

            if not updated:
                return None

            # 渲染模板
            template = self._get_template(template_string)
            return template.render(rename_dict)
            
        except Exception as e:
            logger.error(f"重命名失败: {str(e)}")
            return None

    def modify_field(self, field: str, value: str, separator_types: list) -> Optional[str]:
        """修改字段值"""
        if not value or field not in separator_types:
            return None

        try:
            if isinstance(value, str):
                parts = value.split()
                separator = self._field_separators.get(field, self._separator) if self._field_separators else self._separator
                new_value = separator.join(parts) if separator else value
                return new_value if new_value != value else None
        except Exception as e:
            logger.error(f"修改字段失败: {field} -> {str(e)}")
            
        return None

    @staticmethod
    def __parse_replacement_rules(replacement_str: str) -> List[str]:
        """解析替换规则"""
        if not replacement_str:
            return []

        try:
            return [
                line.strip() for line in replacement_str.splitlines()
                if line.strip() and not line.startswith("#")
            ]
        except Exception as e:
            logger.error(f"解析替换规则失败: {str(e)}")
            return []

    @staticmethod
    def __parse_template_groups(template_group_str: Optional[str]) -> Dict[str, str]:
        """解析模板组"""
        if not template_group_str:
            return {}

        try:
            return {
                category.strip(): template.strip()
                for line in template_group_str.split("\n")
                if not line.startswith("#") and (parts := line.split(":", 1)) and len(parts) == 2
                for category, template in [parts]
            }
        except Exception as e:
            logger.error(f"解析模板组失败: {str(e)}")
            return {}

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """获取插件配置表单"""
        return [
            {
                'component': 'VForm',
                'content': [
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 6},
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'enabled',
                                            'label': '启用插件',
                                            'hint': '开启后插件将处于激活状态',
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
                                'props': {'cols': 12, 'md': 6},
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'separator',
                                            'label': '默认分隔符',
                                            'hint': '请输入默认分隔符，如：. - _ 空格',
                                            'persistent-hint': True
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 6},
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'custom_separator',
                                            'label': '自定义占位符分隔符',
                                            'hint': '请输入 customization 的分隔符，如：. - _ 空格，默认为 @',
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
                                'props': {'cols': 12},
                                'content': [
                                    {
                                        'component': 'VSelect',
                                        'props': {
                                            'multiple': True,
                                            'chips': True,
                                            'clearable': True,
                                            'model': 'separator_types',
                                            'label': '分隔符适用范围',
                                            'items': [
                                                {'title': 'title', 'value': 'title'},
                                                {'title': 'en_title', 'value': 'en_title'},
                                                {'title': 'original_title', 'value': 'original_title'},
                                                {'title': 'name', 'value': 'name'},
                                                {'title': 'en_name', 'value': 'en_name'},
                                                {'title': 'original_name', 'value': 'original_name'},
                                                {'title': 'resourceType', 'value': 'resourceType'},
                                                {'title': 'effect', 'value': 'effect'},
                                                {'title': 'edition', 'value': 'edition'},
                                                {'title': 'videoFormat', 'value': 'videoFormat'},
                                                {'title': 'videoCodec', 'value': 'videoCodec'},
                                                {'title': 'audioCodec', 'value': 'audioCodec'},
                                            ],
                                            'hint': '请选择分隔符适用范围',
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
                                'props': {'cols': 12},
                                'content': [
                                    {
                                        'component': 'VTextarea',
                                        'props': {
                                            'model': 'word_replacements',
                                            'label': '自定义替换词',
                                            'rows': 5,
                                            'placeholder': '每行输入一条替换规则，格式：被替换词 => 替换词',
                                            'hint': '定义替换规则，重命名后会自动进行词语替换',
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
                                'props': {'cols': 12},
                                'content': [
                                    {
                                        'component': 'VTextarea',
                                        'props': {
                                            'model': 'template_groups',
                                            'label': '自定义重命名模板',
                                            'rows': 5,
                                            'placeholder': '每行输入一条重命名模板，格式：\n二级分类名称:重命名模板\nTMDBID:重命名模板',
                                            'hint': '定义重命名模板，覆盖默认的重命名模板',
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
                                'props': {'cols': 12, 'md': 6},
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'cache_enabled',
                                            'label': '启用缓存',
                                            'hint': '开启后可以提升性能，但可能会占用更多内存',
                                            'persistent-hint': True
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 6},
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'cache_ttl',
                                            'label': '缓存时间(秒)',
                                            'type': 'number',
                                            'hint': '缓存的有效期，单位为秒',
                                            'persistent-hint': True
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
            "separator": ".",
            "separator_types": ["title", "en_title", "resourceType", "effect", "edition", "videoFormat", "videoCodec", "audioCodec"],
            "custom_separator": ".",
            "cache_enabled": True,
            "cache_ttl": 3600,
            "word_replacements": """：\. => ：
(?i)(?<=[\W_])BluRay.REMUX(?=[\W_]) => REMUX
(?i)(?<=[\W_])HDR.DV(?=[\W_]) => DoVi.HDR
(?i)(?<=[\W_])DV(?=[\W_]) => DoVi
(?i)(?<=[\W_])4k(?=[\W_]) => 2160p
(?i)(?<=[\W_])1080p(?=[\W_]) => 1080p
(?i)(?<=[\W_])H264(?=[\W_]) => x264
(?i)(?<=[\W_])h265(?=[\W_]) => x265
(?i)(?<=[\W_])NF(?=[\W_]) => Netflix
(?i)(?<=[\W_])AMZN(?=[\W_]) => Amazon
(?i)(?<=[\W_])BluRay(?=[\W_]) => BluRay
(?i)(?<=[\W_])WEB-DL(?=[\W_]) => WEB-DL
(?i)(?<=[\W_])Disc(?=[\W_]) => part
(?i)\.Atmos(?=\W) => """
        }