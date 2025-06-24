import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  root: './app',
  build: {
    outDir: '../build',
    emptyOutDir: true,
  },
  plugins: [react()],
  server: {
    open: true,
  },
});
