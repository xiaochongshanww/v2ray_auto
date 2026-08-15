// Renders an SVG file to a PNG using Electron's Chromium.
// Usage: npx electron scripts/svg-to-png.js [svgPath] [pngPath] [size]
//   svgPath (optional, default assets/icon.svg)
//   pngPath (optional, default assets/icon.png)
//   size    (optional, default 1024)
const { app, BrowserWindow } = require('electron')
const fs = require('node:fs')
const path = require('node:path')

const ASSETS = path.join(__dirname, '..', 'assets')
const SRC = path.join(ASSETS, 'icon.svg')
const OUT = path.join(ASSETS, 'icon.png')
const SIZE = 1024

app.whenReady().then(async () => {
  const svgPath = process.argv[2] || SRC
  const pngPath = process.argv[3] || OUT
  const size = parseInt(process.argv[4], 10) || SIZE

  const svg = fs.readFileSync(svgPath, 'utf8')
  const win = new BrowserWindow({
    width: size,
    height: size,
    show: false,
    useContentSize: true,
    backgroundColor: '#00000000',
    transparent: true,
    webPreferences: { offscreen: true },
  })
  win.setContentSize(size, size)
  const html = `<!doctype html><html><head><style>html,body{margin:0;padding:0;width:${size}px;height:${size}px;overflow:hidden;background:transparent}</style></head><body>${svg}</body></html>`
  await win.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(html)}`)
  await new Promise((resolve) => setTimeout(resolve, 400))
  const image = await win.webContents.capturePage()
  const captured = image.getSize()
  let buffer = image.toPNG()
  if (captured.width !== size || captured.height !== size) {
    const scale = size / Math.max(captured.width, captured.height)
    const resized = image.resize({
      width: Math.round(captured.width * scale),
      height: Math.round(captured.height * scale),
      quality: 'best',
    })
    buffer = resized.toPNG()
  }
  fs.writeFileSync(pngPath, buffer)
  console.log(`wrote ${pngPath} (${buffer.length} bytes, captured ${captured.width}x${captured.height} -> ${size}x${size})`)
  app.quit()
})
