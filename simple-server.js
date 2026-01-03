const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const path = require('path');

const app = express();
const PORT = 5173;

// Serve static files from dist
app.use(express.static(path.join(__dirname, 'dist')));

// Proxy API calls to Flask backend
app.use('/data', createProxyMiddleware({ 
  target: 'http://192.168.10.50:5000',
  changeOrigin: true
}));

app.use('/progress', createProxyMiddleware({ 
  target: 'http://192.168.10.50:5000',
  changeOrigin: true
}));

app.use('/device_groups', createProxyMiddleware({ 
  target: 'http://192.168.10.50:5000',
  changeOrigin: true
}));

app.use('/scan', createProxyMiddleware({ 
  target: 'http://192.168.10.50:5000',
  changeOrigin: true
}));

app.use('/delete_selected', createProxyMiddleware({ 
  target: 'http://192.168.10.50:5000',
  changeOrigin: true
}));

app.use('/snmp_scan', createProxyMiddleware({ 
  target: 'http://192.168.10.50:5000',
  changeOrigin: true
}));

app.use('/ssh_scan', createProxyMiddleware({ 
  target: 'http://192.168.10.50:5000',
  changeOrigin: true
}));

app.use('/get_settings', createProxyMiddleware({ 
  target: 'http://192.168.10.50:5000',
  changeOrigin: true
}));

app.use('/save_settings', createProxyMiddleware({ 
  target: 'http://192.168.10.50:5000',
  changeOrigin: true
}));

app.use('/test_settings', createProxyMiddleware({ 
  target: 'http://192.168.10.50:5000',
  changeOrigin: true
}));

app.use('/get_combined_interfaces', createProxyMiddleware({ 
  target: 'http://192.168.10.50:5000',
  changeOrigin: true
}));

app.use('/get_ssh_cli_interfaces', createProxyMiddleware({ 
  target: 'http://192.168.10.50:5000',
  changeOrigin: true
}));

app.use('/power_history', createProxyMiddleware({ 
  target: 'http://192.168.10.50:5000',
  changeOrigin: true
}));

app.use('/topology_data', createProxyMiddleware({ 
  target: 'http://192.168.10.50:5000',
  changeOrigin: true
}));

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Server running on http://0.0.0.0:${PORT}`);
});
