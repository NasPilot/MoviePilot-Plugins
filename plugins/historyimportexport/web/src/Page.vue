<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <h1 class="text-h4 mb-4">历史记录导入导出</h1>
      </v-col>
    </v-row>

    <!-- 导出功能 -->
    <v-row>
      <v-col cols="12" md="6">
        <v-card class="mb-4">
          <v-card-title>
            <v-icon class="mr-2">mdi-export</v-icon>
            导出历史记录
          </v-card-title>
          <v-card-text>
            <v-btn 
              color="primary" 
              @click="exportAll" 
              :loading="exporting"
              class="mb-2 mr-2"
            >
              <v-icon left>mdi-download</v-icon>
              导出所有记录
            </v-btn>
            <v-btn 
              color="secondary" 
              @click="exportByTv" 
              :loading="exportingTv"
              class="mb-2"
            >
              <v-icon left>mdi-television</v-icon>
              按电视剧导出
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- 导入功能 -->
      <v-col cols="12" md="6">
        <v-card class="mb-4">
          <v-card-title>
            <v-icon class="mr-2">mdi-import</v-icon>
            导入历史记录
          </v-card-title>
          <v-card-text>
            <div 
              class="file-upload-area"
              :class="{ 'dragover': isDragOver }"
              @drop="handleDrop"
              @dragover.prevent="isDragOver = true"
              @dragleave="isDragOver = false"
              @click="$refs.fileInput.click()"
            >
              <v-icon size="48" color="grey">mdi-cloud-upload</v-icon>
              <p class="mt-2">点击或拖拽文件到此处上传</p>
              <p class="text-caption text-grey">支持 JSON 格式的历史记录文件</p>
            </div>
            <input 
              ref="fileInput" 
              type="file" 
              accept=".json" 
              @change="handleFileSelect" 
              style="display: none"
            >
            <v-btn 
              v-if="selectedFile" 
              color="success" 
              @click="importHistory" 
              :loading="importing"
              class="mt-3"
              block
            >
              <v-icon left>mdi-upload</v-icon>
              导入 {{ selectedFile.name }}
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- 导出文件列表 -->
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <v-icon class="mr-2">mdi-file-multiple</v-icon>
            导出文件列表
            <v-spacer></v-spacer>
            <v-btn icon @click="loadExportFiles">
              <v-icon>mdi-refresh</v-icon>
            </v-btn>
          </v-card-title>
          <v-card-text>
            <v-list v-if="exportFiles.length > 0" class="file-list">
              <v-list-item 
                v-for="file in exportFiles" 
                :key="file.filename"
                class="border-b"
              >
                <v-list-item-content>
                  <v-list-item-title>{{ file.filename }}</v-list-item-title>
                  <v-list-item-subtitle>
                    大小: {{ formatFileSize(file.size) }} | 
                    修改时间: {{ formatDate(file.mtime) }}
                  </v-list-item-subtitle>
                </v-list-item-content>
                <v-list-item-action>
                  <v-btn 
                    icon 
                    color="primary" 
                    @click="downloadFile(file.filename)"
                  >
                    <v-icon>mdi-download</v-icon>
                  </v-btn>
                </v-list-item-action>
              </v-list-item>
            </v-list>
            <v-alert v-else type="info" variant="tonal">
              暂无导出文件
            </v-alert>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- 消息提示 -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color">
      {{ snackbar.message }}
      <template v-slot:actions>
        <v-btn variant="text" @click="snackbar.show = false">
          关闭
        </v-btn>
      </template>
    </v-snackbar>
  </v-container>
</template>

<script>
import axios from 'axios'

export default {
  name: 'HistoryImportExportPage',
  data() {
    return {
      exporting: false,
      exportingTv: false,
      importing: false,
      isDragOver: false,
      selectedFile: null,
      exportFiles: [],
      snackbar: {
        show: false,
        message: '',
        color: 'success'
      }
    }
  },
  mounted() {
    this.loadExportFiles()
  },
  methods: {
    async exportAll() {
      this.exporting = true
      try {
        const response = await axios.post('/plugin/HistoryImportExport/export_all')
        if (response.data.success) {
          this.showMessage('导出成功！', 'success')
          this.loadExportFiles()
        } else {
          this.showMessage(response.data.message || '导出失败', 'error')
        }
      } catch (error) {
        this.showMessage('导出失败：' + error.message, 'error')
      } finally {
        this.exporting = false
      }
    },
    async exportByTv() {
      this.exportingTv = true
      try {
        const response = await axios.post('/plugin/HistoryImportExport/export_tv')
        if (response.data.success) {
          this.showMessage('按电视剧导出成功！', 'success')
          this.loadExportFiles()
        } else {
          this.showMessage(response.data.message || '导出失败', 'error')
        }
      } catch (error) {
        this.showMessage('导出失败：' + error.message, 'error')
      } finally {
        this.exportingTv = false
      }
    },
    async importHistory() {
      if (!this.selectedFile) return
      
      this.importing = true
      try {
        const formData = new FormData()
        formData.append('file', this.selectedFile)
        
        const response = await axios.post('/plugin/HistoryImportExport/import_history', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        })
        
        if (response.data.success) {
          this.showMessage('导入成功！', 'success')
          this.selectedFile = null
        } else {
          this.showMessage(response.data.message || '导入失败', 'error')
        }
      } catch (error) {
        this.showMessage('导入失败：' + error.message, 'error')
      } finally {
        this.importing = false
      }
    },
    async loadExportFiles() {
      try {
        const response = await axios.get('/plugin/HistoryImportExport/list_exports')
        if (response.data.success) {
          this.exportFiles = response.data.files || []
        }
      } catch (error) {
        console.error('加载文件列表失败：', error)
      }
    },
    downloadFile(filename) {
      window.open(`/plugin/HistoryImportExport/download/${filename}`, '_blank')
    },
    handleDrop(event) {
      event.preventDefault()
      this.isDragOver = false
      const files = event.dataTransfer.files
      if (files.length > 0) {
        this.selectedFile = files[0]
      }
    },
    handleFileSelect(event) {
      const files = event.target.files
      if (files.length > 0) {
        this.selectedFile = files[0]
      }
    },
    formatFileSize(bytes) {
      if (bytes === 0) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    },
    formatDate(dateString) {
      return new Date(dateString).toLocaleString('zh-CN')
    },
    showMessage(message, color = 'success') {
      this.snackbar.message = message
      this.snackbar.color = color
      this.snackbar.show = true
    }
  }
}
</script>

<style scoped>
.file-upload-area {
  border: 2px dashed #ccc;
  border-radius: 8px;
  padding: 40px;
  text-align: center;
  transition: border-color 0.3s;
  cursor: pointer;
}

.file-upload-area.dragover {
  border-color: #1976d2;
  background-color: rgba(25, 118, 210, 0.1);
}

.file-list {
  max-height: 300px;
  overflow-y: auto;
}

.border-b {
  border-bottom: 1px solid rgba(255, 255, 255, 0.12);
}
</style>