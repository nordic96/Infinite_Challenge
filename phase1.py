from model import vid_recognition as vr
from logger.base_logger import logger
from utils.csv_logger import CsvLogger
import argparse
import pickle
import cv2
import os
import configparser
import re

# Main script for skull detection and extraction of relevant frames from episodes
# Will be used in phase 1 for batch processing of the episodes
# Developed Date: 30 June 2020


def get_episode_number(filename):
    # get base file name
    episode_num = os.path.basename(filename)
    # strip file extension
    episode_num = episode_num.split('.')[0]
    # strip non-digits
    episode_num = re.sub('[^0-9]', '', episode_num)
    return episode_num


# returns the video stream of an unprocessed episode
def fetch_unprocessed_episode():
    # 1. check list of unprocessed episodes
    episode_directory_path = os.path.join(args["input"], "unprocessed")
    episode_directory = os.listdir(episode_directory_path)

    if len(episode_directory) > 0:
        # 2. take an unprocessed episode from the list
        episode = episode_directory[0]
        episode_src_path = os.path.join(episode_directory_path, episode)

        # 3. removed video from unprocessed episode list
        episode_dst_path = os.path.join(args["input"], "processed", episode)
        os.rename(episode_src_path, episode_dst_path)

        # 4. return video as stream for processing
        return get_episode_number(episode_dst_path), cv2.VideoCapture(episode_dst_path)
    else:
        return None


# extracts frames with skull and saves frames and additional data on is a csv file in the specified directory
def extract_and_save_skull_frames(video_stream, detection_method, sampling_period, output_directory, display):
    c_log = CsvLogger(output_directory)
    logger.info("processing video to extract skull frames...")
    extracted_frames = vr.process_stream(video_stream, sampling_period, detection_method, display)
    for extracted_frame in extracted_frames:
        output_filename = "{}.jpg".format(extracted_frame.timestamp.replace(":", "_"))
        logger.info("saving [{}]...".format(output_filename))
        cv2.imwrite(os.path.join(output_directory,output_filename), extracted_frame.frame)
        c_log.add_skull_entry(extracted_frame.frame_number, extracted_frame.timestamp, extracted_frame.coord)


if __name__ == "__main__":
    # Initialise strings from config file
    config = configparser.ConfigParser()
    config.read('strings.config')

    # Initialising arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input", required=True, help="path to the directory containing unprocessed episodes")
    ap.add_argument("-o", "--output", required=True, help="path to the directory where extracted images will be saved")
    ap.add_argument("-y", "--display", type=int, default=1, help="whether or not to display output frame to screen")
    ap.add_argument("-d", "--detection_method", type=str, default="cnn",
                    help="detection model to use: either 'hog'/'cnn'")
    ap.add_argument("-s", "--sample_period", type=int, default=100,
                    help="milliseconds between each sampled frame, default: 100")
    args = vars(ap.parse_args())

    logger.info('start processing remaining unprocessed episode...')
    while True:
        logger.info('attempting to fetch an unprocessed episode...')
        episode = fetch_unprocessed_episode()
        if episode is None:
            logger.info('no unprocessed episodes found. exiting...')
            break

        episode_number, vs = episode
        logger.info('processing episode [{}]...'.format(episode_number))
        output_directory = os.path.join(args["output"], "episode{}".format(episode_number))
        if not os.path.exists(output_directory):
            logger.info('[{}] does not exist, making directory...'.format(output_directory))
            os.makedirs(output_directory)

        extract_and_save_skull_frames(
            vs,
            args["detection_method"],
            args["sample_period"],
            output_directory,
            args["display"]
        )
        logger.info('completed processing episode [{}].'.format(episode_number))
