import { importShared } from './__federation_fn_import-95d4c87b.js';
import { _export_sfc } from './_plugin-vue_export-helper-e9a2c33e.js';

const _sfc_main = {
  name: 'HistoryImportExportConfig',
  props: {
    value: {
      type: Object,
      default: () => ({
        enabled: false,
        export_path: '/tmp/history_export',
        time_interval: 30,
        auto_sort: true
      })
    }
  },
  data() {
    return {
      config: { ...this.value }
    }
  },
  watch: {
    value: {
      handler(newVal) {
        this.config = { ...newVal };
      },
      deep: true
    }
  },
  methods: {
    updateConfig() {
      this.$emit('input', this.config);
    }
  }
};

const {resolveComponent:_resolveComponent,createVNode:_createVNode,withCtx:_withCtx,createTextVNode:_createTextVNode,openBlock:_openBlock,createBlock:_createBlock} = await importShared('vue');


function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
  const _component_v_switch = _resolveComponent("v-switch");
  const _component_v_col = _resolveComponent("v-col");
  const _component_v_row = _resolveComponent("v-row");
  const _component_v_text_field = _resolveComponent("v-text-field");
  const _component_v_alert = _resolveComponent("v-alert");
  const _component_v_form = _resolveComponent("v-form");

  return (_openBlock(), _createBlock(_component_v_form, null, {
    default: _withCtx(() => [
      _createVNode(_component_v_row, null, {
        default: _withCtx(() => [
          _createVNode(_component_v_col, {
            cols: "12",
            md: "4"
          }, {
            default: _withCtx(() => [
              _createVNode(_component_v_switch, {
                modelValue: $data.config.enabled,
                "onUpdate:modelValue": _cache[0] || (_cache[0] = $event => (($data.config.enabled) = $event)),
                label: "启用插件",
                onChange: $options.updateConfig
              }, null, 8, ["modelValue", "onChange"])
            ]),
            _: 1
          })
        ]),
        _: 1
      }),
      _createVNode(_component_v_row, null, {
        default: _withCtx(() => [
          _createVNode(_component_v_col, { cols: "12" }, {
            default: _withCtx(() => [
              _createVNode(_component_v_text_field, {
                modelValue: $data.config.export_path,
                "onUpdate:modelValue": _cache[1] || (_cache[1] = $event => (($data.config.export_path) = $event)),
                label: "导出文件保存路径",
                placeholder: "/tmp/history_export",
                onBlur: $options.updateConfig
              }, null, 8, ["modelValue", "onBlur"])
            ]),
            _: 1
          })
        ]),
        _: 1
      }),
      _createVNode(_component_v_row, null, {
        default: _withCtx(() => [
          _createVNode(_component_v_col, {
            cols: "12",
            md: "6"
          }, {
            default: _withCtx(() => [
              _createVNode(_component_v_text_field, {
                modelValue: $data.config.time_interval,
                "onUpdate:modelValue": _cache[2] || (_cache[2] = $event => (($data.config.time_interval) = $event)),
                modelModifiers: { number: true },
                label: "剧集时间间隔（分钟）",
                placeholder: "30",
                type: "number",
                onBlur: $options.updateConfig
              }, null, 8, ["modelValue", "onBlur"])
            ]),
            _: 1
          }),
          _createVNode(_component_v_col, {
            cols: "12",
            md: "6"
          }, {
            default: _withCtx(() => [
              _createVNode(_component_v_switch, {
                modelValue: $data.config.auto_sort,
                "onUpdate:modelValue": _cache[3] || (_cache[3] = $event => (($data.config.auto_sort) = $event)),
                label: "导入时自动按剧集排序",
                onChange: $options.updateConfig
              }, null, 8, ["modelValue", "onChange"])
            ]),
            _: 1
          })
        ]),
        _: 1
      }),
      _createVNode(_component_v_row, null, {
        default: _withCtx(() => [
          _createVNode(_component_v_col, { cols: "12" }, {
            default: _withCtx(() => [
              _createVNode(_component_v_alert, {
                type: "info",
                variant: "tonal"
              }, {
                default: _withCtx(() => _cache[4] || (_cache[4] = [
                  _createTextVNode(" 支持导出所有历史记录或按电视剧分别导出，导入时可自动按剧集顺序重新排列时间。 ", -1)
                ])),
                _: 1,
                __: [4]
              })
            ]),
            _: 1
          })
        ]),
        _: 1
      })
    ]),
    _: 1
  }))
}
const Config = /*#__PURE__*/_export_sfc(_sfc_main, [['render',_sfc_render]]);

export { Config as default };
