import queue
import sys
import ipaddress
import threading

from PyQt5.QtCore import QTimer, QMetaObject, Q_ARG, Qt, pyqtSlot
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, QTextEdit, QComboBox, QMessageBox
from PyQt5.QtGui import QCursor, QGuiApplication
from v2ray_auto_client import V2rayAutoClient


class MyWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.queue = queue.Queue()
        # 初始化定时器，设置回调并启动
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_textbox)
        self.timer.start(100)  # 每100ms检查一次

        self.setWindowTitle("v2ray_auto_client")
        self.setGeometry(200, 200, 400, 420)

        self.ip_label = QLabel("服务器IP地址:", self)
        self.ip_label.move(20, 20)
        self.ip_textbox = QLineEdit(self)
        self.ip_textbox.move(150, 20)

        self.ssh_port_label = QLabel("SSH端口:", self)
        self.ssh_port_label.move(20, 60)
        self.ssh_port_label_textbox = QLineEdit(self)
        self.ssh_port_label_textbox.move(150, 60)
        self.ssh_port_label_textbox.setText("22")

        self.username_label = QLabel("用户名:", self)
        self.username_label.move(20, 100)
        self.username_textbox = QLineEdit(self)
        self.username_textbox.move(150, 100)

        self.password_label = QLabel("密码:", self)
        self.password_label.move(20, 140)
        self.password_textbox = QLineEdit(self)
        self.password_textbox.move(150, 140)
        self.password_textbox.setEchoMode(QLineEdit.Password)  # 设置密码输入框的显示模式

        self.os_label = QLabel("操作系统:", self)
        self.os_label.move(20, 180)
        self.os_combobox = QComboBox(self)
        self.os_combobox.move(150, 180)
        self.os_combobox.addItem("centos")
        self.os_combobox.addItem("ubuntu")
        self.os_combobox.addItem("azure ubuntu")
        self.os_combobox.addItem("debian")
        self.os_combobox.addItem("fedora")
        self.os_combobox.addItem("redhat")

        self.confirm_button = QPushButton("确认", self)
        self.confirm_button.move(150, 220)
        self.confirm_button.clicked.connect(self.on_confirm)

        self.output_textbox = QTextEdit(self)
        self.output_textbox.setGeometry(20, 260, 360, 100)

        self.vmess_textbox = QLineEdit(self)  # 添加一个新的 QLineEdit 用来显示 vmess URL
        self.vmess_textbox.setGeometry(20, 380, 260, 20)

        self.copy_button = QPushButton("复制", self)  # 添加一个新的 QPushButton，点击此按钮将复制 vmess URL
        self.copy_button.setGeometry(300, 380, 60, 20)
        self.copy_button.clicked.connect(self.on_copy)

    def textbox_callback(self, log_entry):
        self.queue.put(log_entry)

    def update_textbox(self):
        while not self.queue.empty():
            log_entry = self.queue.get()
            self.output_textbox.append(log_entry)

    def on_confirm(self):
        params = self.get_params()
        if not self.check_params(params):
            return

        self.set_loading_state(True)  # 将按钮设置为加载状态

        def worker():
            try:
                v2ray_auto_client = V2rayAutoClient(params, textbox_callback=self.textbox_callback)
                vmess = v2ray_auto_client.run()
                QMetaObject.invokeMethod(self.output_textbox, "append", Qt.QueuedConnection, Q_ARG(str, vmess))
                QMetaObject.invokeMethod(self.vmess_textbox, "setText", Qt.QueuedConnection, Q_ARG(str, vmess))
            except Exception as e:
                QMetaObject.invokeMethod(self, "show_error_message", Qt.QueuedConnection, Q_ARG(str, str(e)))
            finally:
                QMetaObject.invokeMethod(self, "set_loading_state", Qt.QueuedConnection, Q_ARG(bool, False))

        thread = threading.Thread(target=worker)
        thread.start()

    def on_copy(self):
        """
        复制 vmess URL 到剪贴板
        """
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self.vmess_textbox.text())

    def get_params(self):
        """
        获取用户输入的参数
        :return:
        """
        ip = self.ip_textbox.text()
        port = self.ssh_port_label_textbox.text()
        username = self.username_textbox.text()
        password = self.password_textbox.text()
        os = self.os_combobox.currentText()

        params = {
            "server_ip": ip,
            "server_port": port,
            "server_username": username,
            "server_password": password,
            "os": os
        }
        return params

    def check_params(self, params):
        """
        参数校验
        :param params: 用户输入的参数
        :return:
        """
        if not self.check_server_ip(params["server_ip"]):
            return False
        if not self.check_ssh_port(params["server_port"]):
            return False
        if not self.check_username(params["server_username"]):
            return False
        if not self.check_password(params["server_password"]):
            return False
        return True

    def check_server_ip(self, ip):
        """
        校验服务器IP地址
        :return:
        """
        if not ip:
            QMessageBox.warning(self, "警告", "服务器IP地址不能为空")
            return False
        if not self.is_valid_ipv4(ip):
            QMessageBox.warning(self, "警告", "服务器IP地址不合法")
            return False
        return True

    def check_ssh_port(self, port):
        """
        校验SSH端口
        :return:
        """
        if not port:
            QMessageBox.warning(self, "警告", "SSH端口不能为空")
            return False
        if not port.isdigit():
            QMessageBox.warning(self, "警告", "SSH端口必须为数字")
            return False
        if int(port) < 1 or int(port) > 65535:
            QMessageBox.warning(self, "警告", "SSH端口必须在1-65535之间")
            return False
        return True

    def check_username(self, username):
        """
        校验用户名
        :return:
        """
        if not username:
            QMessageBox.warning(self, "警告", "用户名不能为空")
            return False
        return True

    def check_password(self, password):
        """
        校验密码
        :return:
        """
        if not password:
            QMessageBox.warning(self, "警告", "密码不能为空")
            return False
        return True

    @staticmethod
    def is_valid_ipv4(address):
        """
        校验IP地址是否合法
        :return:
        """
        try:
            ipaddress.ip_address(address)
            return True
        except ValueError:
            return False

    @pyqtSlot(bool)
    def set_loading_state(self, loading):
        """
        设置按钮加载状态
        :param loading: 是否为加载状态
        :return:
        """
        if loading:
            self.confirm_button.setText("加载中...")
            self.confirm_button.setEnabled(False)
            QApplication.processEvents()  # 更新界面
        else:
            self.confirm_button.setText("确认")
            self.confirm_button.setEnabled(True)
            QApplication.processEvents()  # 更新界面

    @pyqtSlot(str)
    def show_error_message(self, message):
        QMessageBox.critical(self, "异常", f"程序执行过程中出现异常：\n{message}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    sys.exit(app.exec_())
