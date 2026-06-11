"""
Deprecated legacy public methods module.

This module is superseded by v2ray_auto.core.* modules.
"""

import requests


class V2RayPublicMethod:
    def __int__(self):
        pass

    @staticmethod
    def get_public_network_ip():
        """
        获取服务器的公网ip地址

        :return:
        """
        response = requests.get("http://ipinfo.io/ip")
        public_ip = response.text.strip()
        return public_ip