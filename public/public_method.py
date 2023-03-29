"""
公共方法
"""
from common import *

class V2RayPublicMethod:
    def __int__(self):
        pass

    @staticmethod
    def get_public_network_ip():
        """
        获取服务器的公网ip地址

        :return:
        """
        response = requests.get("http://ipinfo.io/ip")  # 向 http://ipinfo.io/ip 发送 HTTP 请求
        public_ip = response.text.strip()  # 从响应中获取服务器的公网 IP 地址
        logger.info(f"本机公网IP: {public_ip}")
        return public_ip