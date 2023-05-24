# -*- coding:utf-8 -*-
# 自动安装客户端

import os
import sys
from v2ray_auto_client import V2rayAutoClient

if __name__ == "__main__":
    params = dict()
    v2ray_auto_client = V2rayAutoClient(params)
    v2ray_auto_client.run()

