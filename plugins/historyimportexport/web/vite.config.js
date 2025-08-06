import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import federation from '@originjs/vite-plugin-federation'

export default defineConfig({
  plugins: [
    vue(),
    federation({
      name: 'historyimportexport',
      filename: 'remoteEntry.js',
      exposes: {
        './Page': './src/Page.vue',
        './Config': './src/Config.vue'
      },
      shared: {
        vue: {
          singleton: true
        },
        vuetify: {
          singleton: true
        }
      }
    })
  ],
  build: {
    target: 'esnext',
    minify: false,
    cssCodeSplit: false,
    rollupOptions: {
      external: [],
      output: {
        minifyInternalExports: false
      }
    }
  },
  server: {
    port: 3001
  }
})