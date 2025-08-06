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
    plugin_desc = "同步本地Hosts至梅林固件的/jffs/configs/hosts.add文件。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/NasPilot/MoviePilot-Plugins/main/icons/merlin.png"
    # 插件版本
    plugin_version = "0.6"
    # 插件作者
    plugin_author = "NasPilot"
    # 插件作者主页
    author_url = "https://github.com/NasPilot"
    # 插件配置项ID前缀
    plugin_config_prefix = "merlinhosts_"
    # 加载顺序
    plugin_order = 13
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
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'router_ip',
                                            'label': '路由器IP地址',
                                            'placeholder': '192.168.1.1',
                                            'hint': '请输入华硕梅林路由器的IP地址',
                                            'persistent-hint': True
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
                                            'model': 'ssh_port',
                                            'label': 'SSH端口',
                                            'placeholder': '22',
                                            'hint': '请输入SSH端口号，默认为22',
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
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'username',
                                            'label': '用户名',
                                            'placeholder': 'admin',
                                            'hint': '请输入SSH登录用户名，通常为admin',
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
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'password',
                                            'label': '密码',
                                            'hint': '请输入SSH登录密码',
                                            'persistent-hint': True,
                                            'type': 'password'
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
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'private_key_path',
                                            'label': '私钥文件路径',
                                            'hint': 'SSH私钥文件路径（可选，优先使用私钥）',
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
                                            'text': '注意：本插件通过SSH连接华硕梅林路由器，需要开启SSH服务并配置正确的登录凭据'
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
                                            'type': 'warning',
                                            'variant': 'tonal',
                                            'text': '注意：插件会将hosts条目写入/jffs/configs/hosts.add文件并重启dnsmasq服务，请确保路由器已开启JFFS分区'
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
            "cron": "0 6 * * *",
            "router_ip": "192.168.1.1",
            "ssh_port": 22,
            "username": "admin",
            "password": "",
            "private_key_path": "",
            "ignore": ""
        }

    def get_page(self) -> List[dict]:
        pass

    def sync_hosts_to_merlin(self):
        """
        获取本地hosts并更新到梅林路由器
        """
        # 获取路由器当前hosts
        remote_hosts = self.__fetch_remote_hosts()

        local_hosts = self.__get_local_hosts()
        if not local_hosts:
            self.__send_message(title="【梅林路由Hosts更新】", text="获取本地hosts失败，更新失败，请检查日志")
            return

        # 合并hosts
        updated_hosts = self.__merge_hosts_with_local(local_hosts, remote_hosts)
        if not updated_hosts:
            logger.info("没有需要更新的hosts，跳过")
            return

        # 更新路由器hosts
        self.__update_router_hosts(updated_hosts)

    def __fetch_remote_hosts(self) -> list:
        """
        通过SSH获取路由器当前的hosts.add文件内容
        """
        logger.info("正在获取路由器hosts.add文件")
        try:
            ssh_client = self.__create_ssh_connection()
            if not ssh_client:
                return []

            stdin, stdout, stderr = ssh_client.exec_command("cat /jffs/configs/hosts.add 2>/dev/null || echo ''")
            remote_hosts = stdout.read().decode('utf-8').splitlines()
            ssh_client.close()

            logger.info(f"获取路由器hosts.add成功: {len(remote_hosts)}行")
            return remote_hosts
        except Exception as e:
            logger.error(f"获取路由器hosts.add失败: {e}")
            return []

    def __merge_hosts_with_local(self, local_hosts: list, remote_hosts: list) -> list:
        """
        使用本地hosts内容覆盖远程hosts，并合并未冲突的条目，同时忽略IPv6和其他特定的本地定义
        """
        try:
            ignore = self._ignore.split("|") if self._ignore else []
            ignore.extend(["localhost"])

            # 创建远程hosts字典，适应空格或制表符分隔
            remote_dict = {}
            for line in remote_hosts:
                line = line.strip()
                if " " in line or "\t" in line:
                    parts = re.split(r'\s+', line)
                    if len(parts) > 1 and not line.startswith('#'):
                        ip, hostname = parts[0], parts[1]
                        if not self.__should_ignore_ip(ip) and hostname not in ignore and ip not in ignore:
                            remote_dict[hostname] = f"{ip}\t{hostname}"

            # 用本地hosts更新远程hosts
            for line in local_hosts:
                line = line.lstrip("\ufeff").strip()
                if line.startswith("#") or any(ign in line for ign in ignore):
                    continue
                parts = re.split(r'\s+', line)
                if len(parts) < 2:
                    continue
                ip, hostname = parts[0], parts[1]
                if not self.__should_ignore_ip(ip) and hostname not in ignore and ip not in ignore:
                    remote_dict[hostname] = f"{ip}\t{hostname}"

            # 组装最终的hosts列表
            updated_hosts = [line.strip() for line in remote_hosts if line.strip().startswith('#')]
            updated_hosts += [entry for entry in remote_dict.values()]

            logger.info(f"更新后的hosts为: {updated_hosts}")
            return updated_hosts
        except Exception as e:
            logger.error(f"合并hosts失败: {e}")
            return []



    def __update_router_hosts(self, hosts_content: list):
        """
        通过SSH更新路由器的hosts.add文件，增强错误处理和重试机制
        """
        message_title = "【梅林路由Hosts更新】"
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            ssh_client = None
            sftp = None
            try:
                ssh_client = self.__create_ssh_connection()
                if not ssh_client:
                    message_text = "SSH连接失败，无法更新路由器hosts"
                    logger.error(message_text)
                    self.__send_message(title=message_title, text=message_text)
                    return

                # 创建配置目录（如果不存在）
                stdin, stdout, stderr = ssh_client.exec_command("mkdir -p /jffs/configs")
                stdout.read()  # 等待命令完成
                
                # 先备份原始hosts.add文件
                stdin, stdout, stderr = ssh_client.exec_command("cp /jffs/configs/hosts.add /jffs/configs/hosts.add.backup 2>/dev/null || true")
                stdout.read()  # 等待命令完成

                # 创建新的hosts内容
                hosts_string = '\n'.join(hosts_content)
                if not hosts_string.endswith('\n'):
                    hosts_string += '\n'

                # 使用更稳定的方式写入文件
                try:
                    sftp = ssh_client.open_sftp()
                    # 设置SFTP超时
                    sftp.get_channel().settimeout(30)
                    
                    # 先写入临时文件，然后移动到目标位置
                    temp_file = '/tmp/hosts.add.tmp'
                    with sftp.open(temp_file, 'w') as remote_file:
                        remote_file.write(hosts_string)
                    
                    # 移动临时文件到目标位置
                    stdin, stdout, stderr = ssh_client.exec_command(f"mv {temp_file} /jffs/configs/hosts.add")
                    stdout.read()  # 等待命令完成
                    
                    sftp.close()
                    sftp = None
                    
                except Exception as sftp_error:
                    logger.warning(f"SFTP写入失败，尝试使用echo命令: {sftp_error}")
                    if sftp:
                        sftp.close()
                        sftp = None
                    
                    # 备用方案：使用echo命令写入文件
                    # 转义特殊字符
                    escaped_content = hosts_string.replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
                    stdin, stdout, stderr = ssh_client.exec_command(f'echo "{escaped_content}" > /jffs/configs/hosts.add')
                    stdout.read()  # 等待命令完成

                # 验证文件是否写入成功
                stdin, stdout, stderr = ssh_client.exec_command("wc -l /jffs/configs/hosts.add")
                line_count_output = stdout.read().decode('utf-8').strip()
                if line_count_output:
                    actual_lines = int(line_count_output.split()[0])
                    expected_lines = len(hosts_content)
                    logger.info(f"hosts.add文件写入验证: 期望{expected_lines}行，实际{actual_lines}行")

                # 重启dnsmasq服务
                stdin, stdout, stderr = ssh_client.exec_command("service restart_dnsmasq")
                
                # 等待命令完成并检查结果
                stdout_output = stdout.read().decode('utf-8')
                error_output = stderr.read().decode('utf-8')
                
                if error_output and "not found" not in error_output.lower():
                    logger.warning(f"dnsmasq重启警告: {error_output}")
                
                logger.info("路由器hosts.add文件更新成功")
                message_text = "路由器hosts.add文件更新成功"
                
                ssh_client.close()
                self.__send_message(title=message_title, text=message_text)
                return  # 成功完成，退出重试循环

            except (paramiko.SSHException, OSError, EOFError) as e:
                logger.warning(f"更新路由器hosts尝试 {attempt + 1}/{max_retries} 失败: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"等待 {retry_delay} 秒后重试...")
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    message_text = f"更新路由器hosts最终失败: {e}"
                    logger.error(message_text)
            except Exception as e:
                logger.error(f"更新路由器hosts异常: {e}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    message_text = f"更新路由器hosts最终失败: {e}"
            finally:
                # 确保资源清理
                if sftp:
                    try:
                        sftp.close()
                    except:
                        pass
                if ssh_client:
                    try:
                        ssh_client.close()
                    except:
                        pass
        
        # 如果所有重试都失败了
        if 'message_text' not in locals():
            message_text = "更新路由器hosts失败，已尝试所有重试"
        self.__send_message(title=message_title, text=message_text)

    def __create_ssh_connection(self):
        """
        创建SSH连接，增强错误处理和连接稳定性
        """
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                ssh_client = paramiko.SSHClient()
                ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
                # 设置连接参数以提高稳定性
                connect_kwargs = {
                    'hostname': self._router_ip,
                    'port': self._ssh_port,
                    'username': self._username,
                    'timeout': 15,  # 增加超时时间
                    'banner_timeout': 30,  # 增加banner超时
                    'auth_timeout': 30,  # 增加认证超时
                    'allow_agent': False,  # 禁用SSH agent
                    'look_for_keys': False,  # 禁用自动查找密钥
                    'compress': False,  # 禁用压缩
                }

                # 优先使用私钥认证
                if self._private_key_path and len(self._private_key_path.strip()) > 0:
                    try:
                        # 尝试不同的私钥类型
                        private_key = None
                        for key_class in [paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey, paramiko.DSSKey]:
                            try:
                                private_key = key_class.from_private_key_file(self._private_key_path)
                                break
                            except paramiko.PasswordRequiredException:
                                logger.error("私钥文件需要密码，请使用无密码的私钥文件")
                                return None
                            except Exception:
                                continue
                        
                        if private_key:
                            connect_kwargs['pkey'] = private_key
                        else:
                            logger.error("无法加载私钥文件，请检查文件格式")
                            return None
                    except Exception as e:
                        logger.error(f"加载私钥失败: {e}")
                        return None
                else:
                    # 使用密码认证
                    connect_kwargs['password'] = self._password

                # 尝试连接
                ssh_client.connect(**connect_kwargs)
                
                # 测试连接是否正常
                transport = ssh_client.get_transport()
                if transport and transport.is_active():
                    logger.info(f"SSH连接成功: {self._router_ip}:{self._ssh_port} (尝试 {attempt + 1}/{max_retries})")
                    return ssh_client
                else:
                    ssh_client.close()
                    raise Exception("SSH传输通道未激活")

            except paramiko.AuthenticationException as e:
                logger.error(f"SSH认证失败: {e}")
                return None  # 认证失败不重试
            except (paramiko.SSHException, OSError, EOFError) as e:
                logger.warning(f"SSH连接尝试 {attempt + 1}/{max_retries} 失败: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"等待 {retry_delay} 秒后重试...")
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                else:
                    logger.error(f"SSH连接最终失败，已尝试 {max_retries} 次")
            except Exception as e:
                logger.error(f"SSH连接异常: {e}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    logger.error(f"SSH连接最终失败: {e}")
        
        return None

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