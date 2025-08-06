import { importShared } from './__federation_fn_import-95d4c87b.js';
import { _export_sfc } from './_plugin-vue_export-helper-e9a2c33e.js';

const _sfc_main = {
  name: 'HistoryEpisodeSortConfig',
  props: {
    value: {
      type: Object,
      default: () => ({
        enable_sort: false,
        tv_only: true
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
  const _component_v_alert = _resolveComponent("v-alert");
  const _component_v_form = _resolveComponent("v-form");

  return (_openBlock(), _createBlock(_component_v_form, null, {
    default: _withCtx(() => [
      _createVNode(_component_v_row, null, {
        default: _withCtx(() => [
          _createVNode(_component_v_col, {
            cols: "12",
            md: "6"
          }, {
            default: _withCtx(() => [
              _createVNode(_component_v_switch, {
                modelValue: $data.config.enable_sort,
                "onUpdate:modelValue": _cache[0] || (_cache[0] = $event => (($data.config.enable_sort) = $event)),
                label: "启用剧集排序",
                onChange: $options.updateConfig
              }, null, 8, ["modelValue", "onChange"])
            ]),
            _: 1
          }),
          _createVNode(_component_v_col, {
            cols: "12",
            md: "6"
          }, {
            default: _withCtx(() => [
              _createVNode(_component_v_switch, {
                modelValue: $data.config.tv_only,
                "onUpdate:modelValue": _cache[1] || (_cache[1] = $event => (($data.config.tv_only) = $event)),
                label: "仅处理电视剧",
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
                default: _withCtx(() => _cache[2] || (_cache[2] = [
                  _createTextVNode(" 功能说明：该插件会分析同一部电视剧的不同剧集，按照剧集编号重新排序整理时间，确保剧集按正确的时间顺序显示。 ", -1)
                ])),
                _: 1,
                __: [2]
              })
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
                type: "warning",
                variant: "tonal"
              }, {
                default: _withCtx(() => _cache[3] || (_cache[3] = [
                  _createTextVNode(" 注意：该操作会修改历史记录的整理时间，建议在执行前备份数据库。 ", -1)
                ])),
                _: 1,
                __: [3]
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
