// MediaLinker配置示例文件
// 此文件仅供参考，实际配置由插件自动生成

// Plex服务器地址
const plexHost = "http://localhost:32400";

// rclone挂载目录
const mediaMountPath = ["/mnt"];

// Alist地址
const alistAddr = "http://localhost:5244";

// Alist Token
const alistToken = "your-alist-token";

// Alist签名设置
const alistSignEnable = false;
const alistSignExpireTime = 12;

// Alist公网地址
const alistPublicAddr = "https://your-domain.com:5244";

// 字符串头配置
const strHead = {
  lanIp: ["172.", "10.", "192.", "[fd00:"],
  xEmbyClients: {
    seekBug: ["Emby for iOS"],
  },
  xUAs: {
    seekBug: ["Infuse", "VidHub", "SenPlayer"],
    clientsPC: ["EmbyTheater"],
    clients3rdParty: ["Fileball", "Infuse", "SenPlayer", "VidHub"],
    player3rdParty: ["dandanplay", "VLC", "MXPlayer", "PotPlayer"],
    blockDownload: ["Infuse-Download"],
    infuse: {
      direct: "Infuse-Direct",
      download: "Infuse-Download",
    },
  },
  "115": "115.com",
  ali: "aliyundrive.net",
  userIds: {
    mediaPathMappingGroup01: [],
    allowInteractiveSearch: [],
  },
  filePaths: {
    mediaMountPath: [],
    redirectStrmLastLinkRule: [],
    mediaPathMappingGroup01: [],
  },
};

// 路由缓存配置
const routeCacheConfig = {
  enable: true,
  enableL2: false,
  keyExpression: "r.uri:r.args.path:r.args.mediaIndex:r.args.partIndex",
};

// 符号链接规则
const symlinkRule = [
  // [0, "/mnt/sda1"],
];

// 路由规则
const routeRule = [
  // ["filePath", 0, "/mnt/sda1"],
  // ["filePath", 1, ".mp3"],
  // ["filePath", 2, "Google"],
  // ["alistRes", 2, "/NAS/"],
];

// 路径映射
const mediaPathMapping = [
  // [0, 0, "/aliyun-01", "/aliyun-02"],
  // [0, 2, "http:", "https:"],
  // [0, 2, ":5244", "/alist"],
];

// Alist原始URL映射
const alistRawUrlMapping = [
  // [0, 0, "/alias/movies", "/aliyun-01"],
];

// 重定向Strm最后链接规则
const redirectStrmLastLinkRule = [
  [0, strHead.lanIp.map(s => "http://" + s)],
  // [0, alistAddr],
];

// 客户端自请求Alist规则
const clientSelfAlistRule = [
  [2, strHead["115"], alistPublicAddr],
];

// 导出配置
module.exports = {
  plexHost,
  mediaMountPath,
  alistAddr,
  alistToken,
  alistSignEnable,
  alistSignExpireTime,
  alistPublicAddr,
  strHead,
  routeCacheConfig,
  symlinkRule,
  routeRule,
  mediaPathMapping,
  alistRawUrlMapping,
  redirectStrmLastLinkRule,
  clientSelfAlistRule,
};