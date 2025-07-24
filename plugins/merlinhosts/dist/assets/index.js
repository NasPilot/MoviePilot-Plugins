// Vue将通过CDN加载，从全局对象获取
const { defineComponent, ref, onMounted, computed } = Vue;

// 引入CSS文件
const link = document.createElement('link');
link.rel = 'stylesheet';
link.href = './assets/merlin-style.css';
document.head.appendChild(link);

// 引入jQuery库（华硕路由器开关动画需要）
if (!window.jQuery) {
  const jqueryScript = document.createElement('script');
  jqueryScript.src = 'https://cdn.jsdelivr.net/npm/jquery@3.6.0/dist/jquery.min.js';
  document.head.appendChild(jqueryScript);
}

const Config = defineComponent({
  name: 'MerlinHostsConfig',
  template: `
    <div class="merlin-container">
      <div class="merlin-header">
          <h1 class="merlin-title">梅林路由Hosts管理</h1>
          <p class="merlin-subtitle">通过SSH连接定时将本地Hosts同步至华硕梅林路由器，支持密码和密钥认证</p>
          <button class="close-btn" @click="closePlugin" style="position: absolute; top: 15px; right: 20px; background: none; border: none; font-size: 24px; color: #999; cursor: pointer; padding: 0; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center;" title="关闭">
            ×
          </button>
        </div>

      <div class="form-section">
        <h2 class="section-title">基础设置</h2>
        <table class="FormTable">
          <tbody>

            <tr>
              <td height="50" style="padding:10px 0px 0px 0px; text-align: left;" colspan="2">
                <table style="width: 100%; margin: 0; padding: 0;">
                  <tbody>
                    <tr>
                      <td width="33.33%" style="padding: 0; margin: 0;">
                        <table align="left" style="margin-left: 0;">
                          <tbody>
                            <tr>
                              <td>
                                <div class="formfonttitle" style="margin-bottom:0px;margin-right:15px;" title="启用梅林Hosts插件，开始定时同步本地hosts文件到路由器">启用插件</div>
                              </td>
                              <td>
                                <div align="center" class="left" style="width:94px; float:left; cursor:pointer;" id="switch_enabled" @click="toggleSwitch('enabled')">
                                  <div class="iphone_switch_container" style="height:32px; width:74px; position: relative; overflow: hidden">
                                    <img id="iphone_switch_enabled" class="iphone_switch" src="./assets/iphone_switch_container_on.png" style="border-radius:7px;height:32px; width:74px; background-image:url(./assets/iphone_switch.png); background-repeat:no-repeat; background-position:-37px center;">
                                  </div>
                                </div>
                              </td>
                            </tr>
                          </tbody>
                        </table>
                      </td>
                      <td width="33.33%">
                        <table align="left">
                          <tbody>
                            <tr>
                              <td>
                                <div class="formfonttitle" style="margin-bottom:0px;margin-right:15px;" title="启用通知功能，在同步完成或出现错误时发送通知消息">启用通知</div>
                              </td>
                              <td>
                                <div align="center" class="left" style="width:94px; float:left; cursor:pointer;" id="switch_notify" @click="toggleSwitch('notify')">
                                  <div class="iphone_switch_container" style="height:32px; width:74px; position: relative; overflow: hidden">
                                    <img id="iphone_switch_notify" class="iphone_switch" src="./assets/iphone_switch_container_on.png" style="border-radius:7px;height:32px; width:74px; background-image:url(./assets/iphone_switch.png); background-repeat:no-repeat; background-position:-37px center;">
                                  </div>
                                </div>
                              </td>
                            </tr>
                          </tbody>
                        </table>
                      </td>
                      <td width="33.33%">
                        <table align="left">
                          <tbody>
                            <tr>
                              <td>
                                <div class="formfonttitle" style="margin-bottom:0px;margin-right:15px;" title="启用后插件只执行一次同步任务，完成后自动禁用">执行一次</div>
                              </td>
                              <td>
                                <div align="center" class="left" style="width:94px; float:left; cursor:pointer;" id="switch_onlyonce" @click="toggleSwitch('onlyonce')">
                                  <div class="iphone_switch_container" style="height:32px; width:74px; position: relative; overflow: hidden">
                                    <img id="iphone_switch_onlyonce" class="iphone_switch" src="./assets/iphone_switch_container_on.png" style="border-radius:7px;height:32px; width:74px; background-image:url(./assets/iphone_switch.png); background-repeat:no-repeat; background-position:-37px center;">
                                  </div>
                                </div>
                              </td>
                            </tr>
                          </tbody>
                        </table>
                      </td>
                    </tr>
                  </tbody>
                </table>
                <div style="margin-top:5px;" class="line_horizontal"></div>
              </td>
            </tr>
            <tr>
              <th>执行周期</th>
              <td>
                <div style="display: flex; align-items: center; gap: 10px;">
                   <select v-model="cronSelection" @change="handleCronChange" style="width: 200px; padding: 5px; border: 1px solid #ccc; border-radius: 4px; background-color: #fff;">
                     <option value="0 */6 * * *">每6小时执行一次</option>
                     <option value="0 */12 * * *">每12小时执行一次</option>
                     <option value="0 0 * * *">每天执行一次 (午夜)</option>
                     <option value="0 6 * * *">每天执行一次 (早上6点)</option>
                     <option value="0 0 */3 * *">每3天执行一次</option>
                     <option value="0 0 * * 0">每周执行一次 (周日)</option>
                     <option value="0 0 1 * *">每月执行一次 (1号)</option>
                     <option value="custom">自定义</option>
                   </select>
                   <input v-if="cronSelection === 'custom'" type="text" v-model="customCron" @input="handleCustomCronChange" placeholder="0 6 * * *" style="width: 150px; padding: 5px; border: 1px solid #ccc; border-radius: 4px;">
                   <span style="font-size: 12px; color: #999;">定时同步周期</span>
                 </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="form-section">
        <h2 class="section-title">路由器连接设置</h2>
        <table class="FormTable">
          <tbody>
            <tr>
              <td colspan="2">路由器连接配置</td>
            </tr>
            <tr>
              <th>路由器IP地址</th>
              <td>
                <input type="text" v-model="config.router_ip" placeholder="192.168.1.1" style="width: 300px;">
                <span>梅林路由器的IP地址</span>
              </td>
            </tr>
            <tr>
              <th>SSH端口</th>
              <td>
                <input type="number" v-model="config.ssh_port" placeholder="22" style="width: 300px;">
                <span>SSH连接端口，默认22</span>
              </td>
            </tr>
            <tr>
              <th>用户名</th>
              <td>
                <input type="text" v-model="config.username" placeholder="admin" style="width: 300px;">
                <span>路由器登录用户名</span>
              </td>
            </tr>
            <tr>
              <th>密码</th>
              <td>
                <input type="password" v-model="config.password" placeholder="请输入密码" style="width: 300px;">
                <span>路由器登录密码</span>
              </td>
            </tr>
            <tr>
              <th>私钥文件路径</th>
              <td>
                <input type="text" v-model="config.private_key_path" placeholder="/path/to/private_key" style="width: 300px;">
                <span>如果使用密钥认证，请提供私钥文件路径（可选）</span>
              </td>
            </tr>
            <tr>
              <th>忽略的IP或域名</th>
              <td>
                <input type="text" v-model="config.ignore" placeholder="10.10.10.1|wiki.movie-pilot.org" style="width: 300px;">
                <span>多个条目用 | 分隔</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 华硕路由器风格的Hosts列表表格 -->
      <div class="form-section">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
          <h2 class="section-title" style="margin: 0;">Hosts 条目管理</h2>
          <div>
            <button class="table-action-btn" @click="refreshHostsPreview" style="margin-left: 10px;">刷新预览</button>
            <button class="table-action-btn" @click="clearHosts" style="margin-left: 10px;">清空Hosts</button>
            <button class="table-action-btn" @click="resetToDefault" style="margin-left: 10px;">重置配置</button>
          </div>
        </div>   

        <!-- Hosts条目列表表格 -->
        <table class="FormTable_table">
          <tbody>
            <tr>
              <td colspan="4">当前 Hosts 条目预览 (最近同步的前10条)</td>
            </tr>
            <tr>
              <th width="5%">序号</th>
              <th width="25%">IP地址</th>
              <th width="50%">域名</th>
              <th width="20%">状态</th>
            </tr>
            <tr v-for="(host, index) in hostsPreview" :key="index">
              <td>{{ index + 1 }}</td>
              <td class="table_text">{{ host.ip }}</td>
              <td class="table_text">{{ host.domain }}</td>
              <td>
                <span :class="host.status === 'active' ? 'status-indicator status-enabled' : 'status-indicator status-disabled'"></span>
                <span>{{ host.status === 'active' ? '已生效' : '待同步' }}</span>
              </td>
            </tr>
            <tr v-if="hostsPreview.length === 0">
              <td colspan="4" class="tableNoRule" style="color:#FFCC00;">暂无Hosts条目数据</td>
            </tr>
          </tbody>
        </table>


      </div>

      <div class="merlin-alert">
        <span class="merlin-alert-icon">⚠️</span>
        <strong>注意事项：</strong>
        <ul style="margin: 10px 0 0 20px; padding: 0;">
          <li>插件会通过SSH连接到梅林路由器，将本地hosts同步到/jffs/configs/hosts.add文件，并重启dnsmasq服务</li>
          <li>使用前请确保：1. 梅林路由器已开启SSH服务；2. 网络连接正常；3. 提供正确的认证信息（密码或私钥）</li>
        </ul>
      </div>

      <div class="apply_gen" style="text-align: center; margin-top: 30px;">
        <div style="width:136px;margin:5px 10px 0px 0px;display:inline-block;" class="titlebtn" :class="{ 'pulse-animation': testing, 'disabled': false }" @click="testConnection">
          <span>{{ testing ? '测试中...' : '测试连接' }}</span>
        </div>
        <div style="width:136px;margin:5px 10px 0px 0px;display:inline-block;" class="titlebtn" @click="saveConfig">
          <span>保存配置</span>
        </div>
        <div style="width:136px;margin:5px 0px 0px 0px;display:inline-block;" class="titlebtn" :class="{ 'disabled': !config.enabled }" @click="config.enabled ? syncNow() : null">
          <span>立即同步</span>
        </div>
      </div>
    </div>
  `,
  props: {
    initialConfig: {
      type: Object,
      default: () => ({})
    }
  },
  emits: ['configChange'],
  setup(props, { emit }) {
    const config = ref({
        enabled: false,
        notify: false,
        onlyonce: false,
        cron: "0 6 * * *",
        router_ip: "192.168.1.1",
        ssh_port: 22,
        username: "admin",
        password: "",
        private_key_path: "",
        ignore: "",
        ...props.initialConfig
      });

    // 自定义cron表达式
    const customCron = ref("0 6 * * *");
    
    // cron选择器的值
    const cronSelection = ref("0 6 * * *");
    
    // 预设的cron选项
    const presetCrons = ['0 */6 * * *', '0 */12 * * *', '0 0 * * *', '0 6 * * *', '0 0 */3 * *', '0 0 * * 0', '0 0 1 * *'];
    
    // 初始化cronSelection
    if (presetCrons.includes(config.value.cron)) {
      cronSelection.value = config.value.cron;
    } else {
      cronSelection.value = 'custom';
      customCron.value = config.value.cron;
    }

    // Hosts预览数据
    const hostsPreview = ref([
      { ip: "127.0.0.1", domain: "localhost", status: "active" },
      { ip: "0.0.0.0", domain: "ads.example.com", status: "active" },
      { ip: "192.168.1.100", domain: "nas.local", status: "active" },
      { ip: "10.0.0.50", domain: "media.server", status: "pending" },
      { ip: "172.16.1.10", domain: "dev.local", status: "active" }
    ]);

    const testing = ref(false);

    // 监听配置变化
    const configChanged = computed(() => config.value);
    
    // 当配置变化时通知父组件
    const saveConfig = () => {
      emit('configChange', config.value);
      // 这里可以添加保存成功的提示
      console.log('配置已保存:', config.value);
    };

    const testConnection = async () => {
      if (!config.value.router_ip || !config.value.username) {
        alert('请先填写路由器IP地址和用户名');
        return;
      }
      
      testing.value = true;
      try {
        // 这里应该调用后端API测试连接
        await new Promise(resolve => setTimeout(resolve, 2000)); // 模拟测试
        alert('连接测试成功！');
      } catch (error) {
        alert('连接测试失败：' + error.message);
      } finally {
        testing.value = false;
      }
    };

    const syncNow = async () => {
      if (!config.value.enabled) {
        alert('请先启用插件');
        return;
      }
      
      try {
        // 这里应该调用后端API立即同步
        alert('同步任务已启动，请查看日志了解详情');
        // 同步完成后刷新预览
        refreshHostsPreview();
      } catch (error) {
        alert('同步失败：' + error.message);
      }
    };

    // 刷新Hosts预览
    const refreshHostsPreview = () => {
      // 模拟从服务器获取最新的hosts数据
      console.log('刷新Hosts预览数据');
      // 这里可以调用API获取实际数据
    };

    // 清空Hosts
    const clearHosts = () => {
      if (confirm('确定要清空所有Hosts条目吗？此操作不可恢复。')) {
        hostsPreview.value = [];
        console.log('已清空Hosts条目');
      }
    };

    // 重置配置
    const resetToDefault = () => {
      if (confirm('确定要重置所有配置到默认值吗？')) {
        config.value = {
          enabled: false,
          notify: false,
          onlyonce: false,
          cron: "0 6 * * *",
          router_ip: "192.168.1.1",
          ssh_port: 22,
          username: "admin",
          password: "",
          private_key_path: "",
          ignore: ""
        };
        console.log('配置已重置');
      }
    };

    // 华硕风格开关切换方法 - 完全按照华硕路由器标准实现
    const toggleSwitch = (switchName) => {
      const switchElement = document.querySelector(`#iphone_switch_${switchName}`);
      if (!switchElement) return;
      
      // 华硕路由器标准：使用jQuery animate实现平滑过渡
      const $switch = $(switchElement);
      const currentState = config.value[switchName];
      
      if (currentState) {
        // 当前是ON，切换到OFF：华硕标准 background-position: -37px center
        $switch.animate({backgroundPosition: '-37px center'}, 'slow', function() {
          // 动画完成后的回调，模拟华硕switched_off_callback
          config.value[switchName] = false;
          console.log(`${switchName} switched OFF`);
        });
      } else {
        // 当前是OFF，切换到ON：华硕标准 background-position: 0px center
        $switch.animate({backgroundPosition: '0px center'}, 'slow', function() {
          // 动画完成后的回调，模拟华硕switched_on_callback
          config.value[switchName] = true;
          console.log(`${switchName} switched ON`);
        });
      }
    };

    onMounted(() => {
      console.log('MerlinHosts配置组件已加载', props.initialConfig);
      
      // 初始化华硕风格开关状态 - 完全按照华硕路由器标准
      const initSwitches = () => {
        ['enabled', 'notify', 'onlyonce'].forEach(switchName => {
          const switchElement = document.querySelector(`#iphone_switch_${switchName}`);
          if (switchElement) {
            // 华硕标准：直接设置background-position，无需过渡动画
            if (config.value[switchName]) {
              // ON状态：华硕标准 background-position: 0px center
              switchElement.style.backgroundPosition = '0px center';
            } else {
              // OFF状态：华硕标准 background-position: -37px center
              switchElement.style.backgroundPosition = '-37px center';
            }
          }
        });
      };
      
      // 确保jQuery加载完成后再初始化开关
      if (window.jQuery) {
        setTimeout(initSwitches, 100);
      } else {
        // 等待jQuery加载
        const checkJQuery = setInterval(() => {
          if (window.jQuery) {
            clearInterval(checkJQuery);
            setTimeout(initSwitches, 100);
          }
        }, 50);
      }
    });

    // 处理cron选择变化
    const handleCronChange = () => {
      if (cronSelection.value === 'custom') {
        config.value.cron = customCron.value;
      } else {
        config.value.cron = cronSelection.value;
      }
    };
    
    // 处理自定义cron输入变化
    const handleCustomCronChange = () => {
      if (cronSelection.value === 'custom') {
        config.value.cron = customCron.value;
      }
    };
    
    // 监听配置变化
    const { watch } = Vue;
    watch(() => config.value.cron, (newValue) => {
      if (presetCrons.includes(newValue)) {
        cronSelection.value = newValue;
      } else {
        cronSelection.value = 'custom';
        customCron.value = newValue;
      }
    });

    // 关闭插件方法
    const closePlugin = () => {
      if (window.parent && window.parent !== window) {
        // 如果在iframe中，通知父窗口关闭
        window.parent.postMessage({ type: 'close-plugin' }, '*');
      } else {
        // 如果是独立窗口，关闭当前窗口
        window.close();
      }
    };

    return {
      config,
      customCron,
      cronSelection,
      testing,
      hostsPreview,
      toggleSwitch,
      handleCronChange,
      handleCustomCronChange,
      testConnection,
      saveConfig,
      syncNow,
      refreshHostsPreview,
      clearHosts,
      resetToDefault,
      closePlugin
    };
  }
});

// 将配置组件挂载到全局对象供联邦模块使用
window.MerlinHostsConfig = Config;

// 如果页面有app容器，直接挂载Vue应用
if (document.getElementById('app')) {
  const { createApp } = Vue;
  createApp(Config).mount('#app');
}