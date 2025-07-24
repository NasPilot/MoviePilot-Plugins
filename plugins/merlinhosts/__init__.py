import ipaddress
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
from app.utils.common import retry
from app.utils.system import SystemUtils

# 依赖检查
import paramiko

lock = threading.Lock()


class MerlinHosts(_PluginBase):
    # 插件名称
    plugin_name = "梅林路由Hosts"
    # 插件描述
    plugin_desc = "通过SSH连接定时将本地Hosts同步至华硕梅林路由器，支持密码和密钥认证。"
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
    # 路由器IP地址
    _router_ip = None
    # SSH端口
    _ssh_port = 22
    # 用户名
    _username = None
    # 密码
    _password = None
    # 私钥文件路径
    _private_key_path = None
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
        self._router_ip = config.get("router_ip")
        self._ssh_port = config.get("ssh_port", 22)
        self._username = config.get("username")
        self._password = config.get("password")
        self._private_key_path = config.get("private_key_path")
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
        拼装插件配置页面 - Vue模式下返回空配置
        """
        return [], {
            "enabled": False,
            "notify": True,
            "cron": "0 6 * * *",
            "router_ip": "192.168.1.1",
            "ssh_port": 22,
            "username": "admin",
            "password": "",
            "private_key_path": "",
            "ignore": ""
        }

    def get_render_mode(self) -> Tuple[str, str]:
        """
        获取渲染模式
        """
        return "vue", "dist/assets"

    def get_page(self) -> List[dict]:
        pass

    def sync_hosts_to_merlin(self):
        """
        同步本地hosts到梅林路由器
        """
        # 检查必要的配置
        if not self._router_ip or not self._username:
            self.__send_message(title="【梅林路由Hosts更新】", text="路由器IP地址或用户名未配置，请检查配置")
            return

        # 获取本地hosts文件内容
        local_hosts = self.__get_local_hosts()
        if not local_hosts:
            self.__send_message(title="【梅林路由Hosts更新】", text="获取本地hosts失败，更新失败，请检查日志")
            return

        # 过滤和格式化hosts条目
        formatted_hosts = self.__format_hosts(local_hosts)
        if not formatted_hosts:
            logger.info("没有有效的hosts条目需要同步")
            self.__send_message(title="【梅林路由Hosts更新】", text="没有有效的hosts条目需要同步")
            return

        # 通过SSH连接到梅林路由器并同步hosts
        if self.__sync_hosts_via_ssh(formatted_hosts):
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

    @retry(Exception, logger=logger)
    def __sync_hosts_via_ssh(self, hosts: list) -> bool:
        """
        通过SSH连接到梅林路由器并同步hosts
        """
        ssh_client = None
        try:
            # 创建SSH客户端
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # 连接到路由器
            logger.info(f"正在连接到梅林路由器 {self._router_ip}:{self._ssh_port}")
            
            # 准备认证参数
            connect_kwargs = {
                'hostname': self._router_ip,
                'port': self._ssh_port,
                'username': self._username,
                'timeout': 30
            }
            
            # 选择认证方式
            if self._private_key_path and self._private_key_path.strip():
                # 使用私钥认证
                try:
                    private_key = paramiko.RSAKey.from_private_key_file(self._private_key_path)
                    connect_kwargs['pkey'] = private_key
                    logger.info("使用私钥认证")
                except Exception as e:
                    logger.error(f"加载私钥失败: {e}")
                    if self._password:
                        connect_kwargs['password'] = self._password
                        logger.info("私钥认证失败，回退到密码认证")
                    else:
                        return False
            elif self._password:
                # 使用密码认证
                connect_kwargs['password'] = self._password
                logger.info("使用密码认证")
            else:
                logger.error("未提供有效的认证方式（密码或私钥）")
                return False
            
            # 建立SSH连接
            ssh_client.connect(**connect_kwargs)
            logger.info("SSH连接建立成功")
            
            # 准备hosts内容
            hosts_content = "\n".join(hosts) + "\n"
            logger.info(f"准备写入的hosts内容:\n{hosts_content}")
            
            # 创建配置目录（如果不存在）
            stdin, stdout, stderr = ssh_client.exec_command("mkdir -p /jffs/configs")
            stdout.read()
            
            # 备份现有的hosts.add文件
            stdin, stdout, stderr = ssh_client.exec_command("cp /jffs/configs/hosts.add /jffs/configs/hosts.add.bak 2>/dev/null || true")
            stdout.read()
            
            # 写入新的hosts.add文件
            sftp = ssh_client.open_sftp()
            with sftp.open('/jffs/configs/hosts.add', 'w') as remote_file:
                remote_file.write(hosts_content)
            sftp.close()
            logger.info("hosts.add文件写入成功")
            
            # 重启dnsmasq服务
            logger.info("正在重启dnsmasq服务")
            stdin, stdout, stderr = ssh_client.exec_command("service restart_dnsmasq")
            result = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            
            if error:
                logger.warning(f"重启dnsmasq服务时有警告: {error}")
            
            logger.info(f"dnsmasq服务重启完成: {result}")
            return True
            
        except Exception as e:
            logger.error(f"SSH连接或操作失败: {e}")
            return False
        finally:
            if ssh_client:
                ssh_client.close()
                logger.info("SSH连接已关闭")

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