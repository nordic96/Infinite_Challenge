from model import vid_recognition as vr
from model import frame_recognition as fr
from logger.base_logger import logger
from logger.result_logger import ResultLogger, FIELDNAME_BURNED_MEMBER, FIELDNAME_EP, FIELDNAME_TIME
from utils.sql_connecter import SqlConnector
from tempfile import TemporaryDirectory
import boto3
import cv2
import os
import configparser
import traceback
import datetime
import pickle

JOB_INDEX = 'IC_JOB_INDEX'
JOB_INDEX_OFFSET = 'IC_INDEX_OFFSET'
RDS_PASSWORD = 'IC_RDS_PASSWORD'


# Main script for skull detection and extraction of relevant frames from episodes
# Will be used in phase 1 for batch processing of the episodes
# Developed Date: 30 June 2020
# Last Modified: 6 Jul 2020


# Assign an IAM Role with permission to GetObject from S3, boto3 will get
# credentials from instance metadata
# https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html
def phase1_s3_download(bucket_name, filename):
    #adapted from
    #https://www.thetechnologyupdates.com/image-processing-opencv-with-aws-lambda/
    s3 = boto3.client('s3')
    logger.info(f'Downloading: [{bucket_name}/{filename}]')
    try:
        file_obj = s3.get_object(Bucket=bucket_name, Key=filename)
        file_data = file_obj["Body"].read()
        logger.info(f'Complete: [{bucket_name}/{filename}]')
        return file_data
    except BaseException as ex:
        logger.error(f'Download failed')
        raise ex


def phase1_cache_episode_from_s3(bucket_name, episode_name):
    video = phase1_s3_download(bucket_name, episode_name)
    dir = TemporaryDirectory()
    path = os.path.join(dir.name, episode_name)
    file = open(path, 'rb')
    file.write(video)
    logger.info(f'Episode will be cached @ {file.name}')
    return file

def save_extracted_frame(directory, frame):
    filename = f"{frame.episode_number}_{frame.timestamp.replace(':', '_')}.jpg"
    logger.info(filename)
    dst_path = os.path.join(directory, filename)
    cv2.imwrite(dst_path, frame.frame)


# 1. process a single video using model
# 2. cache images with skulls
# 3. update result.csv for each image
def phase1(episode_num, bucket, output_directory, result_logger, sample_rate, confidence, model_version, display):
    try:
        # get episode from S3
        episode_filename = f'episode{episode_num}.mp4'
        logger.info(f'Retrieving {bucket}/{episode_filename} from AWS S3')
        logger.critical('Skipping s3 retrieval for testing purposes')
        #cached_episode = phase1_cache_episode_from_s3(bucket, episode_filename)
        #video_path = cached_episode.name
        video_path = f'resources/sample_episodes/'+episode_filename
        # process episode
        logger.info('Processing video')
        extracted_frames = vr.process_stream(
            video_path=video_path,
            confidence=confidence,
            model_version=model_version,
            sample_rate=sample_rate,
            display=display
        )
        # update results and cache image locally on container
        logger.info('Saving extracted frames')
        for frame in extracted_frames:
            save_extracted_frame(output_directory, frame)
        logger.info('Updating results')
        for frame in extracted_frames:
            result_logger.add_skull_entry(episode_num, frame.timestamp, frame.coord)
    except BaseException as ex:
        logger.error('Phase 1 failed')
        raise ex


# 1. process all images in the output directory of phase1 using frame_det model
# 2. update result.csv for each image
def phase2(input_directory, known_face_encodings, detection_method, result_logger, display):
    images = os.listdir(input_directory)
    logger.info(f'Found {len(images)} frame(s) to process...')
    count = 0
    total = len(images)
    for image in images:
        try:
            count += 1
            path = os.path.join(input_directory, image)
            logger.info(f'Processing frame {count}/{total}')
            processed_img = fr.process_image(path, known_face_encodings, detection_method, display)
            result_logger.update_face_entry(
                processed_img.episode_number,
                processed_img.timestamp,
                processed_img.coordinate,
                processed_img.name
            )
        except BaseException as ex:
            logger.error('Frame {}/{}: {}\n{}'.format(count, total, ex.__class__.__name__, '\n'.join(ex.args)))
            raise ex


def phase3(result_logger: ResultLogger, db_endpoint, db_name, db_username, db_password, result_table):
    logger.info('Estimating burned members')
    list_of_dict, test = result_logger.estimate_burned_member()
    logger.info(test)
    result_logger.bulk_update_entries(list_of_dict)
    logger.info('Updating database')
    con = SqlConnector(result_logger.filepath, db_endpoint, db_name, db_username, db_password)
    con.bulk_insert_csv(result_table, [FIELDNAME_EP, FIELDNAME_TIME, FIELDNAME_BURNED_MEMBER])


def main():
    start = datetime.datetime.now()
    try:
        logger.info('Setting up pipeline')
        # Initialise strings from config file
        try:
            config = configparser.ConfigParser()
            config.read('strings.ini')
            # pipeline parameters
            temp_dir = None
            display = config.getboolean('PIPELINE', 'display')
            s3_bucket_name = config.get('PIPELINE', 'episode_bucket_name')
            image_directory = config.get('PIPELINE', 'local_image_directory')
            if os.path.isdir(image_directory):
                logger.info(f'Images will be saved @ {image_directory}')
            else:
                old = image_directory
                if temp_dir is None:
                    temp_dir = TemporaryDirectory()
                image_directory = os.path.join(temp_dir.name, 'images')
                os.mkdir(image_directory)
                if old is None or len(old.strip()) == 0:
                    logger.warning(f'No directory specified. Output images will be cached @ {image_directory}')
                else:
                    logger.warning(f'"{old}" is not a directory. Output images will be cached @ {image_directory}')
            result_logger_file_path = config.get('PIPELINE', 'result_file_path')
            if os.path.isfile(result_logger_file_path):
                logger.info(f'Results will be saved @ {result_logger_file_path}')
            else:
                old = result_logger_file_path
                if temp_dir is None:
                    temp_dir = TemporaryDirectory()
                result_logger_file_path = os.path.join(temp_dir.name, 'results.csv')
                open(result_logger_file_path, 'w').write('')
                if old is None or len(old.strip()) == 0:
                    logger.warning(f'No result file specified. Results will be cached @ {result_logger_file_path}')
                else:
                    logger.warning(f'{old} is not a file. Results will be cached @ {result_logger_file_path}')
            result_logger = ResultLogger(result_logger_file_path)
            # skull detection (phase 1) parameters
            sample_rate = config.getint('SKULL', 'video_sample_rate')
            model_version = config.get('SKULL', 'model_version')
            confidence = config.getfloat("SKULL", "confidence_threshold")
            # face recognition (phase 2) parameters
            detection_method = config.get('FACE', 'detection_method')
            encodings = config.get('FACE', 'encodings_path')
            encodings = pickle.load(open(encodings, 'rb'))
            # updating database (phase 3) parameters
            result_table = config.get('AWS RDS', 'result_table_name')
            db_server_endpoint = config.get('AWS RDS', 'endpoint')
            db_name = config.get('AWS RDS', 'db_name')
            db_username = config.get('AWS RDS', 'uname')
        except configparser.Error as ex:
            logger.error("Failure while initializing config variables")
            raise ex

        # Initialize job parameters from environment variables
        try:
            db_password = os.environ[RDS_PASSWORD]
        except KeyError as er:
            logger.error(f'{RDS_PASSWORD} environment variable not set')
            raise er
        try:
            job_idx = int(os.environ[JOB_INDEX])
        except KeyError as er:
            logger.error(f'{JOB_INDEX} environment variable not set')
            raise er
        try:
            job_idx_offset = int(os.environ[JOB_INDEX_OFFSET])
        except KeyError as er:
            logger.error(f'{JOB_INDEX_OFFSET} environment variable not set')
            raise er
        episode = job_idx + job_idx_offset

        # phase 1
        logger.info('Starting pipeline phase 1: extract frames with skulls...')
        phase1(
            episode_num=episode,
            bucket=s3_bucket_name,
            output_directory=image_directory,
            result_logger=result_logger,
            sample_rate=sample_rate,
            model_version=model_version,
            confidence=confidence,
            display=display
        )
        # phase 2
        logger.info('Starting pipeline phase 2: recognize faces in extracted frames...')
        phase2(
            input_directory=image_directory,
            known_face_encodings=encodings,
            detection_method=detection_method,
            result_logger=result_logger,
            display=display
        )
        # phase 3
        logger.info('Starting pipeline phase 3: update database...')
        phase3(
            result_logger=result_logger,
            db_endpoint=db_server_endpoint,
            db_name=db_name,
            db_username=db_username,
            db_password=db_password,
            result_table=result_table
        )
        logger.info('Pipeline complete')
    except:
        logger.error('Pipeline failed.')
        traceback.print_exc()
    finally:
        logger.info(f'Time Elapsed: {datetime.datetime.now() - start}')


if __name__ == "__main__":
    main()

