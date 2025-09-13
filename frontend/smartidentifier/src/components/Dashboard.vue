<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-text>
            <v-row>
              <v-col cols="12" md="4">
                <v-card variant="outlined">
                  <v-card-text class="text-center">
                    <div class="text-h6 mb-2">插件状态</div>
                    <v-chip
                      :color="pluginEnabled ? 'success' : 'error'"
                      :text="pluginEnabled ? '运行中' : '已停止'"
                    />
                  </v-card-text>
                </v-card>
              </v-col>
              <v-col cols="12" md="4">
                <v-card variant="outlined">
                  <v-card-text class="text-center">
                    <div class="text-h6 mb-2">替换规则数</div>
                    <div class="text-h4">{{ wordReplacementsCount }}</div>
                  </v-card-text>
                </v-card>
              </v-col>
              <v-col cols="12" md="4">
                <v-card variant="outlined">
                  <v-card-text class="text-center">
                    <div class="text-h6 mb-2">重命名模板数</div>
                    <div class="text-h4">{{ templateGroupsCount }}</div>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  config: {
    type: Object,
    required: true
  }
})

const pluginEnabled = computed(() => props.config.enabled)

const wordReplacementsCount = computed(() => {
  return props.config.word_replacements?.length || 0
})

const templateGroupsCount = computed(() => {
  return props.config.template_groups ? Object.keys(props.config.template_groups).length : 0
})
</script>