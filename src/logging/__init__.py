import os
import sys
import logging
from datetime import datetime
sys.path.append(os.getcwd())

LOGGER_NAME = 'INFINITE_CHALLENGE'
LOG_FORMAT = '%(asctime)s %(module)s:%(funcName)s [%(levelname)s] - %(message)s'
LOGFILE_PATH = os.path.join('logs',
                            datetime.now().strftime('%Y_%m_%d'),
                            f'{datetime.now().strftime("%Y_%m_%d_%H_%M_%S")}.log')

if not os.path.exists(os.path.dirname(LOGFILE_PATH)):
    os.makedirs(os.path.dirname(LOGFILE_PATH))


logger = logging.getLogger(LOGGER_NAME)
if True:
    logger.setLevel(logging.INFO)
    console_stream = logging.StreamHandler()
    console_stream.setFormatter(logging.Formatter(LOG_FORMAT))
    console_stream.setLevel(logging.INFO)
    file = logging.FileHandler(filename=LOGFILE_PATH, mode='w')
    logger.addHandler(console_stream)
    logger.addHandler(file)
