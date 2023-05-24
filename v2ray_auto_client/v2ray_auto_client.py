# -*- coding:utf-8 -*-
import distro
import paramiko
import platform
from common import *


class V2rayAutoClient:
    def __init__(self, params):
        self.params = params
        self.env = dict()  # 环境信息
        self.ssh_client = paramiko.SSHClient()
        self.init_env_info()

    def init_env_info(self):
        """
        初始化环境信息
        :return:
        """
        logger.info("开始初始化环境信息")
        self.env["server_ip"] = self.params["server_ip"]
        self.env["server_port"] = self.params["server_port"]
        self.env["server_username"] = self.params["server_username"]
        self.env["server_password"] = self.params["server_password"]
        logger.info("初始化环境信息完成")

    def run(self):
        """
        运行主函数
        :return:
        """
        self.login_server()
        self.server_update()
        self.auto_install_python()
        self.install_git()
        self.clone_v2ray_auto_code()
        self.install_python_requirements()

    def login_server(self):
        """
        登录服务器
        :return:
        """
        logger.info("开始登录服务器")
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())   # 允许连接不在know_hosts文件中的主机
        self.ssh_client.connect(hostname=self.env["server_ip"], port=self.env["server_port"],
                                username=self.env["server_username"], password=self.env["server_password"])
        logger.info("登录服务器完成")

    def server_update(self):
        """
        更新服务器
        :return:
        """
        logger.info("开始更新服务器")
        self.execute_command("pwd")
        dis_version = self.get_linux_distro()
        if dis_version:
            if dis_version in ['ubuntu', 'debian']:
                command = 'apt-get update && apt-get upgrade -y'  # Ubuntu/Debian系统使用apt-get命令更新
            elif dis_version in ['centos', 'redhat', 'fedora']:
                command = 'yum update -y'  # CentOS/RHEL/Fedora系统使用yum命令更新
            else:
                logger.info("不支持的操作系统版本")
                return
        else:
            logger.info("无法获取系统版本信息")
            return
        self.execute_command(command)
        logger.info("更新服务器完成")

    def execute_command(self, command):
        """
        执行命令并获取输出
        :param command:
        :return:
        """
        server_ip = self.env["server_ip"]
        server_port = self.env["server_port"]
        stdin, stdout, stderr = self.ssh_client.exec_command(command)
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')
        logger.info(f"[{server_ip}: {server_port}]: {command}\n{output}")
        if error:
            logger.info(f"[{server_ip}: {server_port}]:\nCommand error: {error}")
        return output

    def get_linux_distro(self):
        """
        判断Linux操作系统类型
        :return:
        """
        command = 'cat /etc/os-release | grep -E "^ID="'
        output = self.execute_command(command)

        if output:
            linux_distribute = output.split('=')[1].lower().strip().replace('"', '')
            logger.info(f"Linux操作系统类型: {linux_distribute}")
            self.env["linux_distribute"] = linux_distribute
            return linux_distribute
        logger.error("获取Linux操作系统类型失败")
        return None

    def auto_install_python(self):
        """
        自动安装Python
        :return:
        """
        logger.info("开始自动安装Python")
        install_command = self.get_python_install_command()
        self.execute_command(install_command)
        logger.info("自动安装Python完成")
        logger.info("开始自动安装pip")
        pip_install_command = self.get_pip_install_command()
        self.execute_command(pip_install_command)
        logger.info("自动安装pip完成")

    def get_python_install_command(self):
        """
        根据操作系统获取python安装命令
        :return:
        """
        linux_distribute = self.env["linux_distribute"]
        if linux_distribute in ['ubuntu', 'debian']:
            return "apt-get install python3 -y"
        elif linux_distribute in ['centos', 'redhat', 'fedora']:
            return "yum install python3 -y"
        else:
            logger.error("不支持的操作系统类型")
            return None

    def get_pip_install_command(self):
        """
        根据操作系统获取pip安装命令
        :return:
        """
        linux_distribute = self.env["linux_distribute"]
        if linux_distribute in ['ubuntu', 'debian']:
            return "apt-get install python3-pip -y"
        elif linux_distribute in ['centos', 'redhat', 'fedora']:
            return "yum install python3-pip -y"
        else:
            logger.error("不支持的操作系统类型")
            return None

    def install_git(self):
        """
        安装git
        :return:
        """
        logger.info("开始安装git")
        install_command = self.get_git_install_command()
        self.execute_command(install_command)
        logger.info("安装git完成")

    def get_git_install_command(self):
        """
        获取git安装命令
        :return:
        """
        linux_distribute = self.env["linux_distribute"]
        if linux_distribute in ['ubuntu', 'debian']:
            return "apt-get install git -y"
        elif linux_distribute in ['centos', 'redhat', 'fedora']:
            return "yum install git -y"
        else:
            logger.error("不支持的操作系统类型")
            return None

    def clone_v2ray_auto_code(self):
        """
        克隆v2ray-auto代码
        :return:
        """
        logger.info("开始克隆v2ray-auto代码")
        self.execute_command("mkdir -p /home/git_dir")
        clone_command = "git clone https://github.com/wcg14231022/v2ray_auto.git /home/git_dir"
        self.execute_command(clone_command)
        logger.info("克隆v2ray-auto代码完成")

    def install_python_requirements(self):
        """
        安装python依赖
        :return:
        """
        logger.info("开始安装python依赖")
        install_command = "pip install -r /home/git_dir/requirements.txt"
        self.execute_command(install_command)
        logger.info("安装python依赖完成")

    def auto_config_v2ray_service(self):
        """
        自动配置v2ray服务
        :return:
        """
        logger.info("开始自动配置v2ray服务")
        self.execute_command("sudo python3 /home/git_dir/v2ray_auto/auto_install_v2ray.py")
        logger.info("自动配置v2ray服务完成")