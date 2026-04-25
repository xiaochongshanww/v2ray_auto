from config_server_public import ConfigServerPublic
from config_server_api_logger import logger
from configurator import Configurator

class Warp_Configurator:
    """
    连接cloudflare warp， 解锁区域限制
    """
    def __init__(self, configurator):
        self.configurator = configurator
        self.channel = self.configurator.ssh_client.invoke_shell()
    
    def run(self):
        if self.installed_warp():
            logger.info("Warp 已经安装")
            return True
        self.run_warp_script()
    
    def run_warp_script(self):
        """
        运行 warp 的shell脚本，并且进行交互
        """
        command = self.get_warp_exc_cmd()
        self.channel.send(command)
        while True:
            if self.channel.recv_ready():
                output = self.channel.recv(9999).decode('utf-8')
                logger.info(output)
            if self.channel.exit_status_ready():
                break
        
    
    def get_warp_exc_cmd(self):
        """
        获取 warp 的执行命令
        """
        return "wget -N https://gitlab.com/fscarmen/warp/-/raw/main/menu.sh && bash menu.sh [option] [lisence/url/token]"
        
    def installed_warp(self):
        """
        检查是否安装了 warp
        """
        rs = self.configurator.exec_cmd("warp h")
        if "command not found" in rs:
            return False
        return True