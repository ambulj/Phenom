import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import fs from 'fs';
import path from 'path';

function phenomDevTokenPlugin() {
  return {
    name: 'phenom-dev-token',
    configureServer(server: any) {
      server.middlewares.use('/api/dev-token', (_req: any, res: any) => {
        const appdata = process.env.APPDATA || '';
        const candidateFiles = [
          path.join(appdata, 'Phenom', '.session_token'),
          path.join(appdata, 'phenom-desktop', '.session_token'),
        ];
        let token = null;
        for (const f of candidateFiles) {
          if (fs.existsSync(f)) {
            token = fs.readFileSync(f, 'utf8').trim();
            break;
          }
        }
        res.setHeader('Content-Type', 'application/json');
        res.setHeader('Access-Control-Allow-Origin', '*');
        res.end(JSON.stringify({ token }));
      });
    }
  };
}

export default defineConfig({
  plugins: [react(), phenomDevTokenPlugin()],
  server: {
    port: 5173
  },
  base: './',
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/three')) {
            return 'vendor-three';
          }
          if (id.includes('node_modules/@fluentui')) {
            return 'vendor-fluent';
          }
          if (id.includes('node_modules/react') || id.includes('node_modules/scheduler')) {
            return 'vendor-react';
          }
        }
      }
    },
    chunkSizeWarningLimit: 1000
  }
});
