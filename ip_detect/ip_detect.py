import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
print(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# sys.path.append("/home/git_repo/v2ray_auto/")
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


if __name__ == "__main__":
    ip_detect = IpDetect()
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
        time.sleep(3600)  # 每小时检测一次
