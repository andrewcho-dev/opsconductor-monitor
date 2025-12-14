import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    strictPort: true,
    proxy: {
      '/data': 'http://192.168.10.50:5000',
      '/progress': 'http://192.168.10.50:5000',
      '/scan': 'http://192.168.10.50:5000',
      '/scan_selected': 'http://192.168.10.50:5000',
      '/delete_selected': 'http://192.168.10.50:5000',
      '/delete_device': 'http://192.168.10.50:5000',
      '/snmp_scan': 'http://192.168.10.50:5000',
      '/ssh_scan': 'http://192.168.10.50:5000',
      '/device_groups': 'http://192.168.10.50:5000',
      '/get_settings': 'http://192.168.10.50:5000',
      '/save_settings': 'http://192.168.10.50:5000',
      '/test_settings': 'http://192.168.10.50:5000',
      '/get_combined_interfaces': 'http://192.168.10.50:5000',
      '/get_ssh_cli_interfaces': 'http://192.168.10.50:5000',
      '/power_history': 'http://192.168.10.50:5000',
      '/topology_data': 'http://192.168.10.50:5000',
      '/api/network-ranges': 'http://192.168.10.50:5000',
      '/api/custom-groups': 'http://192.168.10.50:5000',
      '/api/network-groups': 'http://192.168.10.50:5000',
      '/api/notify/test': 'http://192.168.10.50:5000',
      '/api/jobs/run': 'http://192.168.10.50:5000',
      '/poller/status': 'http://192.168.10.50:5000',
      '/poller/logs': 'http://192.168.10.50:5000',
      '/poller/discovery': 'http://192.168.10.50:5000',
      '/poller/interface': 'http://192.168.10.50:5000',
      '/poller/optical': 'http://192.168.10.50:5000',
      '/poller/run_all': 'http://192.168.10.50:5000',
      '/poller/statistics': 'http://192.168.10.50:5000',
      '/poller/logs/clear': 'http://192.168.10.50:5000',
      '/api/schema': 'http://192.168.10.50:5000',
      '/api/workflows': 'http://192.168.10.50:5000',
      '/api/devices': 'http://192.168.10.50:5000',
      '/api/groups': 'http://192.168.10.50:5000',
      '/api/alerts': 'http://192.168.10.50:5000',
      '/api/credentials': 'http://192.168.10.50:5000',
      '/api/logs': 'http://192.168.10.50:5000',
      '/api/system': 'http://192.168.10.50:5000',
    }
  },
  build: {
    outDir: '../dist',
    emptyOutDir: true,
  }
})
