# import gevent.monkey
# gevent.monkey.patch_all()

from flask import Flask, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from configurator import Configurator
from config_server_api_logger import logger
import time

app = Flask(__name__)
CORS(app)  # 启用 CORS
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)  # 创建 SocketIO 对象


@app.route('/api/configure', methods=['POST'])
def configure():
    try:
        data = request.json
        server_ip = data.get('serverIp')
        server_port = data.get('serverPort')
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        os_type = data.get('os')

        config_params = {"server_ip": server_ip,
                         "server_port": server_port,
                         "server_username": username,
                         "server_password": password,
                         "email": email,
                         "os": os_type}

        configurator = Configurator(config_params, socketio)  # 创建配置器对象
        result = configurator.run()

        socketio.emit('configuration_complete', {'result': result})
        return {'result': result}
    except Exception as e:
        return {'error': str(e)}
    
@socketio.on('connect')
def handle_connect():
    logger.info('客户端已连接到socket.io服务器')

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('客户端已断开socket.io服务器')

