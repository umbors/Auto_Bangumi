import { resolve } from 'node:path';
import UnoCSS from 'unocss/vite';
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import AutoImport from 'unplugin-auto-import/vite';
import Components from 'unplugin-vue-components/vite';
import VueRouter from 'unplugin-vue-router/vite';
import { VueRouterAutoImports } from 'unplugin-vue-router';

// https://vitejs.dev/config/
export default defineConfig({
  base: './',
  plugins: [
    VueRouter({
      dts: 'types/dts/router-type.d.ts',
    }),
    vue({
      script: {
        defineModel: true,
      },
    }),
    UnoCSS(),
    AutoImport({
      imports: [
        'vue',
        'vitest',
        'pinia',
        '@vueuse/core',
        'vue-i18n',
        VueRouterAutoImports,
      ],
      dts: 'types/dts/auto-imports.d.ts',
      dirs: ['src/api', 'src/store', 'src/hooks', 'src/utils'],
    }),
    Components({
      dts: 'types/dts/components.d.ts',
      dirs: [
        'src/components',
        'src/components/basic',
        'src/components/layout',
        'src/components/setting',
      ],
    }),
  ],
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: '@import "./src/style/mixin.scss";',
      },
    },
  },
  build: {
    cssCodeSplit: false,
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      '#': resolve(__dirname, 'types'),
    },
  },
  server: {
    proxy: {
      '^/api/.*': 'http://127.0.0.1:7892',
    },
  },
});
