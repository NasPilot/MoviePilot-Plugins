import os
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, List, Dict, Tuple, Optional
import re

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import db_query, db_update
from app.db.models import TransferHistory
from app.log import logger
from app.plugins import _PluginBase
from app.schemas import MediaType

lock = threading.Lock()


class HistoryEpisodeSort(_PluginBase):
    # 插件名称
    plugin_name = "历史记录排序"
    # 插件描述
    plugin_desc = "对同一部电视剧的不同剧集按正确的时间顺序重新排序。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/NasPilot/MoviePilot-Plugins/main/icons/historysort.png"
    # 插件版本
    plugin_version = "1.0.1"
    # 插件作者
    plugin_author = "NasPilot"
    # 作者主页
    author_url = "https://github.com/NasPilot"
    # 插件配置项ID前缀
    plugin_config_prefix = "historyepisodesort_"
    # 加载顺序
    plugin_order = 63
    # 可使用的用户级别
    auth_level = 1

    # region 私有属性

    # 启用剧集排序
    _enable_sort = None
    # 仅处理电视剧
    _tv_only = None
    # 退出事件
    _event = threading.Event()
    # 后台任务
    _scheduler = None

    # endregion

    def init_plugin(self, config: dict = None):
        if not config:
            return

        self._enable_sort = config.get("enable_sort", False)
        self._tv_only = config.get("tv_only", True)

        if not self._enable_sort:
            logger.info("未开启历史记录剧集排序")
            return

        self.update_config({})

        self._scheduler = BackgroundScheduler(timezone=settings.TZ)
        self._scheduler.add_job(self.sort_episodes, 'date',
                                run_date=datetime.now(
                                    tz=pytz.timezone(settings.TZ)
                                ) + timedelta(seconds=3),
                                name="历史记录剧集排序")

        if self._scheduler.get_jobs():
            # 启动服务
            self._scheduler.print_jobs()
            self._scheduler.start()

    def get_state(self) -> bool:
        pass

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        """
        定义远程控制命令
        :return: 命令关键字、事件、描述、附带数据
        """
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        pass

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
                                            'model': 'enable_sort',
                                            'label': '启用剧集排序',
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
                                            'model': 'tv_only',
                                            'label': '仅处理电视剧',
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
                                },
                                'content': [
                                    {
                                        'component': 'VAlert',
                                        'props': {
                                            'type': 'info',
                                            'variant': 'tonal',
                                            'text': '功能说明：该插件会分析同一部电视剧的不同剧集，按照剧集编号重新排序整理时间，确保剧集按正确的时间顺序显示。'
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
                                },
                                'content': [
                                    {
                                        'component': 'VAlert',
                                        'props': {
                                            'type': 'warning',
                                            'variant': 'tonal',
                                            'text': '注意：该操作会修改历史记录的整理时间，建议在执行前备份数据库。'
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ], {
            "enable_sort": False,
            "tv_only": True
        }

    def get_page(self) -> List[dict]:
        pass

    def get_service(self) -> List[Dict[str, Any]]:
        """
        注册插件公共服务
        [{
            "id": "服务ID",
            "name": "服务名称",
            "trigger": "触发器：cron/interval/date/CronTrigger.from_crontab()",
            "func": self.xxx,
            "kwargs": {} # 定时器参数
        }]
        """
        pass

    def stop_service(self):
        """
        退出插件
        """
        try:
            if self._scheduler:
                self._scheduler.remove_all_jobs()
                if self._scheduler.running:
                    self._event.set()
                    self._scheduler.shutdown()
                    self._event.clear()
                self._scheduler = None
        except Exception as e:
            print(str(e))

    def sort_episodes(self):
        """执行剧集排序"""
        if not self._enable_sort:
            return

        with lock:
            try:
                logger.info("开始执行历史记录剧集排序")
                self.__sort_tv_episodes()
            except Exception as e:
                self.__log_and_notify(f"剧集排序失败，请排查日志，错误：{e}")

    def __sort_tv_episodes(self):
        """排序电视剧剧集"""
        # 获取所有电视剧历史记录
        tv_histories = self.__get_tv_histories()
        logger.info(f"获取到电视剧历史记录共 {len(tv_histories)} 条")

        if not tv_histories:
            logger.warning("没有获取到电视剧历史记录，跳过排序")
            return

        # 按tmdbid和季数分组
        tv_groups = self.__group_by_tmdbid_season(tv_histories)
        logger.info(f"按tmdbid和季数分组，共获取到 {len(tv_groups)} 组")

        sorted_count = 0
        error_count = 0

        # 处理每个分组
        for group_key, episodes in tv_groups.items():
            if self._event.is_set():
                logger.warning("外部中断请求，剧集排序服务停止")
                break

            try:
                tmdbid, season = group_key
                logger.info(f"正在处理分组: tmdbid={tmdbid}, season={season}, 共 {len(episodes)} 集")
                
                # 对该分组的剧集进行排序
                if self.__sort_episode_group(episodes):
                    sorted_count += len(episodes)
                    logger.info(f"分组 tmdbid={tmdbid}, season={season} 排序完成")
                else:
                    error_count += len(episodes)
                    logger.warning(f"分组 tmdbid={tmdbid}, season={season} 排序失败")
                    
            except Exception as e:
                error_count += len(episodes)
                logger.error(f"处理分组 {group_key} 时发生错误: {e}")

        self.__log_and_notify(f"剧集排序完成，成功处理 {sorted_count} 集，失败 {error_count} 集")

    def __sort_episode_group(self, episodes: List[TransferHistory]) -> bool:
        """对单个分组的剧集进行排序"""
        try:
            # 解析剧集编号并排序
            episode_data = []
            for episode in episodes:
                episode_num = self.__extract_episode_number(episode.episodes)
                if episode_num is not None:
                    episode_data.append({
                        'history': episode,
                        'episode_num': episode_num,
                        'original_date': episode.date
                    })

            if len(episode_data) < 2:
                # 少于2集不需要排序
                return True

            # 按剧集编号排序
            episode_data.sort(key=lambda x: x['episode_num'])

            # 检查是否需要重新排序
            needs_reorder = False
            for i in range(len(episode_data) - 1):
                current_date = datetime.fromisoformat(episode_data[i]['original_date'])
                next_date = datetime.fromisoformat(episode_data[i + 1]['original_date'])
                if current_date > next_date:
                    needs_reorder = True
                    break

            if not needs_reorder:
                logger.info("该分组剧集时间顺序正确，无需调整")
                return True

            # 重新分配时间 - 使用更合理的间隔策略
            base_time = datetime.fromisoformat(episode_data[0]['original_date'])
            
            # 计算合适的时间间隔
            interval_seconds = self.__calculate_time_interval(len(episode_data))
            
            for i, data in enumerate(episode_data):
                # 根据计算的间隔时间分配
                new_time = base_time + timedelta(seconds=i * interval_seconds)
                new_date_str = new_time.isoformat()
                
                # 更新数据库
                self.__update_episode_date(data['history'].id, new_date_str)
                logger.debug(f"剧集 {data['history'].episodes} 时间调整: {data['original_date']} -> {new_date_str}")

            return True

        except Exception as e:
            logger.error(f"排序剧集分组时发生错误: {e}")
            return False

    def __extract_episode_number(self, episodes_str: str) -> Optional[int]:
        """从剧集字符串中提取剧集编号"""
        if not episodes_str:
            return None

        # 匹配 E01, E1, E001 等格式
        match = re.search(r'E(\d+)', episodes_str, re.IGNORECASE)
        if match:
            return int(match.group(1))

        # 匹配纯数字
        match = re.search(r'(\d+)', episodes_str)
        if match:
            return int(match.group(1))

        return None

    def __group_by_tmdbid_season(self, histories: List[TransferHistory]) -> Dict[Tuple[int, str], List[TransferHistory]]:
        """按tmdbid和季数分组"""
        groups = {}
        for history in histories:
            # 使用tmdbid和季数作为分组键
            season = history.seasons or "S01"  # 默认为第一季
            key = (history.tmdbid, season)
            
            if key not in groups:
                groups[key] = []
            groups[key].append(history)
        
        return groups

    @db_query
    def __get_tv_histories(self, db: Session) -> List[TransferHistory]:
        """获取所有电视剧历史记录"""
        return db.query(TransferHistory).filter(
            and_(
                TransferHistory.type == MediaType.TV.value,
                TransferHistory.tmdbid.isnot(None),
                TransferHistory.tmdbid != 0,
                TransferHistory.episodes.isnot(None),
                TransferHistory.status == True
            )
        ).order_by(TransferHistory.date.asc()).all()

    @db_update
    def __update_episode_date(self, db: Session, history_id: int, new_date: str):
        """更新剧集的整理时间"""
        db.query(TransferHistory).filter(
            TransferHistory.id == history_id
        ).update({'date': new_date})
        db.commit()

    def __calculate_time_interval(self, episode_count: int) -> float:
        """
        根据剧集数量计算合适的时间间隔（秒）
        
        策略：
        - 1-10集：每集间隔0.5秒
        - 11-50集：每集间隔0.2秒
        - 51集以上：每集间隔0.1秒
        
        确保间隔时间不超过1秒，符合正常整理的时间特征
        """
        if episode_count <= 10:
            return 0.5  # 0.5秒间隔
        elif episode_count <= 50:
            return 0.2  # 0.2秒间隔
        else:
            return 0.1  # 0.1秒间隔

    def __log_and_notify(self, message):
        """
        记录日志并发送系统通知
        """
        logger.info(message)
        self.systemmessage.put(message, title="历史记录剧集排序")