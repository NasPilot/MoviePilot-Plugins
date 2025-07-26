# PlexWarp 插件

基于新版 PlexWarp 项目的 Plex 媒体服务器中间件，提供 302/301 重定向播放功能，支持路径映射、缓存优化和直链播放。

## 版本信息

- **版本**: 2.0.0
- **基于**: [NasPilot/PlexWarp](https://github.com/NasPilot/PlexWarp) 项目
- **核心组件**: plexwarp 二进制文件

## 主要特性

### 🚀 二进制改造方案
- ✅ 基于新版 PlexWarp 项目的优化架构
- ✅ 使用 plexwarp 二进制文件，无需复杂依赖
- ✅ 支持多平台：Linux (amd64/arm64)、macOS (amd64/arm64)、Windows (amd64)
- ✅ 一键部署，开箱即用

### 🎯 核心功能
- **302/301 重定向**: 优化媒体流传输，减少服务器负载
- **直链播放**: 支持直接播放模式，提升播放体验
- **路径映射**: 灵活的媒体路径映射配置
- **路由缓存**: 智能缓存机制，提升响应速度
- **SSL 支持**: 可选的 HTTPS 加密传输

### 🔧 技术架构
- **PlexWarp 核心**: 高性能的重定向处理引擎
- **配置文件**: 灵活的配置文件格式
- **进程管理**: 自动启动、停止、重启和状态监控
- **自动更新**: 支持自动检查和更新 plexwarp 二进制文件

## 安装配置

### 1. 基础设置

- **启用插件**: 开启 PlexWarp 服务
- **Nginx 端口**: 默认 5006，可自定义
- **Plex 服务器地址**: 留空自动检测，或手动指定
- **媒体挂载路径**: 配置媒体文件的挂载路径

### 2. 高级配置

- **SSL 配置**: 启用 HTTPS 支持
  - SSL 端口：默认 5007
  - SSL 域名：配置证书域名
- **自定义服务器 URL**: 用于反向代理场景
- **自动更新**: 自动检查 plexwarp 更新

### 3. 配置示例

```javascript
// 自动生成的配置文件 (constant.js)
const plexHost = "http://localhost:32400";
const nginxPort = 5006;
const redirectConfig = {
    enable: true,
    redirectType: "302",
    directPlay: true
};
const mediaPathMapping = [
    {"from": "/mnt/media", "to": "/mnt/media"},
    {"from": "/data/movies", "to": "/data/movies"}
];
```

### 4. Plex 服务器配置（重要）

- 在 Plex 设置中**禁用"远程访问"**
- 在设置>网络中**取消"启用中转"**的勾选
- 填写**"自定义服务器访问 URL"**为反代后的地址（如通过Lucky反代的HTTPS地址）

### 容器环境配置说明

**容器部署特殊配置：**

- **容器网关地址**：当 PlexWarp 以容器方式部署且与 Plex 位于同一宿主机时，插件会自动使用容器网关地址 `172.17.0.1:32400`
- **局域网地址备选**：如需使用局域网地址，可在生成的配置文件中手动修改为 `http://10.0.0.3:32400`
- **实际修改参数**：由于未安装 rclone 和 alist，实际生效的配置主要为 `plexHost` 参数
- **配置文件位置**：生成的配置文件为 `constant.js`，基于原 MediaLinker 配置结构简化

## 使用说明

### 1. 启动服务

插件启用后会自动：
1. 下载对应平台的 plexwarp 二进制文件
2. 生成适配的配置文件
3. 启动 PlexWarp 服务
4. 开始处理 Plex 请求

### 2. 访问地址

- **HTTP**: `http://localhost:5006`
- **HTTPS**: `https://localhost:5007` (如果启用 SSL)
- **自定义**: 使用配置的自定义服务器 URL

### 3. 监控管理

- 通过 MoviePilot 插件页面查看运行状态
- 支持远程控制命令：`/plexwarp_status`、`/plexwarp_restart`
- 提供 API 接口：`/plexwarp/status`

## 技术原理

### 重定向机制

1. **请求拦截**: 拦截 Plex 的 `/library/parts` 和 `/video/:/transcode` 请求
2. **路径解析**: 解析媒体文件的实际路径
3. **路径映射**: 根据配置进行路径转换
4. **302 重定向**: 返回优化后的媒体 URL

### 配置结构

```
plexwarp/
├── bin/                    # 二进制文件目录
│   └── plexwarp           # 核心可执行文件
├── config/                 # 配置文件目录
│   └── config.yaml        # 主配置文件
└── logs/                   # 日志目录
```

## 使用指南

### 环境准备

1. **确保 Plex 服务器正常运行**
2. **配置媒体文件路径映射**
3. **准备反向代理配置**（如果需要）

### 插件配置

1. **基础设置**
   - 启用插件
   - 设置 Nginx 端口（默认 5006）
   - 配置 Plex 服务器地址
   - 设置媒体挂载路径

2. **SSL 配置**（可选）
   ```
   启用 SSL: 是
   SSL 端口: 5007
   SSL 域名: your-domain.com
   ```

3. **Plex 网络设置**
   ```
   自定义服务器访问 URL: http://localhost:5006
   # 或反代后的地址: https://plex.example.com
   ```

### 服务验证

1. **检查服务状态**
   - 在插件页面查看运行状态
   - 使用远程命令 `/plexwarp_status` 检查

2. **验证端口访问**
   ```bash
   curl http://localhost:5006/health
   ```

3. **查看日志**
   ```
   日志位置: MoviePilot数据目录/plugins/plexwarp/logs/
   ```

## 故障排除

### 服务启动失败

**问题**: PlexWarp 服务无法启动

**解决方案**:
1. 检查端口是否被占用
   ```bash
   lsof -i :5006
   ```
2. 验证 Plex 服务器地址配置
3. 查看详细日志信息
4. 确保 plexwarp 二进制文件下载成功

### 302 重定向不生效

**问题**: 媒体播放未通过重定向优化

**解决方案**:
1. **检查 Plex 网络设置**
   - 确保已禁用"远程访问"
   - 确保已取消"启用中转"
   - 确认"自定义服务器访问 URL"正确

2. **验证路径映射**
   - 确保媒体挂载路径配置正确
   - 检查路径映射规则

3. **测试重定向**
   ```bash
   curl -I "http://localhost:5006/library/parts/xxx"
   ```

### SSL 证书问题

**问题**: HTTPS 访问出现证书错误

**解决方案**:
1. **检查证书文件**
   ```
   证书位置: MoviePilot数据目录/plugins/plexwarp/ssl/
   ```
2. **验证域名匹配**
3. **检查证书有效期**
4. **重新生成证书**（如果需要）

## 性能优化

### 缓存优化
- 合理设置缓存大小
- 定期清理过期缓存
- 监控缓存命中率

### 并发优化
- 根据服务器性能调整并发数
- 监控系统资源使用情况
- 优化网络带宽分配

### 日志管理
- 设置合适的日志级别
- 定期轮转日志文件
- 监控日志文件大小

## 监控与维护

### 健康检查
- 定期检查服务状态
- 监控端口响应
- 查看错误日志

### 日志管理
```bash
# 查看实时日志
tail -f /path/to/logs/plexwarp.log

# 查看错误日志
grep "ERROR" /path/to/logs/plexwarp.log
```

### 性能监控
- CPU 和内存使用率
- 网络带宽使用情况
- 响应时间统计

## 更新日志

### v2.0.0 (当前版本)
- 🔄 **重大更新**: 基于新版 PlexWarp 项目重构
- ✨ 使用 plexwarp 二进制文件替代原有架构
- 🚀 优化 302 重定向机制，提升播放性能
- 🔧 改进配置文件格式，适配新版 PlexWarp 架构
- 📝 更新插件描述和配置界面
- 🐛 修复多项稳定性问题
- 🎯 支持多平台 plexwarp 二进制文件自动下载
- ⚡ 优化路由缓存和响应速度

### v1.0.0
- 🎉 初始版本发布
- 基于原有架构实现基础功能

## 更新与维护

### 自动更新
- 启用"自动更新"选项
- 重启插件时自动检查 plexwarp 更新
- 自动备份现有版本

### 手动更新
1. 下载最新版本
2. 停止服务
3. 替换程序文件
4. 重启服务

## 常见问题

**Q: 为什么需要禁用 Plex 的远程访问？**
A: 禁用远程访问可以确保 Plex 使用自定义的服务器 URL，从而通过 PlexWarp 进行媒体访问。

**Q: 自定义服务器访问 URL 应该填写什么？**
A: 填写 PlexWarp 服务的访问地址。例如：
- PlexWarp 直接地址：`http://localhost:5006`
- 通过反代后：`https://plex.example.com`
- 在 Plex 中应填写对应的访问地址

**Q: 302 重定向的优势是什么？**
A: 302 重定向可以减少服务器负载，优化媒体流传输，提升播放体验，特别适合大文件和高清视频。

**Q: 如何查看详细的错误信息？**
A: 查看日志文件：`MoviePilot数据目录/plugins/plexwarp/logs/plexwarp.log`

## 技术支持

- **项目主页**: https://github.com/NasPilot/MoviePilot-Plugins
- **问题反馈**: 请在 GitHub 上提交 Issue
- **文档更新**: 请关注项目 README 更新

## 相关链接

- [PlexWarp 项目](https://github.com/NasPilot/PlexWarp)
- [MoviePilot 项目](https://github.com/jxxghp/MoviePilot)
- [Plex 官方文档](https://support.plex.tv/)

## 许可证

本项目采用 MIT 许可证，详情请参阅 LICENSE 文件。基于的 PlexWarp 项目请参考其相应许可证。

## 致谢

感谢以下项目和贡献者：
- [NasPilot/PlexWarp](https://github.com/NasPilot/PlexWarp) 项目提供的核心架构
- MoviePilot 项目团队
- Plex 媒体服务器
- 所有贡献代码和建议的开发者