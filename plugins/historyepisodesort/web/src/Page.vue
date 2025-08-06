<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <h1 class="text-h4 mb-4">历史记录排序</h1>
      </v-col>
    </v-row>

    <!-- 操作按钮 -->
    <v-row>
      <v-col cols="12">
        <v-card class="mb-4">
          <v-card-title>
            <v-icon class="mr-2">mdi-sort</v-icon>
            排序操作
          </v-card-title>
          <v-card-text>
            <v-btn 
              color="primary" 
              @click="runOnce" 
              :loading="running"
              class="mr-2"
            >
              <v-icon left>mdi-play</v-icon>
              立即运行一次
            </v-btn>
            <v-btn 
              color="secondary" 
              @click="loadTvHistories" 
              :loading="loading"
            >
              <v-icon left>mdi-refresh</v-icon>
              刷新列表
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- 电视剧列表 -->
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <v-icon class="mr-2">mdi-television</v-icon>
            电视剧历史记录
            <v-spacer></v-spacer>
            <v-text-field
              v-model="search"
              append-icon="mdi-magnify"
              label="搜索电视剧"
              single-line
              hide-details
              density="compact"
              style="max-width: 300px;"
            ></v-text-field>
          </v-card-title>
          <v-card-text>
            <v-data-table
              v-model="selected"
              :headers="headers"
              :items="filteredTvHistories"
              :loading="loading"
              show-select
              item-value="tmdbid"
              class="elevation-1"
            >
              <template v-slot:item.poster_path="{ item }">
                <v-avatar size="40" class="my-2">
                  <v-img 
                    v-if="item.poster_path" 
                    :src="`https://image.tmdb.org/t/p/w92${item.poster_path}`"
                    :alt="item.title"
                  ></v-img>
                  <v-icon v-else>mdi-television</v-icon>
                </v-avatar>
              </template>
              
              <template v-slot:item.title="{ item }">
                <div>
                  <div class="font-weight-medium">{{ item.title }}</div>
                  <div class="text-caption text-grey">TMDB ID: {{ item.tmdbid }}</div>
                </div>
              </template>
              
              <template v-slot:item.episode_count="{ item }">
                <v-chip color="primary" size="small">
                  {{ item.episode_count }} 集
                </v-chip>
              </template>
              
              <template v-slot:item.season_count="{ item }">
                <v-chip color="secondary" size="small">
                  {{ item.season_count }} 季
                </v-chip>
              </template>
              
              <template v-slot:item.actions="{ item }">
                <v-btn 
                  icon 
                  size="small" 
                  color="primary" 
                  @click="sortSingle(item.tmdbid)"
                  :loading="sortingItems.includes(item.tmdbid)"
                >
                  <v-icon>mdi-sort-ascending</v-icon>
                </v-btn>
                <v-btn 
                  icon 
                  size="small" 
                  color="info" 
                  @click="viewDetails(item)"
                  class="ml-1"
                >
                  <v-icon>mdi-eye</v-icon>
                </v-btn>
              </template>
            </v-data-table>
            
            <div v-if="selected.length > 0" class="mt-4">
              <v-btn 
                color="success" 
                @click="sortSelected" 
                :loading="sortingSelected"
              >
                <v-icon left>mdi-sort</v-icon>
                排序选中的 {{ selected.length }} 部电视剧
              </v-btn>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- 详情对话框 -->
    <v-dialog v-model="detailDialog" max-width="800px">
      <v-card v-if="selectedTv">
        <v-card-title>
          <v-icon class="mr-2">mdi-information</v-icon>
          {{ selectedTv.title }} 详情
        </v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="12" md="4" v-if="selectedTv.poster_path">
              <v-img 
                :src="`https://image.tmdb.org/t/p/w300${selectedTv.poster_path}`"
                :alt="selectedTv.title"
                aspect-ratio="2/3"
                class="rounded"
              ></v-img>
            </v-col>
            <v-col cols="12" :md="selectedTv.poster_path ? 8 : 12">
              <v-list>
                <v-list-item>
                  <v-list-item-title>TMDB ID</v-list-item-title>
                  <v-list-item-subtitle>{{ selectedTv.tmdbid }}</v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <v-list-item-title>剧集数量</v-list-item-title>
                  <v-list-item-subtitle>{{ selectedTv.episode_count }} 集</v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <v-list-item-title>季数</v-list-item-title>
                  <v-list-item-subtitle>{{ selectedTv.season_count }} 季</v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <v-list-item-title>最后更新</v-list-item-title>
                  <v-list-item-subtitle>{{ formatDate(selectedTv.last_update) }}</v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </v-col>
          </v-row>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" @click="detailDialog = false">关闭</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

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
  name: 'HistoryEpisodeSortPage',
  data() {
    return {
      loading: false,
      running: false,
      sortingSelected: false,
      sortingItems: [],
      search: '',
      selected: [],
      tvHistories: [],
      detailDialog: false,
      selectedTv: null,
      headers: [
        { title: '海报', key: 'poster_path', sortable: false, width: '80px' },
        { title: '标题', key: 'title', sortable: true },
        { title: '剧集数', key: 'episode_count', sortable: true, width: '100px' },
        { title: '季数', key: 'season_count', sortable: true, width: '100px' },
        { title: '操作', key: 'actions', sortable: false, width: '120px' }
      ],
      snackbar: {
        show: false,
        message: '',
        color: 'success'
      }
    }
  },
  computed: {
    filteredTvHistories() {
      if (!this.search) return this.tvHistories
      return this.tvHistories.filter(tv => 
        tv.title.toLowerCase().includes(this.search.toLowerCase())
      )
    }
  },
  mounted() {
    this.loadTvHistories()
  },
  methods: {
    async loadTvHistories() {
      this.loading = true
      try {
        const response = await axios.get('/plugin/HistoryEpisodeSort/tv_histories')
        if (response.data.success) {
          this.tvHistories = response.data.data || []
        } else {
          this.showMessage(response.data.message || '加载失败', 'error')
        }
      } catch (error) {
        this.showMessage('加载失败：' + error.message, 'error')
      } finally {
        this.loading = false
      }
    },
    async runOnce() {
      this.running = true
      try {
        const response = await axios.post('/plugin/HistoryEpisodeSort/run_once')
        if (response.data.success) {
          this.showMessage('排序完成！', 'success')
          this.loadTvHistories()
        } else {
          this.showMessage(response.data.message || '排序失败', 'error')
        }
      } catch (error) {
        this.showMessage('排序失败：' + error.message, 'error')
      } finally {
        this.running = false
      }
    },
    async sortSelected() {
      if (this.selected.length === 0) {
        this.showMessage('请先选择要排序的电视剧', 'warning')
        return
      }
      
      this.sortingSelected = true
      try {
        const response = await axios.post('/plugin/HistoryEpisodeSort/sort_selected', {
          tmdbids: this.selected
        })
        if (response.data.success) {
          this.showMessage(`成功排序 ${this.selected.length} 部电视剧！`, 'success')
          this.selected = []
          this.loadTvHistories()
        } else {
          this.showMessage(response.data.message || '排序失败', 'error')
        }
      } catch (error) {
        this.showMessage('排序失败：' + error.message, 'error')
      } finally {
        this.sortingSelected = false
      }
    },
    async sortSingle(tmdbid) {
      this.sortingItems.push(tmdbid)
      try {
        const response = await axios.post('/plugin/HistoryEpisodeSort/sort_selected', {
          tmdbids: [tmdbid]
        })
        if (response.data.success) {
          this.showMessage('排序完成！', 'success')
          this.loadTvHistories()
        } else {
          this.showMessage(response.data.message || '排序失败', 'error')
        }
      } catch (error) {
        this.showMessage('排序失败：' + error.message, 'error')
      } finally {
        this.sortingItems = this.sortingItems.filter(id => id !== tmdbid)
      }
    },
    viewDetails(tv) {
      this.selectedTv = tv
      this.detailDialog = true
    },
    formatDate(dateString) {
      if (!dateString) return '未知'
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
.v-data-table {
  background: transparent;
}
</style>