import logging
import os.path

# 创建全局日志器
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log_file/my_log.log")
if not os.path.exists(os.path.dirname(log_file_path)):
    os.mkdir(os.path.dirname(log_file_path))
with open(log_file_path, 'w') as file:
    file.write("log file")
# 创建文件处理器
file_handler = logging.FileHandler(log_file_path)
file_handler.setLevel(logging.DEBUG)

# 定义日志格式
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# 将处理器添加到日志器
logger.addHandler(console_handler)
logger.addHandler(file_handler)
