# import gevent
# gevent.monkey.patch_all()

import time
import paramiko
import json
import re
import os
from flask_socketio import SocketIO
from config_server_api_logger import logger


class Configurator:
    def __init__(self, params, socketio: SocketIO):
        self.params = params
        self.env = dict()  # 环境信息
        self.ssh_client = paramiko.SSHClient()
        self.socketio = socketio
        self.init_logger()
        self.init_env_info()

    def init_logger(self):
        import config_server_api_logger
        config_server_api_logger.set_socketio(self.socketio)

    def init_env_info(self):
        """
        初始化环境信息
        :return:
        """
        logger.info("开始初始化环境信息")
        logger.info(
            f"用户参数: {json.dumps(self.params, indent=4, ensure_ascii=False)}")
        self.env["server_ip"] = self.params["server_ip"]
        self.env["server_port"] = self.params["server_port"]
        self.env["server_username"] = self.params["server_username"]
        self.env["server_password"] = self.params["server_password"]
        self.env["venv_path"] = "/home/git_dir/v2ray_auto/venv"
        logger.info("初始化环境信息完成")

    def run(self):
        """
        运行主函数
        :return:
        """
        self.login_server()
        self.change_to_root_user()
        self.server_update()
        self.auto_install_python()
        self.install_git()
        self.clone_v2ray_auto_code()
        self.install_python_requirements()
        vmess = self.auto_config_v2ray_service()
        return vmess

    def login_server(self):
        """
        登录服务器
        :return:
        """
        logger.info("开始登录服务器")
        for i in range(3):
            try:
                self.ssh_client.set_missing_host_key_policy(
                    paramiko.AutoAddPolicy())  # 允许连接不在know_hosts文件中的主机
                self.ssh_client.connect(hostname=self.env["server_ip"], port=self.env["server_port"],
                                        username=self.env["server_username"], password=self.env["server_password"])
            except Exception as e:
                logger.error(f"登录服务器失败: {e}")
                return
            break
        else:
            logger.error("尝试多次登陆服务器失败")
            return

        logger.info("登录服务器完成")

    def change_to_root_user(self):
        """
        切换到root用户
        :return:
        """
        logger.info("开始切换到root用户")
        try:
            self.execute_command(
                f"echo {self.env.get('server_password')} | sudo -S su")
        except Exception as e:
            logger.error(f"切换到root用户失败: {e}")
        logger.info("切换到root用户完成")

    def server_update(self):
        """
        更新服务器
        :return:
        """
        logger.info("开始更新服务器")
        self.execute_command("pwd")
        self.add_swap_memory()
        dis_version = self.get_linux_distro()
        if dis_version:
            if dis_version in ['ubuntu', 'debian']:
                # Ubuntu/Debian系统使用apt-get命令更新
                command = 'sudo apt-get update && sudo apt-get upgrade -y'
            elif dis_version in ['centos', 'redhat', 'fedora']:
                command = 'sudo yum update -y'  # CentOS/RHEL/Fedora系统使用yum命令更新
            else:
                logger.info("不支持的操作系统版本")
                return
        else:
            logger.info("无法获取系统版本信息")
            return
        self.execute_command(command)
        logger.info("更新服务器完成")

    def add_swap_memory(self):
        """
        添加交换分区
        :return:
        """
        if int(self.get_available_memory()) > 100:
            logger.info("服务器可用内存大于100M，暂不添加交换分区")
            return
        logger.info("开始添加交换分区")
        self.execute_command(
            "sudo dd if=/dev/zero of=/swapfile bs=1M count=1024")
        self.execute_command("sudo mkswap /swapfile")
        self.execute_command("sudo swapon /swapfile")
        self.execute_command(
            "sudo echo '/swapfile swap swap defaults 0 0' >> /etc/fstab")
        logger.info("添加交换分区完成")

    def get_available_memory(self):
        """
        获取服务器可用内存
        :return:
        """
        command = "free -m | grep Mem | awk '{print $7}'"
        output = self.execute_command(command)
        return output

    def execute_command(self, command, retries=5, delay=10):
        """
        执行命令并实时获取输出
        :param command: 要执行的命令
        :return: 命令的标准输出
        """
        for attempt in range(retries):
            try:
                cmd_output = self.exceute_command_basic(command)
                if self.cmd_output_has_dpkg_lock(cmd_output):
                    logger.info(f"dpkg锁定，等待{delay}秒后重试")
                    self.release_dpkg_lock(cmd_output)
                    time.sleep(delay)
                    logger.info(f"重新下发命令: {command}")
                    continue
                if self.dpkg_interrupted(cmd_output):
                    logger.info(f"dpkg被中断，尝试修复dpkg状态")
                    self.repair_dpkg()
                    continue
                break
            except Exception as e:
                logger.error(f"执行命令失败: {e}")
                time.sleep(delay)

        return cmd_output

    def exceute_command_basic(self, command):
        """
        命令行执行的基本方法，只负责下发命令，读取回显
        :param command:
        :return:
        """
        server_ip = self.env["server_ip"]
        server_port = self.env["server_port"]
        logger.info(f"正在执行命令: {command}")
        stdin, stdout, stderr = self.ssh_client.exec_command(command)

        full_output = ""
        full_error = ""
        # 实时读取标准输出和标准错误
        while not stdout.channel.exit_status_ready():
            if stdout.channel.recv_ready():
                output = stdout.channel.recv(1024).decode('utf-8')
                full_output += output
                self.socketio.emit('process_update', {'message': output})

            if stderr.channel.recv_stderr_ready():
                error = stderr.channel.recv_stderr(
                    1024).decode('utf-8')
                full_error += error
                self.socketio.emit('process_update', {'message': error})

            # gevent.sleep(0)
        # 捕获命令完成后剩余的输出
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')
        if output:
            full_output += output
            self.socketio.emit('process_update', {'message': output})
        if error:
            full_error += error
            self.socketio.emit('process_update', {'message': error})

        if full_output:
            logger.info(f"[{server_ip}: {server_port}]: {full_output}")
            return full_output
        logger.error(f"[{server_ip}: {server_port}]: {full_error}")
        return full_error
        
    
    def cmd_output_has_dpkg_lock(self, cmd_output):
        """
        检查命令输出是否包含dpkg锁
        :return:
        """
        return "dpkg" in cmd_output and "lock" in cmd_output
    
    def dpkg_interrupted(self, cmd_output):
        """
        检查dpkg是否被中断
        :return:
        """
        return "dpkg" in cmd_output and "interrupted" in cmd_output
    
    def repair_dpkg(self):
        """
        修复dpkg
        :return:
        """
        self.exceute_command_basic("sudo dpkg --configure -a")

    def release_dpkg_lock(self, cmd_output):
        """
        释放dpkg锁
        :return:
        """
        logger.info("释放dpkg锁")
        process_id = self.get_dpkg_held_process_from_output(cmd_output)
        if not process_id:
            logger.error("释放dpkg锁失败")
            return
        self.exceute_command_basic(f"sudo kill -9 {process_id}")
        self.exceute_command_basic(f"sudo dpkg --configure -a")

    def get_dpkg_held_process_from_output(self, cmd_output):
        """
        获取dpkg锁定的进程
        :return:
        """
        logger.info("获取dpkg锁定的进程")
        try:
            process_id = re.findall(r"held by process (\d+)", cmd_output)[0]
        except IndexError:
            logger.error("无法获取dpkg锁定的进程")
            process_id = None
        return process_id
    
    def get_linux_distro(self):
        """
        判断Linux操作系统类型
        :return:
        """
        command = 'cat /etc/os-release | grep -E "^ID="'
        output = self.execute_command(command)

        if output:
            linux_distribute = output.split(
                '=')[1].lower().strip().replace('"', '')
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
        self.auto_install_py_venv()

    def auto_install_py_venv(self):
        """
        自动安装python虚拟环境
        :return:
        """
        logger.info("开始自动安装Python虚拟环境")
        logger.info("安装virtualenv")
        install_command = self.get_py_virtualenv_install_command()
        self.execute_command(install_command)
        logger.info("自动安装virtualenv完成")
        logger.info("安装venv")
        venv_install_command = self.get_py_venv_install_command()
        self.execute_command(venv_install_command)
        logger.info("自动安装venv完成")
        logger.info("自动安装Python虚拟环境完成")

    def get_py_venv_install_command(self):
        """
        获取安装python虚拟环境命令
        :return:
        """
        linux_distribute = self.env["linux_distribute"]
        if linux_distribute in ['ubuntu', 'debian']:
            return "sudo apt-get install python3-venv -y"
        elif linux_distribute in ['centos', 'redhat', 'fedora', 'rhel']:
            return "sudo yum install python3-venv -y"
        else:
            logger.error("不支持的操作系统类型")
            return

    def get_py_virtualenv_install_command(self):
        """
        获取安装python虚拟环境命令
        :return:
        """
        linux_distribute = self.env["linux_distribute"]
        if linux_distribute in ['ubuntu', 'debian']:
            return "sudo apt-get install python3-virtualenv -y"
        elif linux_distribute in ['centos', 'redhat', 'fedora', 'rhel']:
            return "sudo yum install python3-virtualenv -y"
        else:
            logger.error("不支持的操作系统类型")
            return

    def get_python_install_command(self):
        """
        根据操作系统获取python安装命令
        :return:
        """
        linux_distribute = self.env["linux_distribute"]
        if linux_distribute in ['ubuntu', 'debian']:
            return "sudo apt-get install python3 -y"
        elif linux_distribute in ['centos', 'redhat', 'fedora', 'rhel']:
            return "sudo yum install python3 -y"
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
            return "sudo apt-get install python3-pip -y"
        elif linux_distribute in ['centos', 'redhat', 'fedora', 'rhel']:
            return "sudo yum install python3-pip -y"
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
            return "sudo apt-get install git -y"
        elif linux_distribute in ['centos', 'redhat', 'fedora', 'rhel']:
            return "sudo yum install git -y"
        else:
            logger.error("不支持的操作系统类型")
            return None

    def clone_v2ray_auto_code(self):
        """
        克隆v2ray-auto代码
        :return:
        """
        logger.info("开始克隆v2ray-auto代码")
        linux_distribute = self.env["linux_distribute"]
        self.execute_command(f"sudo rm -rf {self.get_git_dir_path()}")
        self.execute_command(f"sudo mkdir -p {self.get_git_dir_path()}")
        self.execute_command(
            f"sudo chown -R $(whoami):$(whoami) {self.get_git_dir_path()}")
        clone_command = self.get_clone_v2ray_code_command()
        self.execute_command(clone_command)
        logger.info("克隆v2ray-auto代码完成")

    def get_git_dir_path(self):
        """
        获取git目录路径
        :return:
        """
        git_dir_path = "/home/git_dir"
        if re.search(r"azure ubuntu", self.params.get("os"), re.I):
            git_dir_path = f"/home/{self.env.get('server_username')}/git_dir"
        return git_dir_path

    def get_clone_v2ray_code_command(self):
        """
        获取克隆v2ray代码命令
        :return:
        """
        clone_command = "sudo git clone https://github.com/wcg14231022/v2ray_auto.git /home/git_dir/v2ray_auto"
        if re.search(r"azure ubuntu", self.params.get("os"), re.I):
            clone_command = f"git clone https://github.com/wcg14231022/v2ray_auto.git /home" \
                f"/{self.env.get('server_username')}/git_dir/v2ray_auto"
        return clone_command

    def install_python_requirements(self):
        """
        安装python依赖
        :return:
        """
        logger.info("开始安装python依赖")
        self.create_py_venv()
        # 在虚拟环境中安装python依赖
        # self.execute_command("source venv/bin/activate && pip install -r /home/git_dir/v2ray_auto/requirements.txt")
        install_command = self.get_install_python_requirements_command()
        logger.info(f"安装python依赖命令: {install_command}")
        self.execute_command(
            f"""source venv/bin/activate && {install_command}""")
        # self.execute_command(install_command)
        self.install_python_bs4()
        self.deactivate_py_venv()
        logger.info("安装python依赖完成")

    def create_py_venv(self):
        """
        创建python虚拟环境
        """
        logger.info("开始创建python虚拟环境")
        # 获取当前工作目录
        rs_pwd = self.execute_command("pwd")
        self.env["venv_path"] = rs_pwd.strip() + "/venv"
        # 在当前目录创建python虚拟环境
        self.execute_command("sudo python3 -m venv venv")
        # 修改虚拟环境目录权限
        self.execute_command(f"sudo chown -R $(whoami):$(whoami) ./venv")
        # 激活虚拟环境
        self.execute_command("source venv/bin/activate")
        logger.info("创建python虚拟环境完成")

    def deactivate_py_venv(self):
        """
        退出python虚拟环境
        """
        logger.info("开始退出python虚拟环境")
        # self.execute_command("deactivate")
        logger.info("退出python虚拟环境完成")

    def install_python_bs4(self):
        """
        检查环境上是否已安装beautifulsoup4库，如果没有则安装
        """
        logger.info("开始安装beautifulsoup4库")
        install_command = self.get_install_python_bs4_command()
        logger.info(f"安装beautifulsoup4库命令: {install_command}")
        self.execute_command(
            f"""source venv/bin/activate && {install_command}""")
        # self.execute_command(f"""source venv/bin/activate && pip install beautifulsoup4""")
        # self.execute_command(f"""source venv/bin/activate && pip install bs4""")
        # self.execute_command(install_command)
        logger.info("安装beautifulsoup4库完成")

    def get_install_python_bs4_command(self):
        """
        获取安装beautifulsoup4库命令
        """
        install_command = "pip install beautifulsoup4"
        if re.search(r"azure ubuntu", self.params.get("os"), re.I):
            install_command = f"pip3 install beautifulsoup4"
        return install_command

    def get_install_python_requirements_command(self):
        """
        获取安装python依赖命令
        :return:
        """
        install_command = "pip install -r /home/git_dir/v2ray_auto/requirements.txt"
        if re.search(r"azure ubuntu", self.params.get("os"), re.I):
            install_command = f"pip3 install -r /home/{self.env.get('server_username')}/" \
                f"git_dir/v2ray_auto/requirements.txt"
        return install_command

    def auto_config_v2ray_service(self):
        """
        自动配置v2ray服务
        :return:
        """
        logger.info("开始自动配置v2ray服务")
        config_command = self.get_auto_config_v2ray_service_command()
        logger.info(f"配置命令: {config_command}")
        rs = self.execute_command(config_command)
        logger.info(f"配置结果: {rs}")
        self.open_fire_wall_for_v2ray(rs)
        vmess = re.findall(r"vmess_url:\s*(\S+)\n", rs, re.I | re.M)[0]
        logger.info("自动配置v2ray服务完成")
        logger.info(f"获取到的vmess: {vmess}")
        return vmess

    def open_fire_wall_for_v2ray(self, rs):
        """
        打开防火墙
        :param rs: v2ray配置结果
        :return:
        """
        port = self.get_v2ray_port(rs)
        self.execute_command(
            f"sudo iptables -A INPUT -p tcp --dport {port} -j ACCEPT")
        self.execute_command(
            f"sudo iptables -A INPUT -p udp --dport {port} -j ACCEPT")
        self.execute_command(
            f"sudo firewall-cmd --permanent --zone=public --add-port={port}/tcp")
        self.execute_command(
            f"sudo firewall-cmd --permanent --zone=public --add-port={port}/udp")
        self.execute_command(f"sudo firewall-cmd --reload")

    @staticmethod
    def get_v2ray_port(rs):
        """
        获取v2ray端口
        :param rs:
        :return:
        """
        port = re.findall(r"随机端口为:\s*(\d+)\n", rs, re.I | re.M)[0]
        logger.info(f"获取到的v2ray端口: {port}")
        return port

    def get_auto_config_v2ray_service_command(self):
        """
        获取自动配置v2ray服务命令
        """
        config_command = "cd /home/git_dir/v2ray_auto && python3 /home/git_dir/v2ray_auto/auto_install_v2ray.py"
        if re.search(r"azure ubuntu", self.params.get("os"), re.I):
            venv_python = os.path.join(
                self.env.get("venv_path"), "bin", "python3")
            config_command = f"cd /home/{self.env.get('server_username')}/git_dir/v2ray_auto && {self.get_active_venev_command(
            )} && sudo {venv_python} /home/{self.env.get('server_username')}/git_dir/v2ray_auto/auto_install_v2ray.py --email {self.params.get('email')}"
        return config_command

    def get_active_venev_command(self):
        """
        获取激活虚拟环境命令
        :return:
        """
        cmd = f"source {self.env.get('venv_path')}/bin/activate"
        return cmd

    def configure(self, server_ip, server_port, username, password, os_type):
        # 模拟配置过程
        for i in range(5):
            time.sleep(1)
            message = f"步骤 {
                i+1}: 配置 {server_ip}:{server_port} 上的 {os_type} 系统\n"
            self.socketio.emit('process_update', {'message': message})

        result = f"配置完成！\n服务器 IP: {server_ip}\n服务器端口: {
            server_port}\n用户名: {username}\n操作系统类型: {os_type}"
        return result
