import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, List, Dict, Tuple, Optional

from fastapi import UploadFile
from fastapi.responses import FileResponse, HTMLResponse

from app.core.context import MediaInfo
from app.db import SessionFactory
from app.db.models import TransferHistory
from app.log import logger
from app.plugins import _PluginBase
from app.utils.string import StringUtils


class HistoryImportExport(_PluginBase):
    # 插件名称
    plugin_name = "历史记录导入导出"
    # 插件描述
    plugin_desc = "支持按电视剧分别导出历史记录，并可按剧集顺序重新排列时间后导入。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/NasPilot/MoviePilot-Plugins/main/icons/historyimport.png"
    # 插件版本
    plugin_version = "1.0.0"
    # 插件作者
    plugin_author = "NasPilot"
    # 作者主页
    author_url = "https://github.com/NasPilot"
    # 插件配置项ID前缀
    plugin_config_prefix = "historyimportexport_"
    # 加载顺序
    plugin_order = 99
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _enabled = False
    _export_path = None
    _time_interval = 30
    _auto_sort = True

    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled")
            self._export_path = config.get("export_path") or "/tmp/history_export"
            self._time_interval = config.get("time_interval") or 30
            self._auto_sort = config.get("auto_sort", True)

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    @staticmethod
    def get_render_mode() -> Tuple[str, str]:
        """
        获取渲染模式
        """
        return "none", ""

    def get_api(self) -> List[Dict[str, Any]]:
        return [
            {
                "path": "/export_all",
                "endpoint": self.export_all_api,
                "methods": ["POST"],
                "summary": "导出所有历史记录",
                "description": "导出所有历史记录到JSON文件",
                "auth": "bear",
            },
            {
                "path": "/export_tv",
                "endpoint": self.export_tv_api,
                "methods": ["POST"],
                "summary": "按电视剧导出",
                "description": "按电视剧分别导出历史记录",
                "auth": "bear",
            },
            {
                "path": "/import_history",
                "endpoint": self.import_history_api,
                "methods": ["POST"],
                "summary": "导入历史记录",
                "description": "从JSON文件导入历史记录",
                "auth": "bear",
            },
            {
                "path": "/download/{filename}",
                "endpoint": self.download_file_api,
                "methods": ["GET"],
                "summary": "下载导出文件",
                "description": "下载导出的历史记录文件",
                "auth": "bear",
            },
            {
                "path": "/list_exports",
                "endpoint": self.list_exports_api,
                "methods": ["GET"],
                "summary": "列出导出文件",
                "description": "列出所有导出的历史记录文件",
                "auth": "bear",
            },
            {
                "path": "/page",
                "endpoint": self.get_page_api,
                "methods": ["GET"],
                "summary": "获取插件页面",
                "description": "获取插件的HTML页面",
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
                                    'md': 4
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
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'export_path',
                                            'label': '导出文件保存路径',
                                            'placeholder': '/tmp/history_export',
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
                                            'model': 'time_interval',
                                            'label': '剧集时间间隔（分钟）',
                                            'placeholder': '30',
                                            'type': 'number'
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
                                            'model': 'auto_sort',
                                            'label': '导入时自动按剧集排序',
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
                                            'text': '支持导出所有历史记录或按电视剧分别导出，导入时可自动按剧集顺序重新排列时间。'
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
            "export_path": "/tmp/history_export",
            "time_interval": 30,
            "auto_sort": True
        }

    def get_page(self) -> List[dict]:
        """
        插件的额外页面，返回页面配置
        """
        return [
            {
                "component": "iframe",
                "props": {
                    "src": "/plugin/HistoryImportExport/page",
                    "width": "100%",
                    "height": "800px",
                    "frameborder": "0"
                }
            }
        ]

    def stop_service(self):
        """
        退出插件
        """
        pass

    # API接口实现
    def get_page_api(self):
        """
        获取插件页面API
        """
        try:
            # 读取HTML文件
            html_file = Path(__file__).parent / "dist" / "index.html"
            if html_file.exists():
                with open(html_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                return HTMLResponse(content=html_content, media_type="text/html")
            else:
                return HTMLResponse(content="<h1>页面文件不存在</h1>", media_type="text/html")
        except Exception as e:
            logger.error(f"获取插件页面失败：{str(e)}")
            return HTMLResponse(content=f"<h1>页面加载失败：{str(e)}</h1>", media_type="text/html")

    def export_all_api(self):
        """
        导出所有历史记录API
        """
        try:
            # 确保导出目录存在
            os.makedirs(self._export_path, exist_ok=True)
            
            # 获取所有历史记录
            with SessionFactory() as db:
                histories = db.query(TransferHistory).order_by(TransferHistory.date.desc()).all()
            
            if not histories:
                return {"success": False, "message": "没有找到历史记录"}
            
            # 转换为字典格式
            export_data = []
            for history in histories:
                export_data.append(self._history_to_dict(history))
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"all_history_{timestamp}.json"
            filepath = os.path.join(self._export_path, filename)
            
            # 写入文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"导出所有历史记录成功，共 {len(export_data)} 条记录，文件：{filepath}")
            return {
                "success": True, 
                "message": f"导出成功，共 {len(export_data)} 条记录",
                "filename": filename,
                "count": len(export_data)
            }
            
        except Exception as e:
            logger.error(f"导出所有历史记录失败：{str(e)}")
            return {"success": False, "message": f"导出失败：{str(e)}"}

    def export_tv_api(self):
        """
        按电视剧导出历史记录API
        """
        try:
            # 确保导出目录存在
            os.makedirs(self._export_path, exist_ok=True)
            
            # 获取所有电视剧历史记录
            with SessionFactory() as db:
                tv_histories = db.query(TransferHistory).filter(
                    TransferHistory.type == "电视剧"
                ).order_by(TransferHistory.date.desc()).all()
            
            if not tv_histories:
                return {"success": False, "message": "没有找到电视剧历史记录"}
            
            # 按电视剧分组
            tv_groups = {}
            for history in tv_histories:
                key = f"{history.title}_{history.year}_{history.tmdbid or 'unknown'}"
                if key not in tv_groups:
                    tv_groups[key] = []
                tv_groups[key].append(history)
            
            # 为每个电视剧生成导出文件
            exported_files = []
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            for tv_key, histories in tv_groups.items():
                # 转换为字典格式
                export_data = []
                for history in histories:
                    export_data.append(self._history_to_dict(history))
                
                # 生成安全的文件名
                safe_title = StringUtils.str_filenamify(histories[0].title or "unknown")
                filename = f"tv_{safe_title}_{histories[0].year or 'unknown'}_{timestamp}.json"
                filepath = os.path.join(self._export_path, filename)
                
                # 写入文件
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
                
                exported_files.append({
                    "filename": filename,
                    "title": histories[0].title,
                    "year": histories[0].year,
                    "count": len(export_data)
                })
            
            logger.info(f"按电视剧导出历史记录成功，共导出 {len(exported_files)} 个文件")
            return {
                "success": True,
                "message": f"导出成功，共导出 {len(exported_files)} 个电视剧文件",
                "files": exported_files
            }
            
        except Exception as e:
            logger.error(f"按电视剧导出历史记录失败：{str(e)}")
            return {"success": False, "message": f"导出失败：{str(e)}"}

    def import_history_api(self, file: UploadFile):
        """
        导入历史记录API
        """
        try:
            # 读取上传的文件
            content = file.file.read()
            data = json.loads(content.decode('utf-8'))
            
            if not isinstance(data, list):
                return {"success": False, "message": "文件格式错误，应为JSON数组"}
            
            # 如果启用自动排序，对电视剧剧集进行排序
            if self._auto_sort:
                data = self._sort_tv_episodes(data)
            
            # 导入历史记录
            imported_count = 0
            skipped_count = 0
            
            with SessionFactory() as db:
                for item in data:
                    try:
                        # 检查是否已存在相同的记录
                        existing = db.query(TransferHistory).filter(
                            TransferHistory.src == item.get("src")
                        ).first()
                        
                        if existing:
                            skipped_count += 1
                            continue
                        
                        # 创建新的历史记录
                        history = TransferHistory(
                            src=item.get("src"),
                            src_storage=item.get("src_storage", "local"),
                            src_fileitem=item.get("src_fileitem", {}),
                            dest=item.get("dest"),
                            dest_storage=item.get("dest_storage", "local"),
                            dest_fileitem=item.get("dest_fileitem", {}),
                            mode=item.get("mode"),
                            type=item.get("type"),
                            category=item.get("category"),
                            title=item.get("title"),
                            year=item.get("year"),
                            tmdbid=item.get("tmdbid"),
                            imdbid=item.get("imdbid"),
                            tvdbid=item.get("tvdbid"),
                            doubanid=item.get("doubanid"),
                            seasons=item.get("seasons"),
                            episodes=item.get("episodes"),
                            image=item.get("image"),
                            downloader=item.get("downloader"),
                            download_hash=item.get("download_hash"),
                            status=item.get("status", True),
                            errmsg=item.get("errmsg"),
                            date=item.get("date"),
                            files=item.get("files", []),
                            episode_group=item.get("episode_group")
                        )
                        
                        db.add(history)
                        imported_count += 1
                        
                    except Exception as e:
                        logger.error(f"导入单条记录失败：{str(e)}")
                        continue
                
                db.commit()
            
            logger.info(f"导入历史记录完成，成功导入 {imported_count} 条，跳过 {skipped_count} 条")
            return {
                "success": True,
                "message": f"导入完成，成功导入 {imported_count} 条记录，跳过 {skipped_count} 条重复记录",
                "imported": imported_count,
                "skipped": skipped_count
            }
            
        except Exception as e:
            logger.error(f"导入历史记录失败：{str(e)}")
            return {"success": False, "message": f"导入失败：{str(e)}"}

    def download_file_api(self, filename: str):
        """
        下载导出文件API
        """
        try:
            filepath = os.path.join(self._export_path, filename)
            if not os.path.exists(filepath):
                return {"success": False, "message": "文件不存在"}
            
            return FileResponse(
                path=filepath,
                filename=filename,
                media_type='application/json'
            )
            
        except Exception as e:
            logger.error(f"下载文件失败：{str(e)}")
            return {"success": False, "message": f"下载失败：{str(e)}"}

    def list_exports_api(self):
        """
        列出导出文件API
        """
        try:
            if not os.path.exists(self._export_path):
                return {"success": True, "data": []}
            
            files = []
            for filename in os.listdir(self._export_path):
                if filename.endswith('.json'):
                    filepath = os.path.join(self._export_path, filename)
                    stat = os.stat(filepath)
                    files.append({
                        "filename": filename,
                        "size": stat.st_size,
                        "created": datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
                    })
            
            # 按创建时间倒序排列
            files.sort(key=lambda x: x["created"], reverse=True)
            
            return {"success": True, "data": files}
            
        except Exception as e:
            logger.error(f"列出导出文件失败：{str(e)}")
            return {"success": False, "message": f"获取文件列表失败：{str(e)}"}

    def _history_to_dict(self, history: TransferHistory) -> dict:
        """
        将TransferHistory对象转换为字典
        """
        return {
            "src": history.src,
            "src_storage": history.src_storage,
            "src_fileitem": history.src_fileitem,
            "dest": history.dest,
            "dest_storage": history.dest_storage,
            "dest_fileitem": history.dest_fileitem,
            "mode": history.mode,
            "type": history.type,
            "category": history.category,
            "title": history.title,
            "year": history.year,
            "tmdbid": history.tmdbid,
            "imdbid": history.imdbid,
            "tvdbid": history.tvdbid,
            "doubanid": history.doubanid,
            "seasons": history.seasons,
            "episodes": history.episodes,
            "image": history.image,
            "downloader": history.downloader,
            "download_hash": history.download_hash,
            "status": history.status,
            "errmsg": history.errmsg,
            "date": history.date,
            "files": history.files,
            "episode_group": history.episode_group
        }

    def _sort_tv_episodes(self, data: List[dict]) -> List[dict]:
        """
        对电视剧剧集按顺序重新排列时间
        """
        try:
            # 按电视剧分组
            tv_groups = {}
            other_records = []
            
            for item in data:
                if item.get("type") == "电视剧" and item.get("seasons") and item.get("episodes"):
                    key = f"{item.get('title')}_{item.get('year')}_{item.get('tmdbid') or 'unknown'}"
                    if key not in tv_groups:
                        tv_groups[key] = []
                    tv_groups[key].append(item)
                else:
                    other_records.append(item)
            
            # 对每个电视剧的剧集进行排序
            sorted_data = []
            
            for tv_key, episodes in tv_groups.items():
                # 按季和集排序
                episodes.sort(key=lambda x: (
                    int(x.get("seasons", "S01")[1:]) if x.get("seasons", "S01")[1:].isdigit() else 999,
                    int(x.get("episodes", "E01")[1:]) if x.get("episodes", "E01")[1:].isdigit() else 999
                ))
                
                # 重新分配时间
                if episodes:
                    # 获取最早的时间作为基准
                    base_time = min(episode.get("date", "") for episode in episodes if episode.get("date"))
                    if base_time:
                        base_datetime = datetime.strptime(base_time, "%Y-%m-%d %H:%M:%S")
                        
                        for i, episode in enumerate(episodes):
                            # 每集间隔指定的分钟数
                            new_time = base_datetime + timedelta(minutes=i * self._time_interval)
                            episode["date"] = new_time.strftime("%Y-%m-%d %H:%M:%S")
                
                sorted_data.extend(episodes)
            
            # 添加其他记录
            sorted_data.extend(other_records)
            
            logger.info(f"电视剧剧集排序完成，共处理 {len(tv_groups)} 个电视剧")
            return sorted_data
            
        except Exception as e:
            logger.error(f"电视剧剧集排序失败：{str(e)}")
            return data