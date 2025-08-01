# 梅林路由Hosts插件

## 功能描述

定时将本地Hosts同步至华硕梅林路由器的/jffs/configs/hosts.add文件，支持智能合并、备份和密码/密钥认证。

## 主要优化内容

### 1. 添加SSH连接功能
- 支持通过SSH连接到梅林路由器
- 实现真正的远程文件操作，替代原有的模拟操作
- 添加连接超时和错误处理机制

### 2. 多种认证方式
- **密码认证**：使用用户名和密码登录
- **密钥认证**：使用SSH私钥文件认证
- **混合认证**：优先使用私钥，失败时回退到密码认证

### 3. 完善的错误处理
- 添加配置验证（IP地址、用户名等必填项检查）
- paramiko库依赖检查
- SSH连接失败重试机制
- 详细的日志记录

### 4. 智能合并功能
- **智能合并**：保留路由器现有hosts条目，只更新或添加本地新条目
- **去重处理**：自动去除重复的hosts条目
- **备份保护**：操作前自动备份现有配置

### 5. 安全性增强
- 自动备份现有hosts.add文件
- 安全的文件传输（SFTP）
- 连接后自动关闭SSH会话

### 6. 用户界面优化
- 添加路由器连接配置项
- 清晰的配置说明和提示
- 警告信息提醒用户注意事项

## 配置说明

### 必填配置
- **路由器IP地址**：梅林路由器的IP地址（如：192.168.1.1）
- **用户名**：路由器登录用户名（通常为admin）
- **密码** 或 **私钥文件路径**：至少配置一种认证方式

### 可选配置
- **SSH端口**：默认22
- **私钥文件路径**：如果使用密钥认证
- **忽略的IP或域名**：不需要同步的条目
- **执行周期**：cron表达式，默认每天早上6点

## 使用前准备

1. **开启梅林路由器SSH服务**
   - 登录路由器管理界面
   - 进入「系统管理」->「系统设置」
   - 开启「Enable SSH」

2. **确保网络连接正常**
   - MoviePilot服务器能够访问路由器IP
   - SSH端口未被防火墙阻挡

## 工作原理

1. 读取本地hosts文件（/etc/hosts 或 Windows系统hosts文件）
2. 过滤和格式化hosts条目（忽略IPv6、回环地址等）
3. 通过SSH连接到梅林路由器
4. 获取路由器现有的/jffs/configs/hosts.add文件内容
5. 智能合并本地hosts与远程hosts（保留现有条目，更新重复条目）
6. 备份现有的hosts.add文件
7. 写入合并后的hosts内容到hosts.add文件
8. 重启dnsmasq服务使配置生效
9. 关闭SSH连接

## 注意事项

- 插件采用智能合并策略，会保留路由器现有的hosts条目
- 建议先在测试环境验证功能正常后再在生产环境使用
- 如果使用密钥认证，请确保私钥文件路径正确且有读取权限
- 路由器重启后hosts配置会保持，但如果恢复出厂设置会丢失

## 版本历史

### v0.5
- 新增moviepilot域名过滤功能，自动过滤本地hosts中的moviepilot相关条目
- 保留注释行和空行，确保hosts文件格式完整性
- 添加详细的过滤日志记录，显示过滤前后的行数统计
- 优化hosts条目处理逻辑，提高同步准确性

### v0.4
- 增强SFTP连接稳定性，解决文件写入时的"EOF during negotiation"错误
- 添加SFTP操作重试机制，支持多次尝试和指数退避
- 优化文件写入方式，先写入临时文件再移动到目标位置
- 添加echo命令备用方案，当SFTP失败时自动切换
- 增加文件写入验证，确保内容正确性
- 改进资源清理机制，防止连接泄露

### v0.3
- 增强SSH连接稳定性，解决"EOF during negotiation"错误
- 新增连接重试机制，支持指数退避策略
- 优化连接参数，增加超时时间和banner处理
- 支持多种私钥格式（RSA、Ed25519、ECDSA、DSS）
- 改进错误分类和日志记录

### v0.2
- **新增智能合并功能**：保留路由器现有hosts条目，智能合并本地hosts
- **优化同步策略**：从覆盖模式改为合并模式，更安全可靠
- **改进代码结构**：重构核心逻辑，提高代码可维护性
- **增强错误处理**：更完善的异常捕获和错误提示

### v0.1
- 添加SSH连接功能，支持密码和SSH密钥认证
- 增强安全性和稳定性（自动备份、SFTP传输、重试机制）
- 优化配置界面，新增路由器IP、SSH端口、用户名、密码、私钥文件路径等配置项
- 技术改进：代码结构优化、配置验证、错误处理、日志输出