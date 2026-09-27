import react from '@vitejs/plugin-react';
import path from 'node:path';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@ghostrange/ui-3d': path.resolve(__dirname, '../../packages/ui-3d/src/index.ts'),
    },
  },
  server: {
    port: 5173,
  },
});
