# PlexWarp

## 插件简介

PlexWarp 是一个专为 Plex 媒体服务器设计的中间件插件，主要功能包括：

- 优化播放 STRM 文件
- 自定义前端样式
- 自定义允许访问客户端
- 嵌入脚本功能
- CRX 美化
- 头像过滤
- 显示同人图
- 外置播放器支持
- Web 弹幕
- 共同观影
- SRT 转 ASS 字幕

## 配置说明

### 基础设置

- **启用插件**: 开启或关闭插件功能
- **端口**: 反代后媒体服务器访问端口（默认：3002）
- **媒体服务器**: 选择要使用的 Plex 媒体服务器
- **STRM 媒体库路径**: 配置 STRM 文件的媒体库路径，一行一个

### STRM 路径示例

```
/media/strm/movie
/media/strm/tv
```

### Web 页面配置

- **CRX 美化**: 启用 CRX 美化功能
- **头像过滤**: 过滤没有头像的演员和制作人员
- **显示同人图**: 显示同人图（fanart 图）
- **外置播放器**: 开启外置播放器支持
- **Web 弹幕**: 启用 Web 弹幕功能
- **共同观影**: 启用共同观影功能

### 字体相关设置

- **SRT 转 ASS**: 将 SRT 字幕转换为 ASS 字幕

## 注意事项

1. 如果 MoviePilot 容器为 bridge 模式，需要手动映射配置的端口
2. 更多详细配置可以前往 MoviePilot 配置目录找到此插件的配置目录进行配置文件配置
3. 目前支持 115网盘STRM助手、123云盘STRM助手、CloudMediaSync、OneStrm、Symedia、q115-strm 等软件生成的 STRM 文件

## 致谢

感谢项目作者：https://github.com/NasPilot/MediaWarp

## 版本历史

- v1.0.0: 初始版本，基于 MediaWarp 项目适配 Plex 专用功能