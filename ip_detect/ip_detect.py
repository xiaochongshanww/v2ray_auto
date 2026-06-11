"""
Deprecated legacy IP detection module.

This module is kept for historical reference only.
"""

import socket

import requests
from bs4 import BeautifulSoup

from public.public_method import V2RayPublicMethod


class IpDetect:
    def __int__(self):
        pass

    @staticmethod
    def is_blocked():
        """
        判断本机ip是否已被封锁

        :return:
        """
        try:
            socket.create_connection(('www.baidu.com', 80), timeout=5)
            is_blocked = False
        except socket.error:
            is_blocked = True
        if is_blocked:
            print("This IP address is likely blocked")
        return is_blocked

    @staticmethod
    def ip_detect_by_ping_pe():
        """
        利用ping.pe网站进行查询

        :return:
        """
        public_ip = V2RayPublicMethod.get_public_network_ip()
        print(f"本机公网IP: {public_ip}")
        ip_address = '8.8.8.8'
        url = f'http://ping.chinaz.com/178.128.220.205'
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, verify=False)
        html = response.content
        soup = BeautifulSoup(html, 'html.parser')
        result_div = soup.find('div', {'class': 'result'})
        result_text = result_div.text.strip()
        print(f'{ip_address} 的查询结果：{result_text}')
