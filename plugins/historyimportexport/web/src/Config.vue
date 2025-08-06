<template>
  <v-form>
    <v-row>
      <v-col cols="12" md="4">
        <v-switch
          v-model="config.enabled"
          label="启用插件"
          @change="updateConfig"
        ></v-switch>
      </v-col>
    </v-row>
    
    <v-row>
      <v-col cols="12">
        <v-text-field
          v-model="config.export_path"
          label="导出文件保存路径"
          placeholder="/tmp/history_export"
          @blur="updateConfig"
        ></v-text-field>
      </v-col>
    </v-row>
    
    <v-row>
      <v-col cols="12" md="6">
        <v-text-field
          v-model.number="config.time_interval"
          label="剧集时间间隔（分钟）"
          placeholder="30"
          type="number"
          @blur="updateConfig"
        ></v-text-field>
      </v-col>
      <v-col cols="12" md="6">
        <v-switch
          v-model="config.auto_sort"
          label="导入时自动按剧集排序"
          @change="updateConfig"
        ></v-switch>
      </v-col>
    </v-row>
    
    <v-row>
      <v-col cols="12">
        <v-alert type="info" variant="tonal">
          支持导出所有历史记录或按电视剧分别导出，导入时可自动按剧集顺序重新排列时间。
        </v-alert>
      </v-col>
    </v-row>
  </v-form>
</template>

<script>
export default {
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
        this.config = { ...newVal }
      },
      deep: true
    }
  },
  methods: {
    updateConfig() {
      this.$emit('input', this.config)
    }
  }
}
</script>