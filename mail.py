import logging


def send_url_to_email():
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
    password = 'bspkamarwiqzfytn'

    # 邮件内容
    message = MIMEText('这是一封来自Python发送的邮件。', 'plain', 'utf-8')
    message['From'] = Header('Python邮件测试', 'utf-8')
    message['To'] = Header('测试接收人', 'utf-8')
    message['Subject'] = Header('Python SMTP邮件测试', 'utf-8')

    # 发送邮件
    try:
        # 连接SMTP服务器
        smtpObj = smtplib.SMTP(smtp_server, smtp_port)
        smtpObj.starttls()  # 开启TLS加密
        smtpObj.login(username, password)  # 登录邮箱账号
        smtpObj.sendmail(sender, receiver, message.as_string())  # 发送邮件
        print("邮件发送成功")
    except smtplib.SMTPException:
        print("Error: 无法发送邮件")

# send_url_to_email()

def ip_detect_by_ping_pe():
    """
    利用ping.pe网站进行查询

    :return:
    """
    import requests
    from bs4 import BeautifulSoup
    logger = logging.getLogger()
    logger.info("开始本机IP连通性检测：")
    public_ip = "167.179.93.73"
    logger.info(f"本机公网IP: {public_ip}")
    url = f'https://tcping.pe/{public_ip}:22'  # 构建查询的 URL
    print(url)
    headers = {'User-Agent': 'Mozilla/5.0'}  # 设置 User-Agent 头部，模拟浏览器访问
    # 发送 GET 请求，获取网页内容
    response = requests.get(url, headers=headers, verify=False, proxies={})
    html = response.content
    # 使用 BeautifulSoup 解析网页内容
    soup = BeautifulSoup(html, 'html.parser')
    # 查找包含查询结果的 div 元素
    result_div = soup.find('div', {'class': 'result'})
    # 获取查询结果的文本内容
    result_text = result_div.text.strip()
    # 输出查询结果
    print(f'{public_ip} 的查询结果：{result_text}')
ip_detect_by_ping_pe()