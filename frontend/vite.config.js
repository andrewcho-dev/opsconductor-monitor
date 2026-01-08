import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Backend API server
const API_SERVER = 'http://192.168.10.50:5000';

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    strictPort: true,
    proxy: {
      // ============================================================
      // OpenAPI 3.x Domain-Based Endpoints (Primary API)
      // These use /api prefix to avoid conflicts with frontend routes
      // ============================================================
      '/api/identity': API_SERVER,      // Authentication, users, roles
      '/api/inventory': API_SERVER,     // Devices, interfaces, topology
      '/api/monitoring': API_SERVER,    // Metrics, alerts, polling
      '/api/automation': API_SERVER,    // Workflows, jobs, scheduling
      '/api/integrations': API_SERVER,  // NetBox, PRTG, MCP
      '/api/system': API_SERVER,        // Settings, logs, health
      '/api/credentials': API_SERVER,   // Credential vault
      '/api/notifications': API_SERVER, // Notification channels
      '/api/admin': API_SERVER,         // Administrative operations
      '/auth': API_SERVER,          // Login/logout endpoints
      
      // ============================================================
      // MVP Alert Aggregation API
      // ============================================================
      '/api/v1': API_SERVER,        // Alerts, connectors, dependencies
      
      // ============================================================
      // WebSocket for Real-Time Updates
      // ============================================================
      '/ws': {
        target: API_SERVER,
        ws: true,
        changeOrigin: true,
      },
      
      // ============================================================
      // API Documentation
      // ============================================================
      '/api/docs': API_SERVER,
      '/api/redoc': API_SERVER,
      '/api/openapi.json': API_SERVER,
    }
  },
  build: {
    outDir: '../dist',
    emptyOutDir: true,
  }
})
