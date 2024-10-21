import logging
import os.path
import sys
from logging.handlers import TimedRotatingFileHandler

# 创建全局日志器
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# 创建控制台处理器
console_handler = logging.StreamHandler(sys.stdout)  # 日志记录到标准输出
console_handler.setLevel(logging.DEBUG)

# 定义日志格式
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# 将处理器添加到日志器
logger.addHandler(console_handler)

# 创建一个函数来设置 socketio 对象
socketio = None

def set_socketio(sio):
    global socketio
    socketio = sio

# 创建一个自定义日志处理器
class SocketIOHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        if socketio:
            socketio.emit('process_update', {'message': log_entry})

# 创建并配置 SocketIOHandler
socketio_handler = SocketIOHandler()
socketio_handler.setLevel(logging.DEBUG)
socketio_handler.setFormatter(formatter)

# 将 SocketIOHandler 添加到日志器
logger.addHandler(socketio_handler)

# 创建文件处理器，按时间分割日志文件
log_file_path = os.path.join(os.path.dirname(__file__), 'config_server.log')
file_handler = TimedRotatingFileHandler(log_file_path, when='midnight', interval=1, backupCount=7)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# 将文件处理器添加到日志器
logger.addHandler(file_handler)
