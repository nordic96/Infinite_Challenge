import boto3
import os
from tempfile import TemporaryDirectory
from logger.base_logger import logger


# Assign an IAM Role with permission to GetObject from S3, boto3 will get
# credentials from instance metadata
# https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html
def s3_download(region_name, bucket_name, filename):
    #adapted from
    #https://www.thetechnologyupdates.com/image-processing-opencv-with-aws-lambda/
    s3 = boto3.client('s3', region_name=region_name)
    logger.info(f'Downloading: [{bucket_name}/{filename}]')
    try:
        file_obj = s3.get_object(Bucket=bucket_name, Key=filename)
        file_data = file_obj["Body"].read()
        logger.info(f'Complete: [{bucket_name}/{filename}]')
        return file_data
    except BaseException as ex:
        logger.error(f'Download failed')
        raise ex


def cache_episode_from_s3(region, bucket_name, episode_name):
    video = s3_download(region, bucket_name, episode_name)
    dir = TemporaryDirectory()
    path = os.path.join(dir.name, episode_name)
    file = open(path, 'rb')
    file.write(video)
    logger.info(f'Episode will be cached @ {file.name}')
    return file
