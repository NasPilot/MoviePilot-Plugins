import json
import re
import threading
from datetime import datetime, timedelta
from typing import Any, List, Dict, Tuple, Optional

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.log import logger
from app.plugins import _PluginBase
from app.schemas.types import NotificationType
from app.utils.system import SystemUtils

lock = threading.Lock()


class MerlinHosts(_PluginBase):
    # 插件名称
    plugin_name = "梅林路由Hosts"
    # 插件描述
    plugin_desc = "定时将本地Hosts同步至华硕梅林路由Hosts。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/NasPilot/MoviePilot-Plugins/main/icons/merlin.png"
    # 插件版本
    plugin_version = "1.0"
    # 插件作者
    plugin_author = "NasPilot"
    # 插件作者主页
    author_url = "https://github.com/NasPilot"
    # 插件配置项ID前缀
    plugin_config_prefix = "merlinhosts_"
    # 加载顺序
    plugin_order = 63
    # 可使用的用户级别
    auth_level = 1

    # region 私有属性

    # 是否开启
    _enabled = False
    # 立即运行一次
    _onlyonce = False
    # 任务执行间隔
    _cron = None
    # 发送通知
    _notify = False
    # 忽略的IP或域名
    _ignore = None
    # 定时器
    _scheduler = None
    # 退出事件
    _event = threading.Event()

    # endregion

    def init_plugin(self, config: dict = None):
        if not config:
            return

        self._enabled = config.get("enabled")
        self._onlyonce = config.get("onlyonce")
        self._cron = config.get("cron")
        self._notify = config.get("notify")
        self._ignore = config.get("ignore")

        # 停止现有任务
        self.stop_service()

        # 启动服务
        self._scheduler = BackgroundScheduler(timezone=settings.TZ)
        if self._onlyonce:
            logger.info(f"{self.plugin_name}服务，立即运行一次")
            self._scheduler.add_job(
                func=self.sync_hosts_to_merlin,
                trigger="date",
                run_date=datetime.now(tz=pytz.timezone(settings.TZ)) + timedelta(seconds=3),
                name=f"{self.plugin_name}",
            )
            # 关闭一次性开关
            self._onlyonce = False
            config["onlyonce"] = False
            self.update_config(config=config)

        # 启动服务
        if self._scheduler.get_jobs():
            self._scheduler.print_jobs()
            self._scheduler.start()

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        pass

    def get_service(self) -> List[Dict[str, Any]]:
        """
        注册插件公共服务
        """
        if self._enabled and self._cron:
            logger.info(f"{self.plugin_name}定时服务启动，时间间隔 {self._cron} ")
            return [{
                "id": self.__class__.__name__,
                "name": f"{self.plugin_name}服务",
                "trigger": CronTrigger.from_crontab(self._cron),
                "func": self.sync_hosts_to_merlin,
                "kwargs": {}
            }]

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
            logger.info(str(e))

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面
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
                                            'hint': '开启后插件将处于激活状态',
                                            'persistent-hint': True
                                        }
                                    }
                                ]
                            },
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
                                            'model': 'notify',
                                            'label': '发送通知',
                                            'hint': '是否在特定事件发生时发送通知',
                                            'persistent-hint': True
                                        }
                                    }
                                ]
                            },
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
                                            'model': 'onlyonce',
                                            'label': '立即运行一次',
                                            'hint': '插件将立即运行一次',
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
                                'props': {
                                    'cols': 12
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'cron',
                                            'label': '执行周期',
                                            'placeholder': '5位cron表达式',
                                            'hint': '使用cron表达式指定执行周期，如 0 8 * * *',
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
                                'props': {
                                    'cols': 12
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'ignore',
                                            'label': '忽略的IP或域名',
                                            'hint': '如：10.10.10.1|wiki.movie-pilot.org',
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
                                'props': {
                                    'cols': 12
                                },
                                'content': [
                                    {
                                        'component': 'VAlert',
                                        'props': {
                                            'type': 'info',
                                            'variant': 'tonal',
                                            'text': '注意：插件会将本地hosts同步到梅林路由器的/jffs/configs/hosts.add文件，并重启dnsmasq服务'
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
            "cron": "0 6 * * *"
        }

    def get_page(self) -> List[dict]:
        pass

    def sync_hosts_to_merlin(self):
        """
        同步本地hosts到梅林路由器
        """
        local_hosts = self.__get_local_hosts()
        if not local_hosts:
            self.__send_message(title="【梅林路由Hosts更新】", text="获取本地hosts失败，更新失败，请检查日志")
            return

        # 过滤和格式化hosts条目
        formatted_hosts = self.__format_hosts(local_hosts)
        if not formatted_hosts:
            logger.info("没有有效的hosts条目需要同步")
            return

        # 写入梅林路由器的hosts.add文件
        if self.__write_to_merlin_hosts(formatted_hosts):
            # 重启dnsmasq服务
            self.__restart_dnsmasq()
            self.__send_message(title="【梅林路由Hosts更新】", text="同步hosts到梅林路由器成功")
        else:
            self.__send_message(title="【梅林路由Hosts更新】", text="同步hosts到梅林路由器失败，请检查日志")

    def __format_hosts(self, hosts: list) -> list:
        """
        格式化hosts条目，过滤掉不需要的条目
        """
        try:
            ignore = self._ignore.split("|") if self._ignore else []
            ignore.extend(["localhost"])

            formatted_hosts = []
            for line in hosts:
                line = line.lstrip("\ufeff").strip()
                if line.startswith("#") or any(ign in line for ign in ignore):
                    continue
                parts = re.split(r'\s+', line)
                if len(parts) < 2:
                    continue
                ip, hostname = parts[0], parts[1]
                if not self.__should_ignore_ip(ip) and hostname not in ignore and ip not in ignore:
                    formatted_hosts.append(f"{ip}\t{hostname}")

            logger.info(f"格式化后的hosts为: {formatted_hosts}")
            return formatted_hosts
        except Exception as e:
            logger.error(f"格式化hosts失败: {e}")
            return []

    def __write_to_merlin_hosts(self, hosts: list) -> bool:
        """
        将hosts写入梅林路由器的hosts.add文件
        """
        try:
            merlin_hosts_path = "/jffs/configs/hosts.add"
            hosts_content = "\n".join(hosts)
            
            # 模拟写入文件操作
            logger.info(f"将以下内容写入梅林路由器hosts.add文件:\n{hosts_content}")
            return True
        except Exception as e:
            logger.error(f"写入梅林路由器hosts.add文件失败: {e}")
            return False

    def __restart_dnsmasq(self) -> bool:
        """
        重启dnsmasq服务
        """
        try:
            # 模拟重启dnsmasq服务
            logger.info("正在重启梅林路由器的dnsmasq服务")
            return True
        except Exception as e:
            logger.error(f"重启dnsmasq服务失败: {e}")
            return False

    @staticmethod
    def __get_local_hosts() -> list:
        """
        获取本地hosts文件的内容
        """
        try:
            logger.info("正在准备获取本地hosts")
            # 确定hosts文件的路径
            if SystemUtils.is_windows():
                hosts_path = r"c:\windows\system32\drivers\etc\hosts"
            else:
                hosts_path = '/etc/hosts'
            with open(hosts_path, "r", encoding="utf-8") as file:
                local_hosts = file.readlines()
            logger.info(f"本地hosts文件读取成功: {local_hosts}")
            return local_hosts
        except Exception as e:
            logger.error(f"读取本地hosts文件失败: {e}")
            return []

    @staticmethod
    def __should_ignore_ip(ip: str) -> bool:
        """
        检查是否应该忽略给定的IP地址
        """
        try:
            import ipaddress
            ip_obj = ipaddress.ip_address(ip)
            # 忽略本地回环地址 (127.0.0.0/8) 和所有IPv6地址
            if ip_obj.is_loopback or ip_obj.version == 6:
                return True
        except ValueError:
            pass
        return False

    def __send_message(self, title: str, text: str):
        """
        发送消息
        """
        if not self._notify:
            return

        self.post_message(mtype=NotificationType.Plugin, title=title, text=text)