# MediaWarp

## 插件描述

Plex/EmbyServer/Jellyfin 中间件：优化播放 Strm 文件、自定义前端样式、自定义允许访问客户端、嵌入脚本。

**版本**: 2.0.0  
**作者**: DDSRem  
**基于项目**: [MediaWarp](https://github.com/DDSRem/MediaWarp)

## 核心特性

### 🎯 多媒体服务器支持
- **Plex Server** - 支持Plex媒体服务器
- **Emby Server** - 支持Emby媒体服务器
- **Jellyfin Server** - 支持Jellyfin媒体服务器

### 🚀 核心功能
- **STRM文件优化** - 优化播放Strm文件的性能和兼容性
- **前端样式定制** - 自定义Web界面样式和主题
- **客户端访问控制** - 自定义允许访问的客户端
- **脚本嵌入** - 支持嵌入自定义JavaScript脚本
- **字幕转换** - SRT转ASS字幕格式转换
- **弹幕支持** - Web弹幕功能
- **共同观影** - 多用户同步观影功能

### 🔧 技术架构
- **YAML配置** - 使用YAML格式的配置文件
- **二进制部署** - 自动下载和管理MediaWarp二进制文件
- **多平台支持** - 支持Linux、Windows、macOS等平台
- **自动更新** - 支持自动检查和更新二进制文件

## 安装配置

### 基础设置

1. **启用插件**
   - 在插件页面启用MediaWarp插件

2. **端口配置**
   - 设置MediaWarp服务监听端口（默认：8096）

3. **媒体服务器配置**
   - 选择媒体服务器类型：Plex/Emby/Jellyfin
   - 配置服务器地址和API密钥

4. **STRM媒体库路径**
   - 配置STRM文件的媒体库路径
   - 支持多路径配置（每行一个路径）

### Plex服务器配置

```yaml
# Plex特有配置
Plex:
  Enable: true          # 启用Plex支持
  RedirectType: "302"    # 重定向类型
  DirectPlay: true      # 启用直接播放

# 媒体服务器配置
MediaServer:
  Type: "Plex"                    # 服务器类型
  ADDR: "http://localhost:32400"  # Plex服务器地址
  AUTH: "your-plex-token"         # Plex访问令牌
```

### Emby/Jellyfin服务器配置

```yaml
# 媒体服务器配置
MediaServer:
  Type: "Emby"                   # 或 "Jellyfin"
  ADDR: "http://localhost:8096"  # 服务器地址
  AUTH: "your-api-key"           # API密钥
```

### 高级配置

```yaml
# Web界面配置
Web:
  Crx: true              # CRX美化
  ActorPlus: false       # 头像过滤
  FanartShow: true       # 显示同人图
  ExternalPlayerUrl: false # 外置播放器
  Danmaku: true          # Web弹幕
  VideoTogether: false   # 共同观影

# STRM配置
HTTPStrm:
  Enable: true           # 启用STRM支持
  FinalURL: true         # 使用最终URL
  PrefixList:            # STRM路径前缀列表
    - "/mnt/media"
    - "/data/movies"

# 字幕配置
Subtitle:
  SRT2ASS: true          # SRT转ASS
```

## 使用说明

### 启动流程

1. **二进制下载** - 插件自动从GitHub下载MediaWarp二进制文件
2. **配置生成** - 根据插件设置生成YAML配置文件
3. **服务启动** - 启动MediaWarp服务进程
4. **服务监听** - 在指定端口提供中间件服务

### 访问地址

- **HTTP访问**: `http://your-server-ip:port`
- **配置管理**: 通过MoviePilot插件页面管理

### 监控管理

- **插件页面** - 在MoviePilot插件页面查看运行状态
- **日志查看** - 查看MediaWarp运行日志
- **进程管理** - 支持启动、停止、重启服务

## 技术原理

### 中间件架构

```
客户端请求 → MediaWarp中间件 → 媒体服务器
     ↓              ↓              ↓
  优化处理 ←    配置处理    ←    响应处理
```

### 配置结构

```
mediawarp/
├── bin/
│   └── MediaWarp          # 二进制文件
├── config/
│   └── config.yaml        # YAML配置文件
└── logs/
    └── mediawarp.log      # 运行日志
```

### Plex适配特性

- **302重定向** - 支持Plex的302重定向机制
- **直接播放** - 优化Plex的直接播放功能
- **令牌认证** - 支持Plex的X-Plex-Token认证
- **路径映射** - 智能处理Plex的媒体路径

## 故障排除

### 常见问题

1. **服务启动失败**
   - 检查端口是否被占用
   - 确认二进制文件下载完成
   - 查看插件日志获取详细错误信息

2. **Plex连接失败**
   - 验证Plex服务器地址是否正确
   - 确认Plex访问令牌有效
   - 检查网络连接和防火墙设置

3. **STRM文件播放问题**
   - 确认STRM路径配置正确
   - 检查媒体文件是否存在
   - 验证路径映射设置

### 日志分析

```bash
# 查看MediaWarp日志
tail -f /path/to/mediawarp/logs/mediawarp.log

# 查看插件日志
# 在MoviePilot日志中搜索"MediaWarp"
```

## 更新日志

### v2.0.0 (2024-12-19)
- ✨ **新增Plex支持** - 完整支持Plex媒体服务器
- 🔧 **配置格式统一** - 统一使用YAML配置格式
- 🚀 **多服务器支持** - 同时支持Plex、Emby、Jellyfin
- 📝 **配置生成优化** - 根据服务器类型动态生成配置
- 🎯 **Plex特性适配** - 支持302重定向、直接播放等Plex特性
- 🔄 **向下兼容** - 保持对原有Emby/Jellyfin配置的兼容

## 相关链接

- [MediaWarp项目](https://github.com/DDSRem/MediaWarp)
- [MoviePilot](https://github.com/jxxghp/MoviePilot)
- [Plex官方文档](https://support.plex.tv/)
- [Emby官方文档](https://emby.media/support.html)
- [Jellyfin官方文档](https://jellyfin.org/docs/)

## 许可证

本插件遵循 MIT 许可证。

## 致谢

- 感谢 [DDSRem](https://github.com/DDSRem) 开发的 MediaWarp 项目
- 感谢 [jxxghp](https://github.com/jxxghp) 开发的 MoviePilot 平台
- 感谢所有贡献者和用户的支持