import os.path

REPO_ADDR = "wcg14231022/233boy_v2ray_backup"
BRANCH = "master"
V2RAY_SCRIPT_PATH = "install.sh"
GITHUB_TOKEN = "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"

DEFAULT_CONFIG_PATH = "/usr/local/etc/v2ray/config.json"
SERVER_CONFIG_TEMPLATE = os.path.join(os.getcwd(), "config_template/server_config.json")
CLIENT_CONFIG_TEMPLATE = os.path.join(os.getcwd(), "config_template/client_config.json")
CLIENT_CONFIG_PATH = os.path.join(os.getcwd(), "client_config/client_config.json")  # 生成的客户端配置文件
GMAIL_CODE = "bspkamarwiqzfytn"
