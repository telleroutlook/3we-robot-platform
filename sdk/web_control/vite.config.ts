// SPDX-License-Identifier: Apache-2.0
import { defineConfig } from 'vite';

export default defineConfig({
  root: '.',
  build: {
    outDir: 'dist',
    target: 'es2022',
  },
  server: {
    port: 5173,
    open: true,
  },
});
