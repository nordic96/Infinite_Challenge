from model import vid_recognition as vr
from model import azure_face_recognition as afr
from logger.base_logger import logger
from logger.result_logger import ResultLogger, FIELDNAME_BURNED_MEMBER, FIELDNAME_EP, FIELDNAME_TIME
from utils.sql_connecter import SqlConnector
from tempfile import TemporaryDirectory
from shutil import move
import boto3
import cv2
import os
import configparser
import traceback
import datetime

Timestamp = vr.Timestamp
JOB_INDEX = 'AWS_BATCH_JOB_ARRAY_INDEX'
JOB_INDEX_OFFSET = 'IC_INDEX_OFFSET'
AWS_RDS_PASSWORD = 'IC_RDS_PASSWORD'
AZURE_KEY_SKULL = 'IC_AZURE_KEY_SKULL'
AZURE_KEY_FACE = 'IC_AZURE_KEY_FACE'


# Main script for skull detection and extraction of relevant frames from episodes
# Will be used in phase 1 for batch processing of the episodes
# Developed Date: 30 June 2020
# Last Modified: 6 Jul 2020


# Assign an IAM Role with permission to GetObject from S3, boto3 will get
# credentials from instance metadata
# https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html
def phase1_s3_download(region_name, bucket_name, filename):
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


def phase1_cache_episode_from_s3(region, bucket_name, episode_name):
    video = phase1_s3_download(region, bucket_name, episode_name)
    dir = TemporaryDirectory()
    path = os.path.join(dir.name, episode_name)
    file = open(path, 'rb')
    file.write(video)
    logger.info(f'Episode will be cached @ {file.name}')
    return file


def save_extracted_frame(directory, frame):
    filename = f"{frame.episode_number}_{frame.timestamp.with_delimiter('_')}.jpg"
    logger.info(filename)
    dst_path = os.path.join(directory, filename)
    cv2.imwrite(dst_path, frame.frame)


# 1. process a single video using model
# 2. cache images with skulls
# 3. update result.csv for each image
def phase1(episode_num, region, bucket, output_directory, result_logger, sample_rate, azure_key, confidence, model_version, display):
    try:
        # get episode from S3
        episode_filename = f'episode{episode_num}.mp4'
        logger.info(f'Retrieving {bucket}/{episode_filename} from AWS S3({region})')
        cached_episode = phase1_cache_episode_from_s3(region, bucket, episode_filename)
        video_path = cached_episode.name
        # process episode
        logger.info('Processing video')
        extracted_frames = vr.process_stream(
            video_path=video_path,
            azure_key=azure_key,
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
def phase2(input_directory, unknown_faces_dir, result_logger, endpoint, azure_key, person_group_id, display):
    images = os.listdir(input_directory)
    logger.info(f'Found {len(images)} frame(s) to process...')
    fc = afr.authenticate_client(endpoint, azure_key)
    mappings = afr.recognise_faces(fc, input_directory, person_group_id, unknown_faces_dir, label_and_save=display)
    for filename in mappings:
        names, faces = mappings[filename]
        entry_id = filename.split('.')[0]
        ep, h, m, s, ms = entry_id.split('_')
        result_logger.update_face_entry(
            ep,
            Timestamp(h, m, ms, s),
            faces,
            names
        )


def phase3(result_logger: ResultLogger, db_endpoint, db_name, db_username, db_password, result_table):
    logger.info('Estimating burned members...')
    list_of_dict = result_logger.estimate_burned_member()
    result_logger.bulk_update_entries(list_of_dict)
    logger.info('Updating database...')
    con = SqlConnector(result_logger.filepath, db_endpoint, db_name, db_username, db_password)
    con.bulk_insert_csv(result_table, [FIELDNAME_EP, FIELDNAME_TIME, FIELDNAME_BURNED_MEMBER])


def save_cached_files(cache_dir_path, save_cached_path):
    for resource in os.listdir(cache_dir_path):
        try:
            src = os.path.join(cache_dir_path, resource)
            dst = os.path.join(save_cached_path, resource)
            if os.path.isfile(src):
                n = 1
                name, ext = dst.split('.', 1)
                while os.path.exists(dst):
                    dst = f'{name}_({n}).{ext}'
                move(src, dst)
                logger.info(f'Cached file [{src}] was saved @ [{dst}]')
            elif os.path.isdir(src):
                save_cached_files(src, dst)
        except BaseException as ex:
            logger.warning(f'Error occurred while trying to saved cached file [{resource}]. File will not be saved: {ex.__class__.__name__}')


def main():
    start = datetime.datetime.now()
    try:
        logger.info('Initializing pipeline parameters...')
        # Initialise strings from config file
        config = configparser.ConfigParser()
        # pipeline main parameters
        try:
            config.read('strings.ini')
            # pipeline parameters
            db_password = os.environ[AWS_RDS_PASSWORD]
            try:
                job_idx = int(os.environ[JOB_INDEX])
            except KeyError:
                job_idx = 0
            job_idx_offset = int(os.environ[JOB_INDEX_OFFSET])
            episode = job_idx + job_idx_offset
            display = config.getboolean('PIPELINE', 'display')
            s3_bucket_name = os.environ['IC_BUCKET_NAME']
            s3_bucket_region = os.environ['IC_BUCKET_REGION']
            image_directory = config.get('PIPELINE', 'local_image_directory')
            save_cached = config.getboolean('PIPELINE', 'save_if_cached')
            save_cached_path = config.get('PIPELINE', 'save_cached_path')
            cache_dir = None
            if os.path.isdir(image_directory):
                logger.info(f'Images will be saved @ {image_directory}')
            else:
                old = image_directory
                if cache_dir is None:
                    cache_dir = TemporaryDirectory()
                image_directory = os.path.join(cache_dir.name, 'images')
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
                if cache_dir is None:
                    cache_dir = TemporaryDirectory()
                result_logger_file_path = os.path.join(cache_dir.name, 'results.csv')
                open(result_logger_file_path, 'w').write('')
                if old is None or len(old.strip()) == 0:
                    logger.warning(f'No result file specified. Results will be cached @ {result_logger_file_path}')
                else:
                    logger.warning(f'{old} is not a file. Results will be cached @ {result_logger_file_path}')

            if cache_dir is None:
                save_cached = False

            result_logger = ResultLogger(result_logger_file_path)
        except KeyError as er:
            logger.error('Error while initializing pipeline parameters due to missing environment variable.')
            raise er
        except BaseException as ex:
            logger.error("Error while initializing pipeline miscellaneous parameters")
            logger.error("Failure while initializing pipeline parameters")
            raise ex
        # skull detection (phase 1) parameters
        try:
            sample_rate = config.getint('SKULL', 'video_sample_rate')
            model_version = config.get('SKULL', 'model_version')
            confidence = config.getfloat("SKULL", "confidence_threshold")
            azure_key_skull = os.environ[AZURE_KEY_SKULL]
        except KeyError as er:
            logger.error(f'{AZURE_KEY_SKULL} environment variable not set')
            raise er
        except BaseException as ex:
            logger.error("Failure while initializing pipeline phase 1 parameters")
            raise ex
        # face recognition (phase 2) parameters
        try:
            endpoint = config.get('FACE', 'endpoint')
            person_group_id = config.get('FACE', 'person_group_id')
            unknown_faces_dir = config.get('FACE', 'unknown_faces_dir')
            azure_key_face = os.environ[AZURE_KEY_FACE]
        except KeyError as er:
            logger.error(f'{AZURE_KEY_FACE} environment variable not set')
            raise er
        except BaseException as ex:
            logger.error("Failure while initializing pipeline phase 2 parameters")
            raise ex
        # updating database (phase 3) parameters
        try:
            result_table = config.get('AWS RDS', 'result_table_name')
            db_server_endpoint = config.get('AWS RDS', 'endpoint')
            db_name = config.get('AWS RDS', 'db_name')
            db_username = config.get('AWS RDS', 'uname')
        except BaseException as ex:
            logger.error("Failure while initializing pipeline phase 3 parameters")
            raise ex

        # phase 1
        logger.info('Starting pipeline phase 1: extract frames with skulls...')
        phase1(
            episode_num=episode,
            region=s3_bucket_region,
            bucket=s3_bucket_name,
            output_directory=image_directory,
            result_logger=result_logger,
            sample_rate=sample_rate,
            azure_key=azure_key_skull,
            model_version=model_version,
            confidence=confidence,
            display=display
        )
        # phase 2
        logger.info('Starting pipeline phase 2: recognize faces in extracted frames...')
        phase2(
            input_directory=image_directory,
            unknown_faces_dir=unknown_faces_dir,
            result_logger=result_logger,
            endpoint=endpoint,
            azure_key=azure_key_face,
            person_group_id=person_group_id,
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
        if save_cached:
            logger.info(f'Saving cached files to {save_cached_path}')
            save_cached_files(cache_dir.name, save_cached_path)

        logger.info('Pipeline complete')
    except:
        logger.error('Pipeline failed.')
        traceback.print_exc()
    finally:
        logger.info(f'Time Elapsed: {datetime.datetime.now() - start}')


if __name__ == "__main__":
    main()

