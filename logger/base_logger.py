import logging
import configparser
from datetime import datetime
import os

LOG_FORMAT = '%(asctime)s %(module)s [%(levelname)s] - %(message)s'

# Initialise strings from config file
config = configparser.ConfigParser()
config.read('strings.ini')

logger = logging
log_path = config['LOG']['logfile_dir']
if not os.path.exists(log_path):
    os.makedirs(log_path)

current_date = datetime.now().strftime('%Y_%m_%d')
log_path = os.path.join(log_path, current_date)

if not os.path.exists(log_path):
    os.makedirs(log_path)

current_datetime = datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
logfile_name = 'LOG_{}.log'.format(current_datetime)
logfile_path = os.path.join(log_path, logfile_name)

logger.basicConfig(
    filename= logfile_path,
    filemode='w',
    format=LOG_FORMAT,
    level=logging.INFO
)

console = logging.StreamHandler()
console.setLevel(logging.INFO)
# set a format which is simpler for console use
formatter = logging.Formatter(LOG_FORMAT)
# tell the handler to use this format
console.setFormatter(formatter)
# add the handler to the root logger
logging.getLogger('').addHandler(console)