import gevent.monkey
from config_server_api_logger import logger

class ConfigServerPublic:
    """
    定义公共方法
    """
    def __init__(self):
        pass
    
    
    @staticmethod
    def exceute_command_basic_public(command, **kwargs):
        """
        命令行执行的基本方法，只负责下发命令，读取回显
        :param cmd: 命令行
        :param kwargs: 参数字典
        需要的参数：
        server_ip: 服务器IP
        server_port: 服务器端口
        ssh_client: SSHClient对象
        socketio: socketio对象
        :return:
        """
        server_ip = kwargs.get('server_ip')
        server_port = kwargs.get('server_port')
        ssh_client = kwargs.get('ssh_client')
        socketio = kwargs.get('socketio')
        
        logger.info(f"正在执行命令: {command}")
        stdin, stdout, stderr = ssh_client.exec_command(command)

        full_output = ""
        full_error = ""
        # 实时读取标准输出和标准错误
        while not stdout.channel.exit_status_ready():
            if stdout.channel.recv_ready():
                output = stdout.channel.recv(1024).decode('utf-8')
                full_output += output
                socketio.emit('process_update', {'message': output})

            if stderr.channel.recv_stderr_ready():
                error = stderr.channel.recv_stderr(
                    1024).decode('utf-8')
                full_error += error
                socketio.emit('process_update', {'message': error})

            gevent.sleep(0)
        # 捕获命令完成后剩余的输出
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')
        if output:
            full_output += output
            socketio.emit('process_update', {'message': output})
        if error:
            full_error += error
            socketio.emit('process_update', {'message': error})

        if full_output:
            logger.info(f"[{server_ip}: {server_port}]: {full_output}")
            return full_output
        logger.error(f"[{server_ip}: {server_port}]: {full_error}")
        return full_error