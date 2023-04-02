import email_service_config
from flask import Flask

app = Flask(__name__)


@app.route('/')
def index():
    return "hello world"


@app.route('/email-key', methods=['GET'])
def get_email_key():
    return email_service_config.GMAIL_CODE


if __name__ == "__main__":
    app.run(port=5000)
