from model import vid_recognition as vr
from logger.base_logger import logger
from utils.csv_logger import CsvLogger
import argparse
import cv2
import os
import configparser

# Main script for skull detection and extraction of relevant frames from episodes
# Will be used in phase 1 for batch processing of the episodes
# Developed Date: 30 June 2020





# returns filepath of an unprocessed episode
def select_unprocessed_episode(directory):
    unprocessed_directory_path = os.path.join(directory, "episodes", "unprocessed")
    processed_directory_path = os.path.join(directory, "episodes", "processed")
    for ep in os.listdir(unprocessed_directory_path):
        episode_path = os.path.join(unprocessed_directory_path, ep)
        os.rename(episode_path, os.path.join(processed_directory_path, ep))
        episode_path = os.path.join(processed_directory_path, ep)
        return episode_path
    return None


def save_extracted_frame(extracted_frame, directory):
    filename = "{}_{}.jpg".format(
        extracted_frame.episode_number,
        extracted_frame.timestamp.replace(':', '_')
    )
    dst_path = os.path.join(directory, "images", "unprocessed", filename)
    cv2.imwrite(dst_path, extracted_frame.frame)


# extracts frames with skull and saves frames and additional data on is a csv file in the specified directory
def extract_and_save_skull_frames(path, detection_method, sampling_period, directory, display):
    logger.info("processing video to extract skull frames...")
    extracted_frames = vr.process_stream(path, sampling_period, detection_method, display)

    c_log = CsvLogger(directory)
    logger.info('saving csv data to {}'.format(c_log.filename))
    for extracted_frame in extracted_frames:
        #save image
        save_extracted_frame(extracted_frame, directory)
        #add to data.csv
        c_log.add_skull_entry(extracted_frame.episode_number, extracted_frame.timestamp, extracted_frame.coord)


if __name__ == "__main__":
    # Initialise strings from config file
    config = configparser.ConfigParser()
    config.read('strings.ini')

    # Initialising arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-w", "--working_directory", required=True,
                    help="path to the directory containing episodes, images folder, and data.csv file")
    ap.add_argument("-y", "--display", type=int, default=1, help="whether or not to display output frame to screen")
    ap.add_argument("-d", "--detection_method", type=str, default="cnn",
                    help="detection model to use: either 'hog'/'cnn'")
    ap.add_argument("-s", "--sample_period", type=int, default=100,
                    help="milliseconds between each sampled frame, default: 100")
    args = vars(ap.parse_args())

    logger.info('start processing remaining unprocessed episode...')

    while True:
        logger.info('searching for unprocessed episode...')
        path = select_unprocessed_episode(args['working_directory'])

        if not path:
            logger.info('no unprocessed episodes found. exiting...')
            break

        logger.info('processing [{}]...'.format(path))

        extract_and_save_skull_frames(
            path,
            args["detection_method"],
            args["sample_period"],
            args["working_directory"],
            args["display"]
        )

        logger.info('completed processing [{}].'.format(path))
