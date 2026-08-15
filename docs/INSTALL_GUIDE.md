# 安装指引

## macOS

应用未签名 / 未公证，首次打开会提示「已损坏，无法打开」。这是因为 macOS Gatekeeper 会拦截从网络下载的未签名应用，并非文件损坏。

### 方式一：终端命令（推荐）

打开「终端」（Terminal），执行：

```bash
xattr -dr com.apple.quarantine "/Applications/V2Ray Auto.app"
```

然后再次打开应用即可。

### 方式二：右键打开

1. 打开「访达」（Finder），进入「应用程序」（Applications）
2. 按住 `Control` 键点击（或右键）「V2Ray Auto」
3. 选择「打开」，在弹出的对话框中点击「打开」

> 注意：如果右键菜单没有「打开」选项，请使用方式一。

## Windows

直接运行 `V2Ray.Auto.Setup.0.1.0.exe`（安装版）或 `V2Ray.Auto.0.1.0.exe`（便携版）。若 SmartScreen 提示「未知发布者」，点击「更多信息」→「仍要运行」即可。

## Linux

`.AppImage`：`chmod +x V2Ray.Auto.AppImage && ./V2Ray.Auto.AppImage`（或双击运行）。

`.deb`：`sudo dpkg -i v2ray-auto-desktop_0.1.0_amd64.deb`
