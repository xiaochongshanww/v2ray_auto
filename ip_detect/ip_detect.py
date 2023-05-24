import sys
import os
from requests_html import HTMLSession
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import *


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
            sock = socket.create_connection(('www.baidu.com', 80), timeout=5)
            is_blocked = False
        except socket.error:
            is_blocked = True
        if is_blocked:
            logger.error("This IP address is likely blocked")

    @staticmethod
    def ip_detect_by_ping_pe():
        """
        利用ping.pe网站进行查询

        :return:
        """
        logger.info("开始本机IP连通性检测：")
        public_ip = V2RayPublicMethod.get_public_network_ip()
        logger.info(f"本机公网IP: {public_ip}")
        ip_address = '8.8.8.8'  # 要查询的 IP 地址
        url = f'https://tcping.pe/{ip_address}'  # 构建查询的 URL
        url = f'http://ping.chinaz.com/178.128.220.205'
        headers = {'User-Agent': 'Mozilla/5.0'}  # 设置 User-Agent 头部，模拟浏览器访问
        # 发送 GET 请求，获取网页内容
        response = requests.get(url, headers=headers, verify=False)
        time.sleep(60)
        html = response.content
        # 使用 BeautifulSoup 解析网页内容
        soup = BeautifulSoup(html, 'html.parser')
        # 查找包含查询结果的 div 元素
        result_div = soup.find('div', {'class': 'result'})
        # 获取查询结果的文本内容
        result_text = result_div.text.strip()
        # 输出查询结果
        print(f'{ip_address} 的查询结果：{result_text}')


if __name__ == "__main__":
    ip_detect = IpDetect()
    # ip_detect.ip_detect_by_ping_pe()
    while True:
        if ip_detect.is_blocked():
            v2ray_email = V2RayEmail()
            cur_ip_address = V2RayPublicMethod.get_public_network_ip()
            v2ray_email.set_message(f"your ip address {cur_ip_address} was blocked")
            v2ray_email.send_email()
        else:
            logger.info("IP 正常")
            v2ray_email = V2RayEmail()
            cur_ip_address = V2RayPublicMethod.get_public_network_ip()
            v2ray_email.set_message(f"your ip address {cur_ip_address} is active")
            v2ray_email.send_email()
        time.sleep(28800)  # 每小时检测一次
