from unittest import TestCase
from auto_install_v2ray import MyV2Ray


class TestMyV2Ray(TestCase):
    def test_get_public_network_ip(self):
        ip_addr = MyV2Ray.get_public_network_ip()
        actual_ip = "167.179.103.98"
        self.assertTrue(ip_addr == actual_ip)
