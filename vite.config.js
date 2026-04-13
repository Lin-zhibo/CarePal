import { defineConfig } from 'vite'
import uni from '@dcloudio/vite-plugin-uni'

// 开发环境请求会先命中 /api 代理，再转发到后端服务。
// 如果后端 IP 变更，请同步修改这里。
const DEV_BACKEND_TARGET = 'http://192.168.137.79:8000'
const DEV_YOLO_TARGET = 'http://127.0.0.1:8010'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    uni(),
  ],
  server: {
    proxy: {
      '/api': {
        target: DEV_BACKEND_TARGET,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      '/yoloapi': {
        target: DEV_YOLO_TARGET,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/yoloapi/, ''),
      },
    },
  },
})
