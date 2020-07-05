import logging
from datetime import datetime
import os

logger = logging
current_date = datetime.now().strftime('%YY_%m_%d')

if not os.path.exists(current_date):
    os.makedirs()

current_datetime = datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
logfile_name = 'LOG_{}.log'.format(current_datetime)
logger.basicConfig(
    filename= '{}/{}'.format(current_date, logfile_name),
    format='%(asctime)s %(module)s [%(levelname)s] - %(message)s',
    level=logging.INFO
)