const moduleMap = {
  './Config': () => Promise.resolve({ default: window.MerlinHostsConfig })
};

const get = (module) => {
  return moduleMap[module] ? moduleMap[module]() : Promise.reject(new Error(`Module ${module} not found`));
};

const init = (shared) => {
  // 初始化共享依赖
  console.log('MerlinHosts plugin initialized with shared dependencies:', shared);
};

// 导出联邦模块接口
window.merlinhosts = {
  get,
  init
};

export { get, init };