import logging
import configparser
from datetime import datetime
import os
import logging
import boto3
from botocore.exceptions import ClientError

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
    filename=logfile_path,
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


def upload_file(file_name, bucket, object_name=None):
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """

    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = file_name

    # Upload the file
    s3_client = boto3.client('s3')
    try:
        response = s3_client.upload_file(file_name, bucket, object_name)
        logger.info('Upload successful!')
    except ClientError as e:
        logger.info(e)
        return False
    return True