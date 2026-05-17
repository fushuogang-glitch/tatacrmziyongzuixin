import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import path from 'path';

const ts = Date.now();

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': path.resolve(__dirname, 'src') },
  },
  build: {
    rollupOptions: {
      output: {
        // 每次构建文件名带时间戳，彻底绕过浏览器缓存
        entryFileNames: `assets/[name]-${ts}-[hash].js`,
        chunkFileNames: `assets/[name]-${ts}-[hash].js`,
        assetFileNames: `assets/[name]-${ts}-[hash].[ext]`,
      },
    },
  },
  server: {
    port: 5174,
    proxy: {
      '/api':   { target: 'http://localhost:8000', changeOrigin: true },
      '/admin': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
});
