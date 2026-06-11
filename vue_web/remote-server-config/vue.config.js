const { defineConfig } = require('@vue/cli-service')
module.exports = defineConfig({
  transpileDependencies: true,
  devServer: {
    port: 8080,
    allowedHosts: 'all',
    proxy: {
      '/api': { target: 'http://127.0.0.1:5000' },
      '/socket.io': { target: 'http://127.0.0.1:5000', ws: true },
    },
  },
})
