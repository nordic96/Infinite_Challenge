import logging
import os
from datetime import datetime

LOGGER_NAME = 'INFINITE_CHALLENGE'
LOG_FORMAT = '%(asctime)s %(module)s:%(funcName)s [%(levelname)s] - %(message)s'
logger = logging.getLogger(LOGGER_NAME)
console_stream = logging.StreamHandler()

if True:
    logger.setLevel(logging.INFO)
    console_stream.setFormatter(logging.Formatter(LOG_FORMAT))
    console_stream.setLevel(logging.INFO)
    logger.addHandler(console_stream)


def add_file_handler(base_dir):
    logfile_dir = os.path.join(base_dir,
                               datetime.now().strftime('%Y_%m_%d'))
    logfile_name = os.path.join(logfile_dir, f'{datetime.now().strftime("%Y_%m_%d_%H_%M_%S")}.log')
    os.makedirs(logfile_dir, exist_ok=True)
    file = logging.FileHandler(filename=logfile_name, mode='w')
    file.setLevel(logging.INFO)
    file.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(file)
    file_handler_count = 0
    for handler in logger.handlers:
        if handler.__class__ == logging.FileHandler:
            file_handler_count += 1
    if file_handler_count > 1:
        logger.warning(f'Multiple ({file_handler_count}) file handlers are associated with this logger')
