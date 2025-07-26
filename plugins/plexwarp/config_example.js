// PlexWarp 配置示例文件
// 此文件展示配置结构，实际配置由插件自动生成为 constant.js
// 基于原MediaLinker配置简化，专注于Plex优化

// 必填项，根据实际情况修改下面的设置

// Plex服务器地址配置
// 容器环境下使用网关地址，宿主机环境使用局域网地址
const plexHost = "http://172.17.0.1:32400"; // 容器网关地址
// const plexHost = "http://10.0.0.3:32400"; // 局域网地址备选

// 媒体挂载路径配置
const mediaMountPath = ["/mnt"];

// 选填项，用不到保持默认即可

// Nginx端口配置
const nginxPort = 8091;
const sslPort = 8443;
const sslEnable = false;
const sslDomain = "";

// 自定义服务器URL（反代地址）
const customServerUrl = "";

// 日志配置
const logLevel = "info";

// 路由缓存配置
const routeCacheConfig = {
    enable: true,
    enableL2: false,
    keyExpression: "r.uri:r.args.path:r.args.mediaIndex:r.args.partIndex"
};

// 转码配置
const transcodeConfig = {
    enable: false
};

// 导出配置
export default {
    plexHost,
    mediaMountPath,
    nginxPort,
    sslPort,
    sslEnable,
    sslDomain,
    customServerUrl,
    logLevel,
    routeCacheConfig,
    transcodeConfig
};