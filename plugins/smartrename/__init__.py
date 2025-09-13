import os
from typing import Any, Dict, List, Optional
from app.core.config import settings
from app.core.context import MediaInfo
from app.core.meta import MetaBase
from app.log import logger
from app.plugins import _PluginBase
from app.schemas import TransferInfo

class SmartRename(_PluginBase):
    """
    智能重命名插件
    """
    # 插件名称
    plugin_name = "智能重命名"
    # 插件描述
    plugin_desc = "提供智能文件重命名功能。"
    # 插件图标
    plugin_icon = "rename.png"
    # 插件版本
    plugin_version = "1.0"
    # 插件作者
    plugin_author = "NasPilot"
    # 作者主页
    author_url = "https://github.com/NasPilot"
    # 插件配置项ID前缀
    plugin_config_prefix = "smartrename_"
    # 加载顺序
    plugin_order = 21
    # 可使用的用户级别
    user_level = 1

    def init_plugin(self, config: Dict[str, Any]) -> None:
        """初始化插件配置"""
        pass

    def get_state(self) -> bool:
        """获取插件启用状态"""
        return True

    def stop_service(self) -> None:
        """停止服务"""
        pass

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        """注册命令"""
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        """注册API"""
        from .api import router
        return [
            {
                "path": "/api/v1/plugins/smartrename",
                "router": router,
                "description": "智能重命名插件API"
            }
        ]

    def get_form(self) -> Dict[str, Any]:
        """获取配置表单"""
        return {}

    def get_page(self) -> List[Dict[str, Any]]:
        """获取页面"""
        return [
            {
                "name": "重命名管理",
                "path": "/smartrename",
                "component": "smartrename/index"
            }
        ]

    def get_script(self) -> List[Dict[str, Any]]:
        """获取脚本"""
        return []

    def get_service(self) -> List[Dict[str, Any]]:
        """注册服务"""
        return []

    def __rename_file(self, file_path: str, new_name: str) -> bool:
        """重命名文件"""
        try:
            os.rename(file_path, new_name)
            return True
        except Exception as e:
            logger.error(f"重命名文件失败: {str(e)}")
            return False

    def transfer_completed(self, file_item: TransferInfo, mediainfo: MediaInfo, meta: MetaBase) -> Optional[bool]:
        """文件转移完成后处理"""
        from .api import add_file
        add_file(file_item, mediainfo, meta)
        return True