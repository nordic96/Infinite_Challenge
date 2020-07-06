from model import vid_recognition as vr
from model import frame_recognition as fr
from logger.base_logger import logger
from utils.csv_logger import CsvLogger
from tempfile import TemporaryDirectory
import boto3
import cv2
import os
import configparser
import traceback
import datetime
import pickle

JOB_INDEX_KEY = 'AWS_BATCH_JOB_ARRAY_INDEX'
IDX_OFFSET_KEY = 'EPISODE_OFFSET'

# Main script for skull detection and extraction of relevant frames from episodes
# Will be used in phase 1 for batch processing of the episodes
# Developed Date: 30 June 2020
# Last Modified: 6 Jul 2020

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
def phase1(episode_num, bucket, output_directory, result_logger, sample_rate, weights, cache_path, result_path, image_num, confidence):
    try:
        # get episode
        episode_filename = f'episode{episode_num}.mp4'
        cached_episode = phase1_cache_episode_from_s3(bucket, episode_filename)
        video_path = cached_episode.name
        #video_path = f'resources/sample_episodes/episode{episode_num}.mp4'
        # process episode
        extracted_frames = vr.process_stream(
            video_path=video_path,
            sample_rate=sample_rate,
            cache_path=cache_path,
            result_path=result_path,
            image_num=image_num,
            confidence=confidence,
            weights=weights,
            display=False
        )
        # update results and cache image locally on container
        logger.info('Caching extracted frames')
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
def phase2(input_directory, known_face_encodings, detection_method, result_logger):
    images = os.listdir(input_directory)
    logger.info(f'Found {len(images)} frame(s) to process...')
    count = 0
    total = len(images)
    for image in images:
        try:
            count += 1
            path = os.path.join(input_directory, image)
            logger.info(f'Processing frame {count}/{total}') # debug
            processed_img = fr.process_image(path, known_face_encodings, detection_method)
            result_logger.update_face_entry(
                processed_img.episode_number,
                processed_img.timestamp,
                processed_img.coordinate,
                processed_img.name
            )
        except BaseException as ex:
            logger.error('frame {}/{}: {}\n{}'.format(count, total, ex.__class__.__name__, '\n'.join(ex.args)))
            raise ex
def main():
    start = datetime.datetime.now()
    try:
        # Initialize job parameters from environment variables
        logger.info('Setting up pipeline')
        try:
            episode = int(os.environ[JOB_INDEX_KEY]) + int(os.environ[IDX_OFFSET_KEY])
        except KeyError as ex:
            logger.error('Environment variables not set')
            raise ex
        # Initialise strings from config file
        try:
            config = configparser.ConfigParser()
            config.read('strings.ini')
            # pipeline parameters
            s3_bucket_name = config.get('PIPELINE', 'episode_bucket_name')
            image_directory = config.get('PIPELINE', 'local_image_directory')
            result_logger_file_path = config.get('PIPELINE', 'result_file_path')
            if not image_directory:
                tempdir_image = TemporaryDirectory()
                image_directory = tempdir_image.name
                logger.warning(f'No image directory specified. Output images will be cached @ {image_directory}')
            if not result_logger_file_path or not result_logger_file_path.endswith('.csv'):
                tempdir_results = TemporaryDirectory()
                result_logger_file_path = os.path.join(tempdir_results.name, 'results.csv')
                open(result_logger_file_path, 'w').write('')
                logger.warning(f'No result file specified. Results will be cached @ {result_logger_file_path}')
            result_logger = CsvLogger(result_logger_file_path)
            # skull detection (phase 1) parameters
            sample_rate = config.getint('SKULL', 'video_sample_rate')
            weights_file_path = config.get("SKULL", "weights")
            cache_path = config.get("SKULL", "path_cache")
            result_path = config.get("SKULL", "path_result_cache")
            image_num = config.getint("SKULL", "image_num")
            confidence = config.getfloat("SKULL", "confidence_threshold")
            # face recognition (phase 2) parameters
            detection_method = config.get('FACE', 'detection_method')
            encodings = config.get('FACE', 'encodings_path')
            encodings = pickle.load(open(encodings, 'rb'))
        except configparser.Error as ex:
            logger.error("Failure while initializing config variables")
            raise ex

        # phase 1
        logger.info('Starting pipeline phase 1...')
        phase1(
            episode_num=episode,
            bucket=s3_bucket_name,
            output_directory=image_directory,
            result_logger=result_logger,
            sample_rate=sample_rate,
            weights=weights_file_path,
            cache_path=cache_path,
            result_path=result_path,
            image_num=image_num,
            confidence=confidence
        )
        # phase 2
        logger.info('Starting pipeline phase 2...')
        phase2(
            input_directory=image_directory,
            known_face_encodings=encodings,
            detection_method=detection_method,
            result_logger=result_logger
        )
        logger.info('Pipeline complete')
    except:
        logger.error('Pipeline failed.')
        traceback.print_exc()
    finally:
        logger.info(f'Time Elapsed: {datetime.datetime.now() - start}')


if __name__ == "__main__":
    main()

