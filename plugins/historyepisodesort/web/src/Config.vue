<template>
  <v-form>
    <v-row>
      <v-col cols="12" md="6">
        <v-switch
          v-model="config.enable_sort"
          label="启用剧集排序"
          @change="updateConfig"
        ></v-switch>
      </v-col>
      <v-col cols="12" md="6">
        <v-switch
          v-model="config.tv_only"
          label="仅处理电视剧"
          @change="updateConfig"
        ></v-switch>
      </v-col>
    </v-row>
    
    <v-row>
      <v-col cols="12">
        <v-alert type="info" variant="tonal">
          功能说明：该插件会分析同一部电视剧的不同剧集，按照剧集编号重新排序整理时间，确保剧集按正确的时间顺序显示。
        </v-alert>
      </v-col>
    </v-row>
    
    <v-row>
      <v-col cols="12">
        <v-alert type="warning" variant="tonal">
          注意：该操作会修改历史记录的整理时间，建议在执行前备份数据库。
        </v-alert>
      </v-col>
    </v-row>
  </v-form>
</template>

<script>
export default {
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