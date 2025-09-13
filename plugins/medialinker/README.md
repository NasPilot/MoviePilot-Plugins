# MediaLinker MoviePilot 插件

## 简介

MediaLinker 是一个为 MoviePilot 设计的高级插件，专门用于优化 Plex 媒体服务器的 Strm 文件播放体验。该插件基于 [embyExternalUrl](https://github.com/chen3861229/embyExternalUrl) 项目，经过深度优化，提供了企业级的中间件功能。

## 核心特性

### 🚀 智能服务管理
- **自动下载与更新**：自动从 GitHub 下载最新版本的 MediaLinker
- **版本管理**：智能版本检查和自动更新机制
- **进程监控**：使用 psutil 进行高级进程管理和健康检查
- **优雅停止**：支持优雅停止和强制终止机制
- **备份恢复**：自动备份和故障恢复功能

### 🎯 媒体优化
- **Strm 文件优化**：专业的 Strm 文件播放优化
- **直链加速**：支持各种云盘和网盘的直链播放
- **路径智能映射**：灵活的媒体路径映射和转换
- **缓存机制**：智能缓存提升播放性能

### 🔗 强大集成
- **Alist 深度集成**：完美支持 Alist 文件管理系统
- **rclone 挂载支持**：智能处理 rclone 挂载的媒体文件
- **Plex 原生支持**：针对 Plex 媒体服务器深度优化
- **多协议支持**：HTTP/HTTPS 双协议支持

### 🛡️ 安全与稳定
- **SSL/TLS 支持**：完整的 HTTPS 安全连接
- **配置验证**：智能配置验证和自动修复
- **错误恢复**：完善的错误处理和自动恢复机制
- **日志管理**：详细的日志记录和管理

## 主要功能

### 1. Strm文件优化
- 自动处理Strm文件的播放链接
- 支持多种媒体格式的直链播放
- 优化播放体验，减少缓冲时间

### 2. Alist集成
- 支持Alist API集成
- 自动获取直链地址
- 支持Alist签名验证
- 支持公网和内网地址切换

### 3. 路径映射
- 支持rclone挂载路径处理
- 自动路径映射和转换
- 支持多种存储后端

### 4. SSL支持
- 支持HTTPS配置
- 自动SSL证书管理
- 支持自定义域名

## 🚀 快速开始

### 安装步骤

1. **下载插件**
   ```bash
   git clone https://github.com/your-repo/MoviePilot-Plugins.git
   ```

2. **复制插件**
   ```bash
   cp -r plugins/medialinker /path/to/moviepilot/plugins/
   ```

3. **重启 MoviePilot**
   ```bash
   systemctl restart moviepilot
   ```

4. **启用插件**
   - 进入 MoviePilot 管理界面
   - 导航到「插件管理」
   - 找到「MediaLinker」插件并启用

### 首次配置

插件启用后会自动：
- 下载最新版本的 MediaLinker 程序
- 创建默认配置文件
- 启动服务并进行健康检查

## ⚙️ 详细配置

### 🔧 基础设置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| **启用插件** | `false` | 插件总开关 |
| **Nginx端口** | `8091` | HTTP 服务端口 |
| **SSL端口** | `8095` | HTTPS 服务端口 |
| **启用SSL** | `false` | HTTPS 支持开关 |
| **自动更新** | `true` | 自动检查和更新程序 |

### 🎬 Plex 集成

| 配置项 | 必填 | 说明 |
|--------|------|------|
| **媒体服务器** | ✅ | 选择要代理的Plex服务器 |
| **媒体挂载路径** | ✅ | rclone挂载的媒体库路径，一行一个 |

### 📁 Alist 集成

| 配置项 | 必填 | 说明 |
|--------|------|------|
| **Alist地址** | ✅ | 格式：`http://ip:port` |
| **Alist Token** | ✅ | Alist API访问令牌 |
| **Alist签名** | ❌ | 启用Alist签名验证 |
| **签名过期时间** | ❌ | 默认 24 小时 |
| **Alist公网地址** | ❌ | 供客户端直接访问的公网地址 |

### 🔒 SSL 设置

| 配置项 | 说明 | 示例 |
|--------|------|------|
| **启用SSL** | 开启HTTPS支持 | 建议生产环境启用 |
| **SSL端口** | HTTPS服务端口 | 默认 8095 |
| **SSL域名** | SSL证书对应的域名 | `media.yourdomain.com` |

## 📖 使用指南

### 基本使用流程

1. **环境准备**
   ```bash
   # 确保 Plex 服务器正常运行
   systemctl status plexmediaserver
   
   # 确保 Alist 服务正常（如果使用）
   systemctl status alist
   ```

2. **配置插件**
   - 在 MoviePilot 插件管理页面配置 MediaLinker
   - 填写 Plex 服务器信息和 Alist 配置
   - 设置媒体挂载路径

3. **验证服务**
   ```bash
   # 检查服务状态
   curl http://localhost:8091/health
   
   # 检查 SSL（如果启用）
   curl https://localhost:8095/health
   ```

4. **测试播放**
   - 在 Plex 中播放 Strm 文件
   - 观察是否通过 MediaLinker 进行了优化

### 高级配置示例

#### 多路径映射配置
```javascript
// config.js 示例
module.exports = {
  plex: {
    url: "http://192.168.1.100:32400",
    token: "your-plex-token"
  },
  alist: {
    url: "http://192.168.1.200:5244",
    token: "your-alist-token",
    sign: true,
    signExpireHours: 24
  },
  pathMappings: [
    {
      local: "/mnt/media/movies",
      remote: "/alist/movies"
    },
    {
      local: "/mnt/media/tv",
      remote: "/alist/tv"
    }
  ]
};
```

## 🔧 故障排除

### 常见问题解决

#### 🚨 服务启动失败

**症状**：插件状态显示"未运行"

**解决方案**：
```bash
# 1. 检查端口占用
lsof -i :8091

# 2. 查看插件日志
tail -f /path/to/moviepilot/logs/plugins/medialinker.log

# 3. 手动测试端口
telnet localhost 8091
```

#### 🎬 Strm 文件无法播放

**症状**：Plex 中 Strm 文件播放失败

**检查清单**：
- [ ] Plex Token 是否正确
- [ ] Alist 服务是否可访问
- [ ] 路径映射是否正确
- [ ] 网络连接是否正常

**调试命令**：
```bash
# 测试 Plex 连接
curl -H "X-Plex-Token: YOUR_TOKEN" "http://plex-server:32400/identity"

# 测试 Alist 连接
curl -H "Authorization: Bearer YOUR_TOKEN" "http://alist-server:5244/api/me"
```

#### 🔒 SSL 证书问题

**症状**：HTTPS 访问失败

**解决方案**：
```bash
# 检查证书有效性
openssl x509 -in /path/to/cert.pem -text -noout

# 测试 SSL 连接
openssl s_client -connect localhost:8095
```

### 性能优化建议

1. **启用缓存**
   ```javascript
   cache: {
     enabled: true,
     ttl: 3600,  // 1小时
     maxSize: 1000
   }
   ```

2. **调整并发数**
   ```javascript
   performance: {
     maxConcurrent: 10,
     timeout: 30000
   }
   ```

3. **优化日志级别**
   ```javascript
   logging: {
     level: "info",  // 生产环境建议使用 info
     maxFiles: 5,
     maxSize: "10m"
   }
   ```

## 📊 监控与维护

### 健康检查

插件提供了内置的健康检查端点：

```bash
# 基本健康检查
curl http://localhost:8091/health

# 详细状态信息
curl http://localhost:8091/status

# 性能指标
curl http://localhost:8091/metrics
```

### 日志管理

```bash
# 查看实时日志
tail -f /path/to/moviepilot/logs/plugins/medialinker.log

# 搜索错误日志
grep -i error /path/to/moviepilot/logs/plugins/medialinker.log

# 日志轮转（自动管理）
# 插件会自动管理日志文件大小和数量
```

## 🔄 更新与维护

### 自动更新

插件支持自动更新功能：
- 启动时检查新版本
- 自动下载和安装
- 备份旧版本以便回滚

### 手动更新

```bash
# 1. 停止服务
systemctl stop moviepilot

# 2. 备份配置
cp -r /path/to/plugins/medialinker /backup/

# 3. 更新插件代码
git pull origin main

# 4. 重启服务
systemctl start moviepilot
```

## 🤝 贡献指南

### 开发环境搭建

```bash
# 1. 克隆仓库
git clone https://github.com/your-repo/MoviePilot-Plugins.git

# 2. 安装依赖
cd MoviePilot-Plugins/plugins/medialinker
pip install -r requirements.txt

# 3. 运行测试
python -m pytest tests/
```

### 提交规范

- 使用语义化提交信息
- 添加适当的测试用例
- 更新相关文档
- 确保代码通过 lint 检查

### 报告问题

在提交 Issue 时，请包含：
- 详细的问题描述
- 复现步骤
- 系统环境信息
- 相关日志信息

## 📄 许可证

本项目基于 [MIT 许可证](LICENSE) 开源。

## 🙏 致谢

- [embyExternalUrl](https://github.com/chen3861229/embyExternalUrl) - 提供核心功能基础
- [MoviePilot](https://github.com/jxxghp/MoviePilot) - 优秀的媒体管理平台
- 所有贡献者和用户的支持

---

**如果这个插件对你有帮助，请考虑给项目一个 ⭐ Star！**