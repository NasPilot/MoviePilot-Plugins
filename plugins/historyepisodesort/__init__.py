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
    plugin_version = "1.0.4"
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
        return [
            {
                "path": "/page",
                "endpoint": self.get_page_api,
                "methods": ["GET"],
                "summary": "获取插件页面",
                "description": "获取插件的HTML页面",
                "auth": "bear",
            },
            {
                "path": "/tv_histories",
                "endpoint": self.get_tv_histories_api,
                "methods": ["GET"],
                "summary": "获取电视剧历史记录",
                "description": "获取所有电视剧的历史记录列表",
                "auth": "bear",
            },
            {
                "path": "/sort_selected",
                "endpoint": self.sort_selected_api,
                "methods": ["POST"],
                "summary": "排序选中的电视剧",
                "description": "对选中的电视剧进行剧集排序",
                "auth": "bear",
            },
            {
                "path": "/update_time",
                "endpoint": self.update_time_api,
                "methods": ["POST"],
                "summary": "更新剧集时间",
                "description": "手动更新指定剧集的整理时间",
                "auth": "bear",
            },
            {
                "path": "/run_once",
                "endpoint": self.run_once_api,
                "methods": ["POST"],
                "summary": "立即运行一次",
                "description": "立即执行一次全部排序",
                "auth": "bear",
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
        """
        插件的额外页面，返回页面配置
        """
        return [
            {
                "component": "iframe",
                "props": {
                    "src": "/plugin/HistoryEpisodeSort/page",
                    "width": "100%",
                    "height": "800px",
                    "frameborder": "0"
                }
            }
        ]

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

    # API接口实现
    def get_page_api(self):
        """
        获取插件页面API
        """
        try:
            import os
            from fastapi.responses import HTMLResponse
            
            # 获取HTML文件路径
            html_file = os.path.join(os.path.dirname(__file__), "dist", "index.html")
            
            if os.path.exists(html_file):
                with open(html_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                return HTMLResponse(content=html_content, media_type="text/html")
            else:
                return HTMLResponse(content="<h1>页面文件不存在</h1>", media_type="text/html")
        except Exception as e:
            logger.error(f"获取页面失败: {str(e)}")
            return HTMLResponse(content=f"<h1>页面加载失败: {str(e)}</h1>", media_type="text/html")
    
    def get_tv_histories_api(self):
        """
        获取电视剧历史记录API
        """
        try:
            tv_histories = self.__get_tv_histories()
            if not tv_histories:
                return {"success": True, "data": []}
            
            # 按tmdb_id分组统计
            tv_groups = {}
            for history in tv_histories:
                tmdb_id = history.tmdbid
                if tmdb_id not in tv_groups:
                    tv_groups[tmdb_id] = {
                        "tmdb_id": tmdb_id,
                        "title": history.title,
                        "episodes": [],
                        "episode_count": 0,
                        "earliest_date": None,
                        "latest_date": None
                    }
                
                tv_groups[tmdb_id]["episodes"].append(history)
                tv_groups[tmdb_id]["episode_count"] += 1
                
                # 更新最早和最晚时间
                date = history.date
                if tv_groups[tmdb_id]["earliest_date"] is None or date < tv_groups[tmdb_id]["earliest_date"]:
                    tv_groups[tmdb_id]["earliest_date"] = date
                if tv_groups[tmdb_id]["latest_date"] is None or date > tv_groups[tmdb_id]["latest_date"]:
                    tv_groups[tmdb_id]["latest_date"] = date
            
            # 转换为列表格式
            result = []
            for group in tv_groups.values():
                result.append({
                    "tmdb_id": group["tmdb_id"],
                    "title": group["title"],
                    "episode_count": group["episode_count"],
                    "earliest_date": group["earliest_date"].strftime("%Y-%m-%d %H:%M:%S") if group["earliest_date"] else "",
                    "latest_date": group["latest_date"].strftime("%Y-%m-%d %H:%M:%S") if group["latest_date"] else ""
                })
            
            return {"success": True, "data": result}
        except Exception as e:
            logger.error(f"获取电视剧历史记录失败: {e}")
            return {"success": False, "message": str(e)}

    def sort_selected_api(self, **kwargs):
        """
        排序选中的电视剧API
        """
        try:
            tmdb_ids = kwargs.get('tmdb_ids', [])
            if not tmdb_ids:
                return {"success": False, "message": "未选择任何电视剧"}
            
            tv_histories = self.__get_tv_histories()
            if not tv_histories:
                return {"success": False, "message": "没有找到电视剧历史记录"}
            
            # 筛选选中的电视剧
            selected_histories = [h for h in tv_histories if h.tmdbid in tmdb_ids]
            if not selected_histories:
                return {"success": False, "message": "未找到选中的电视剧记录"}
            
            # 按tmdb_id和season分组
            tv_groups = {}
            for history in selected_histories:
                group_key = (history.tmdbid, history.season)
                if group_key not in tv_groups:
                    tv_groups[group_key] = []
                tv_groups[group_key].append(history)
            
            success_count = 0
            total_count = len(tv_groups)
            
            # 处理每个分组
            for group_key, episodes in tv_groups.items():
                try:
                    tmdbid, season = group_key
                    logger.info(f"正在处理选中的分组: tmdbid={tmdbid}, season={season}, 共 {len(episodes)} 集")
                    
                    if self.__sort_episode_group(episodes):
                        success_count += 1
                except Exception as e:
                    logger.error(f"处理分组 {group_key} 时出错: {e}")
            
            message = f"选中排序完成，成功处理 {success_count}/{total_count} 个分组"
            self.__log_and_notify(message)
            return {"success": True, "message": message}
            
        except Exception as e:
            logger.error(f"排序选中电视剧失败: {e}")
            return {"success": False, "message": str(e)}

    def update_time_api(self, **kwargs):
        """
        更新剧集时间API
        """
        try:
            history_id = kwargs.get('history_id')
            new_date = kwargs.get('new_date')
            
            if not history_id or not new_date:
                return {"success": False, "message": "缺少必要参数 history_id 或 new_date"}
            
            # 解析新时间
            try:
                new_datetime = datetime.strptime(new_date, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return {"success": False, "message": "时间格式错误，请使用 YYYY-MM-DD HH:MM:SS 格式"}
            
            # 更新数据库
            if self.__update_episode_date(history_id, new_date):
                message = f"成功更新剧集 {history_id} 的时间为 {new_date}"
                logger.info(message)
                return {"success": True, "message": message}
            else:
                return {"success": False, "message": "更新失败"}
                
        except Exception as e:
            logger.error(f"更新剧集时间失败: {e}")
            return {"success": False, "message": str(e)}

    def run_once_api(self):
        """
        立即运行一次API
        """
        try:
            # 在后台线程中执行排序
            import threading
            thread = threading.Thread(target=self.sort_episodes)
            thread.daemon = True
            thread.start()
            
            message = "已启动全部排序任务"
            logger.info(message)
            return {"success": True, "message": message}
            
        except Exception as e:
            logger.error(f"启动排序任务失败: {e}")
            return {"success": False, "message": str(e)}