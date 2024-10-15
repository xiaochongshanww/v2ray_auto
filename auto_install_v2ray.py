from common import *
import argparse


class MyV2Ray:
    def __init__(self):
        self.uuid = ""
        self.server_config = dict()  # 服务端配置
        self.client_config = dict()  # 客户端配置
        self.client_config_vmess_url = ""  # 客户端配置生成的vmess url

        self.init()

    def init(self):
        """
        初始化参数

        :return:
        """
        logger.info("开始自动安装V2Ray...")
        self.get_uuid()
        self.init_server_config()
        self.init_client_config()

    def init_server_config(self):
        """
        从模板文件初始化服务端配置

        :return:
        """
        with open(config.SERVER_CONFIG_TEMPLATE, 'r') as server_config:
            config_data = json.load(server_config)
        self.server_config = config_data
        self.server_config["inbounds"][0]["port"] = MyV2Ray.get_server_listen_port()
        _clients = [{"id": self.uuid, "alterId": 0}]
        self.server_config["inbounds"][0]["settings"]["clients"] = _clients


    def init_client_config(self):
        """
        从模板文件初始化客户端配置

        :return:
        """
        with open(config.CLIENT_CONFIG_TEMPLATE, 'r') as client_config:
            config_data = json.load(client_config)
        self.client_config = config_data
        users = [{"id": f"{self.uuid}", "alterId": 0}]
        self.client_config["outbounds"][0]["settings"]["vnext"][0]["users"] = users
        self.client_config["outbounds"][0]["settings"]["vnext"][0]["address"] = V2RayPublicMethod.get_public_network_ip()

    @staticmethod
    def auto_install():
        logger.info("install v2ray")
        result = subprocess.Popen("systemctl daemon-reload", shell=True, stdout=subprocess.PIPE)
        logger.info(result.stdout.read().decode('utf-8'))
        result = subprocess.Popen("sudo su root", shell=True, stdout=subprocess.PIPE)
        logger.info(result.stdout.read().decode('utf-8'))
        result = subprocess.Popen(['bash', '-c',
                                   'curl -s -L https://raw.githubusercontent.com/v2fly/fhs-install-v2ray/master/install-release.sh | bash'],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
        logger.info(result.stdout.read().decode('utf-8'))
        logger.info("install v2ray finished")

    @staticmethod
    def auto_uninstall():
        logger.info("uninstall v2ray")
        result = subprocess.Popen(['bash', '-c',
                       'echo y | bash <(curl -L https://raw.githubusercontent.com/v2fly/fhs-install-v2ray/master/install-release.sh) --remove'],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
        logger.info(result.stdout.read().decode('utf-8'))
        logger.info("uninstall v2ray finished")

    @staticmethod
    def start_v2ray():
        """
        启动v2ray

        :return:
        """
        logger.info("start v2ray")
        result = subprocess.Popen("systemctl enable v2ray", shell=True, stdout=subprocess.PIPE)
        logger.info(result.stdout.read().decode('utf-8'))
        result = subprocess.Popen("systemctl start v2ray", shell=True, stdout=subprocess.PIPE)
        logger.info(result.stdout.read().decode('utf-8'))
        logger.info("start v2ray finished")

    @staticmethod
    def stop_v2ray():
        """
        停止v2ray服务

        :return:
        """
        logger.info("stop v2ray")
        result = subprocess.Popen("systemctl stop v2ray", shell=True, stdout=subprocess.PIPE)
        logger.info(result.stdout.read().decode('utf-8'))
        logger.info("stop v2ray finished")

    def get_uuid(self):
        """
        返回一个uuid字符串

        :return: None
        """
        uuid_value = uuid.uuid4()
        logger.info(f"生成的uuid: {str(uuid_value)}")
        self.uuid = str(uuid_value)

    @staticmethod
    def get_v2ray_config_path():
        """
        获取v2ray的配置文件路径，当前采用默认安装，默认配置文件地址：/etc/v2ray/config.json

        :return:
        """
        return config.DEFAULT_CONFIG_PATH

    def apply_server_config(self):
        """
        将配置写入服务器上的配置文件并生效

        :return:
        """
        with open(MyV2Ray.get_v2ray_config_path(), 'w') as config_file:
            json.dump(self.server_config, config_file)
        MyV2Ray.stop_v2ray()
        MyV2Ray.start_v2ray()

    def write_client_config(self):
        """
        将客户端配置写入配置文件

        :return:
        """
        with open(config.CLIENT_CONFIG_PATH, 'w') as client_config:
            json.dump(self.client_config, client_config)

    @staticmethod
    def edit_server_config_inbounds(config_data):
        """
        编辑服务器端配置的inbounds

        :return:
        """

    @staticmethod
    def get_server_listen_port():
        """
        随机获取服务器上的监听端口，范围从1000到65535

        :return: int
        """
        logger.info("获取随机端口：")
        rand_port = random.randint(1000, 65535)
        logger.info(f"随机端口为: {rand_port}")
        return rand_port

    def generate_v2ray_vmess_url(self):
        """
        根据客户端配置文件生成vmess url

        :param config:
        :return:
        """
        with open(config.CLIENT_CONFIG_PATH, 'r') as file:
            config_data = json.load(file)
        server = config_data["outbounds"][0]["settings"]["vnext"][0]["address"]
        port = self.server_config["inbounds"][0]["port"]
        uuid = config_data["outbounds"][0]["settings"]["vnext"][0]["users"][0]["id"]
        alterId = config_data["outbounds"][0]["settings"]["vnext"][0]["users"][0]["alterId"]
        network = "tcp"

        vmess = {
            "v": "2",
            "ps": f"wcg_{server}",
            "add": server,
            "port": port,
            "id": uuid,
            "aid": alterId,
            "net": network,
            "type": "none",
            "host": "",
            "path": "",
            "tls": ""
        }

        # 编码为 base64
        encoded_vmess = base64.b64encode(json.dumps(vmess).encode("utf-8")).decode("utf-8")

        # 组装 vmess URL
        vmess_url = "vmess://" + encoded_vmess
        self.client_config_vmess_url = vmess_url
        logger.info(f"vmess_url: {vmess_url}")
        return vmess_url

    def send_url_to_email(self):
        """
        将生成的vmess url发送至邮箱

        :return:
        """
        target_email = "327306310@qq.com"
        import smtplib
        from email.mime.text import MIMEText
        from email.header import Header

        
        # 邮件发送方地址
        sender = 'wcg14231022@gmail.com'
        # 邮件接收方地址
        receiver = '327306310@qq.com'
        # SMTP服务器地址
        smtp_server = 'smtp.gmail.com'
        # SMTP服务器端口号
        smtp_port = 587
        # 邮箱账号
        username = 'wcg14231022@gmail.com'
        # 邮箱密码或授权码
        password = config.GMAIL_CODE

        # 邮件内容
        message = MIMEText(f'vmess url: {self.client_config_vmess_url}', 'plain', 'utf-8')
        message['From'] = Header('wcg', 'utf-8')
        message['To'] = Header('接收人', 'utf-8')
        message['Subject'] = Header('vmess url update', 'utf-8')

        # 发送邮件
        try:
            # 连接SMTP服务器
            smtpObj = smtplib.SMTP(smtp_server, smtp_port)
            smtpObj.starttls()  # 开启TLS加密
            smtpObj.login(username, password)  # 登录邮箱账号
            smtpObj.sendmail(sender, receiver, message.as_string())  # 发送邮件
            logger.info("邮件发送成功")
        except smtplib.SMTPException:
            logger.error("无法发送邮件")


    @staticmethod
    def ip_detect_service():
        script_path = os.path.join(os.getcwd(), "ip_detect/ip_detect.py")  # 定义 Python 脚本路径
        # 创建 Systemd 配置文件
        service_file_content = f"""\
        [Unit]
        Description=My Python Service
        After=network.target
    
        [Service]
        User={os.getlogin()}
        ExecStart=/usr/bin/python {script_path}
        Restart=always
    
        [Install]
        WantedBy=multi-user.target
        """
        # 写入配置文件
        with open("/etc/systemd/system/my_ip_detect_service.service", "w") as f:
            f.write(service_file_content)
        os.system("sudo systemctl daemon-reload")  # 重新加载 Systemd 配置文件
        os.system("sudo systemctl stop my_ip_detect_service")  # 启动前先stop服务
        os.system("sudo systemctl start my_ip_detect_service")  # 启动服务
        os.system("sudo systemctl enable my_ip_detect_service")  # 设置开机自启动


if __name__ == "__main__":
    # 接收命令行参数
    parser = argparse.ArgumentParser(description="Manage V2Ray installation")
    parser.add_argument('--email', type=str, required=True, help="Email address to send the VMess URL")

    my = MyV2Ray()
    my.auto_uninstall()
    my.auto_install()
    my.apply_server_config()
    my.write_client_config()
    my.generate_v2ray_vmess_url()
    my.send_url_to_email()
    my.ip_detect_service()