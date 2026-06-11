"""
Deprecated legacy email module.

This module is superseded by environment-variable-based SMTP configuration
in v2ray_auto.core.settings. Kept only for historical reference.
"""


class V2RayEmail:
    def __init__(self):
        # NOTE: Use environment variables instead (V2RAY_AUTO_SMTP_*).
        # The old config.GMAIL_CODE was removed during the destructive refactor.
        self.my_email = ""
        self.my_user = ""
        self.my_email_key = ""
        self.target_email = ""
        self.smtp_server = ""
        self.smtp_port = 587
        self.sender = ""
        self.receiver = ""
        self.message = None

    def set_message(self, message: str, header="auto send email"):
        """
        设置消息内容

        :return:
        """
        message = MIMEText(f'{message}', 'plain', 'utf-8')
        message['From'] = Header('wcg', 'utf-8')
        message['To'] = Header('接收人', 'utf-8')
        message['Subject'] = Header(f'{header}', 'utf-8')
        self.message = message

    def send_email(self):
        """
        发送邮件

        :return:
        """
        try:
            # 连接SMTP服务器
            smtp_obj = smtplib.SMTP(self.smtp_server, self.smtp_port)
            smtp_obj.starttls()  # 开启TLS加密
            smtp_obj.login(self.my_user, self.my_email_key)  # 登录邮箱账号
            smtp_obj.sendmail(self.my_email, self.target_email, self.message.as_string())  # 发送邮件
            logger.info("邮件发送成功")
        except smtplib.SMTPException:
            logger.error("无法发送邮件")

    @staticmethod
    def get_email_key():
        """
        获取邮箱应用密码
        :return:
        """
        response = requests.get("http://www.xiaochongshan.xyz:5000/email-key")
        if response.status_code == 200:
            data = response.text
        return data
