<template>
  <v-container>
    <v-form>
      <v-row>
        <v-col cols="12" md="6">
          <v-switch
            v-model="config.enabled"
            label="启用插件"
            hint="开启后插件将处于激活状态"
            persistent-hint
          />
        </v-col>
      </v-row>

      <v-row>
        <v-col cols="12" md="6">
          <v-text-field
            v-model="config.separator"
            label="默认分隔符"
            hint="请输入默认分隔符，如：. - _ 空格"
            persistent-hint
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-text-field
            v-model="config.custom_separator"
            label="自定义占位符分隔符"
            hint="请输入 customization 的分隔符，如：. - _ 空格，默认为 @"
            persistent-hint
          />
        </v-col>
      </v-row>

      <v-row>
        <v-col cols="12">
          <v-select
            v-model="config.separator_types"
            label="分隔符适用范围"
            :items="separatorTypes"
            multiple
            chips
            clearable
            hint="请选择分隔符适用范围"
            persistent-hint
          />
        </v-col>
      </v-row>

      <v-row>
        <v-col cols="12">
          <v-expansion-panels>
            <v-expansion-panel>
              <v-expansion-panel-title>自定义替换词</v-expansion-panel-title>
              <v-expansion-panel-text>
                <v-row v-for="(rule, index) in config.word_replacements" :key="index">
                  <v-col cols="5">
                    <v-text-field
                      v-model="rule.old"
                      label="原词"
                      hide-details
                    />
                  </v-col>
                  <v-col cols="5">
                    <v-text-field
                      v-model="rule.new"
                      label="替换词"
                      hide-details
                    />
                  </v-col>
                  <v-col cols="2" class="d-flex align-center">
                    <v-btn
                      icon="mdi-delete"
                      variant="text"
                      color="error"
                      @click="removeWordReplacement(index)"
                    />
                  </v-col>
                </v-row>
                <v-btn
                  prepend-icon="mdi-plus"
                  variant="tonal"
                  class="mt-4"
                  @click="addWordReplacement"
                >
                  添加替换规则
                </v-btn>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-col>
      </v-row>

      <v-row>
        <v-col cols="12">
          <v-expansion-panels>
            <v-expansion-panel>
              <v-expansion-panel-title>自定义重命名模板</v-expansion-panel-title>
              <v-expansion-panel-text>
                <v-row v-for="(template, index) in templateGroups" :key="index">
                  <v-col cols="4">
                    <v-text-field
                      v-model="template.name"
                      label="模板名称"
                      hide-details
                    />
                  </v-col>
                  <v-col cols="6">
                    <v-text-field
                      v-model="template.pattern"
                      label="模板格式"
                      hide-details
                    />
                  </v-col>
                  <v-col cols="2" class="d-flex align-center">
                    <v-btn
                      icon="mdi-delete"
                      variant="text"
                      color="error"
                      @click="removeTemplate(index)"
                    />
                  </v-col>
                </v-row>
                <v-btn
                  prepend-icon="mdi-plus"
                  variant="tonal"
                  class="mt-4"
                  @click="addTemplate"
                >
                  添加模板
                </v-btn>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-col>
      </v-row>
    </v-form>
  </v-container>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  config: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['update:config'])

const separatorTypes = [
  { title: 'title', value: 'title' },
  { title: 'en_title', value: 'en_title' },
  { title: 'original_title', value: 'original_title' },
  { title: 'name', value: 'name' },
  { title: 'en_name', value: 'en_name' },
  { title: 'original_name', value: 'original_name' },
  { title: 'resourceType', value: 'resourceType' },
  { title: 'effect', value: 'effect' },
  { title: 'edition', value: 'edition' },
  { title: 'videoFormat', value: 'videoFormat' },
  { title: 'videoCodec', value: 'videoCodec' },
  { title: 'audioCodec', value: 'audioCodec' }
]

const templateGroups = ref([])

watch(() => props.config, (newConfig) => {
  if (newConfig.template_groups) {
    templateGroups.value = Object.entries(newConfig.template_groups).map(([name, pattern]) => ({
      name,
      pattern
    }))
  }
}, { immediate: true })

const addWordReplacement = () => {
  if (!props.config.word_replacements) {
    props.config.word_replacements = []
  }
  props.config.word_replacements.push({ old: '', new: '' })
}

const removeWordReplacement = (index) => {
  props.config.word_replacements.splice(index, 1)
}

const addTemplate = () => {
  templateGroups.value.push({ name: '', pattern: '' })
  updateTemplateGroups()
}

const removeTemplate = (index) => {
  templateGroups.value.splice(index, 1)
  updateTemplateGroups()
}

const updateTemplateGroups = () => {
  const newTemplateGroups = {}
  templateGroups.value.forEach(template => {
    if (template.name && template.pattern) {
      newTemplateGroups[template.name] = template.pattern
    }
  })
  props.config.template_groups = newTemplateGroups
  emit('update:config', props.config)
}
</script>