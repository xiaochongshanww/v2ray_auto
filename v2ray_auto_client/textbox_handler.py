import logging


class TextboxHandler(logging.Handler):
    def __init__(self, textbox_callback):
        super().__init__()
        self.textbox_callback = textbox_callback

    def emit(self, record):
        log_entry = self.format(record)
        self.textbox_callback(log_entry)