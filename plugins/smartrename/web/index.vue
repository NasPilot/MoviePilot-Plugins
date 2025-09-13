<template>
  <div class="smart-rename">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>重命名规则配置</span>
        </div>
      </template>
      <el-form :model="renameConfig" label-width="120px">
        <el-form-item label="电影命名格式">
          <el-input v-model="renameConfig.movieFormat" placeholder="请输入电影重命名格式"/>
          <div class="format-hint">可用变量: {{title}}, {{year}}, {{part}}, {{videoFormat}}, {{fileExt}}</div>
        </el-form-item>
        <el-form-item label="剧集命名格式">
          <el-input v-model="renameConfig.tvFormat" placeholder="请输入剧集重命名格式"/>
          <div class="format-hint">可用变量: {{title}}, {{year}}, {{season}}, {{season_episode}}, {{episode}}, {{part}}, {{fileExt}}</div>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="saveConfig">保存配置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="box-card mt-4">
      <template #header>
        <div class="card-header">
          <span>文件列表</span>
          <el-button type="primary" size="small" @click="refreshList">刷新</el-button>
        </div>
      </template>
      <el-table :data="fileList" style="width: 100%">
        <el-table-column prop="originalName" label="原文件名" width="300"/>
        <el-table-column prop="newName" label="新文件名" width="300"/>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.status === 'success' ? 'success' : 'warning'">
              {{ scope.row.status === 'success' ? '成功' : '待处理' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="scope">
            <el-button size="small" @click="previewRename(scope.row)">预览</el-button>
            <el-button size="small" type="primary" @click="executeRename(scope.row)"
                       :disabled="scope.row.status === 'success'">重命名</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

// 重命名配置
const renameConfig = ref({
  movieFormat: '{{title}}{% if year %} ({{year}}){% endif %}/{{title}}{% if year %} ({{year}}){% endif %}{% if part %}-{{part}}{% endif %}{% if videoFormat %} - {{videoFormat}}{% endif %}{{fileExt}}',
  tvFormat: '{{title}}{% if year %} ({{year}}){% endif %}/Season {{season}}/{{title}} - {{season_episode}}{% if part %}-{{part}}{% endif %}{% if episode %} - 第 {{episode}} 集{% endif %}{{fileExt}}'
})

// 文件列表
const fileList = ref([])

// 获取配置
const getConfig = async () => {
  try {
    const response = await fetch('/api/v1/plugins/smartrename/config')
    const data = await response.json()
    renameConfig.value = data
  } catch (error) {
    ElMessage.error('获取配置失败')
  }
}

// 保存配置
const saveConfig = async () => {
  try {
    await fetch('/api/v1/plugins/smartrename/config', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(renameConfig.value)
    })
    ElMessage.success('保存成功')
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

// 刷新文件列表
const refreshList = async () => {
  try {
    const response = await fetch('/api/v1/plugins/smartrename/files')
    const data = await response.json()
    fileList.value = data
  } catch (error) {
    ElMessage.error('获取文件列表失败')
  }
}

// 预览重命名
const previewRename = async (file) => {
  try {
    const response = await fetch(`/api/v1/plugins/smartrename/preview/${file.id}`)
    const data = await response.json()
    file.newName = data.newName
  } catch (error) {
    ElMessage.error('预览失败')
  }
}

// 执行重命名
const executeRename = async (file) => {
  try {
    await fetch(`/api/v1/plugins/smartrename/rename/${file.id}`, {
      method: 'POST'
    })
    file.status = 'success'
    ElMessage.success('重命名成功')
  } catch (error) {
    ElMessage.error('重命名失败')
  }
}

onMounted(() => {
  getConfig()
  refreshList()
})
</script>

<style scoped>
.smart-rename {
  padding: 20px;
}

.box-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.format-hint {
  font-size: 12px;
  color: #666;
  margin-top: 4px;
}

.mt-4 {
  margin-top: 16px;
}
</style>