# AdaptiveIntroSkip 插件升级说明

## 版本 1.8.0 更新内容

### 主要变化

1. **兼容最新版 MoviePilot**
   - 更新事件注册方式，从全局 `eventmanager` 改为实例方法 `self.eventmanager.register()`
   - 修复插件在最新版 MoviePilot 中无法正常安装和运行的问题

2. **HTTP 请求优化**
   - 替换 `requests` 库为 MoviePilot 内置的 `RequestUtils`
   - 增加请求失败的错误处理，提高插件稳定性

3. **代码规范化**
   - 更新插件基类方法的返回类型注解
   - 优化导入语句结构

### 升级前后对比

#### 事件注册方式
**旧版本 (1.7.7):**
```python
@eventmanager.register(EventType.WebhookMessage)
def hook(self, event: Event):
    # 处理逻辑
```

**新版本 (1.8.0):**
```python
def init_plugin(self, config: dict = None):
    # 配置初始化
    if self._enable:
        self.eventmanager.register(EventType.WebhookMessage, self.hook)
        self.eventmanager.register(EventType.TransferComplete, self.episodes_hook)

def hook(self, event: Event):
    # 处理逻辑
```

#### HTTP 请求方式
**旧版本:**
```python
import requests
response = requests.get(url, headers=headers)
```

**新版本:**
```python
from app.utils.http import RequestUtils
response = RequestUtils(headers=headers).get_res(url)
if not response:
    return  # 处理请求失败
```

### 安装要求

- MoviePilot 最新版本
- Emby 服务器
- ChapterAPI 插件（Emby 插件）

### 功能说明

本插件支持自适应生成 IntroSkip 片头片尾标记，适用于 Emby 跳片头、片尾功能。

主要特性：
- 自动检测片头片尾时间点
- 支持用户自定义时间段
- 支持关键词过滤
- 支持特别指定时间点
- 新集入库自动应用标记

### 使用说明

1. 确保 Emby 已安装 ChapterAPI 插件
2. 在 Emby 通知设置中添加 MoviePilot 的回调 webhook
3. 在 MoviePilot 中启用本插件并配置相关参数
4. 在限定时间内暂停/恢复播放或正常退出播放来标记片头片尾

### 注意事项

- 目前只支持 Emby 官方客户端、网页端等能够正确报告暂停信息的客户端
- 如遇到问题，建议重置插件配置
- 详细使用说明请参考：https://github.com/honue/MoviePilot-Plugins