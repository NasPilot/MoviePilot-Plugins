<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title class="text-h6">
            智能识别词
          </v-card-title>
          <v-card-text>
            <p>本插件通过分析整理记录，提取并优化媒体文件的识别词，提高识别准确率。</p>
            
            <v-alert
              v-if="!config.enabled"
              type="warning"
              class="mt-4"
            >
              插件当前未启用，请在配置页面开启。
            </v-alert>

            <!-- 统计信息 -->
            <v-row class="mt-4">
              <v-col cols="12" md="4">
                <v-card>
                  <v-card-text class="text-center">
                    <div class="text-h5">{{ stats.totalRules || 0 }}</div>
                    <div class="text-subtitle-1">识别规则总数</div>
                  </v-card-text>
                </v-card>
              </v-col>
              <v-col cols="12" md="4">
                <v-card>
                  <v-card-text class="text-center">
                    <div class="text-h5">{{ stats.processedFiles || 0 }}</div>
                    <div class="text-subtitle-1">已处理文件数</div>
                  </v-card-text>
                </v-card>
              </v-col>
              <v-col cols="12" md="4">
                <v-card>
                  <v-card-text class="text-center">
                    <div class="text-h5">{{ stats.successRate || '0%' }}</div>
                    <div class="text-subtitle-1">识别成功率</div>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>

            <!-- 最近处理记录 -->
            <v-card class="mt-4">
              <v-card-title>最近处理记录</v-card-title>
              <v-card-text>
                <v-table>
                  <thead>
                    <tr>
                      <th>时间</th>
                      <th>文件名</th>
                      <th>识别结果</th>
                      <th>状态</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="record in recentRecords" :key="record.id">
                      <td>{{ formatTime(record.time) }}</td>
                      <td>{{ record.filename }}</td>
                      <td>{{ record.result }}</td>
                      <td>
                        <v-chip
                          :color="record.status === 'success' ? 'success' : 'error'"
                          size="small"
                        >
                          {{ record.status === 'success' ? '成功' : '失败' }}
                        </v-chip>
                      </td>
                    </tr>
                  </tbody>
                </v-table>
              </v-card-text>
            </v-card>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const config = ref({
  enabled: false
})

const stats = ref({
  totalRules: 0,
  processedFiles: 0,
  successRate: '0%'
})

const recentRecords = ref([])

const formatTime = (time) => {
  return new Date(time).toLocaleString()
}

onMounted(async () => {
  // TODO: 从后端获取配置和统计数据
  // 示例数据
  recentRecords.value = [
    {
      id: 1,
      time: new Date(),
      filename: 'example.mkv',
      result: '示例电影.2023',
      status: 'success'
    }
  ]
})
</script>

<style scoped>
.v-card {
  border-radius: 8px;
}

.text-h5 {
  font-weight: 500;
}

.text-subtitle-1 {
  color: rgba(0, 0, 0, 0.6);
}
</style>