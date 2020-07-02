from model import frame_recognition as fr
from logger.base_logger import logger
from utils.csv_logger import CsvLogger
import argparse
import os
import pickle
import configparser

# Main script for facial detection in extracted sampled frames
# Will be used in phase 2 for batch processing of the episodes
# Developed Date: 30 June 2020


# returns filepath of an unprocessed episode
def select_unprocessed_img(directory):
    unprocessed_directory_path = os.path.join(directory, "images", "unprocessed")
    processed_directory_path = os.path.join(directory, "images", "processed")
    for img in os.listdir(unprocessed_directory_path):
        img_path = os.path.join(unprocessed_directory_path, img)
        os.rename(img_path, os.path.join(processed_directory_path, img))
        img_path = os.path.join(processed_directory_path, img)
        return img_path
    return None


def process_image(img_path, data, detection_method, directory, display):
    processed_img = fr.process_image(img_path, data, detection_method, display)
    c_log = CsvLogger(directory)
    c_log.update_face_entry(
        processed_img.episode_number,
        processed_img.timestamp,
        processed_img.coordinate,
        processed_img.name
    )


if __name__ == "__main__":
    # Initialise strings from config file
    config = configparser.ConfigParser()
    config.read('strings.ini')

    # Initialising arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-e", "--encodings", required=True, help="path to serialized db of facial encodings")
    ap.add_argument("-w", "--working_directory", required=True,
                    help="path to the directory containing episodes, images folder, and data.csv file")
    ap.add_argument("-y", "--display", type=int, default=1, help="whether or not to display output frame to screen")
    ap.add_argument("-d", "--detection_method", type=str, default="cnn",
                    help="detection model to use: either 'hog'/'cnn'")
    args = vars(ap.parse_args())

    logger.info('start processing remaining unprocessed episode...')
    while True:
        logger.info('searching for unprocessed img...')
        path = select_unprocessed_img(args['working_directory'])

        if not path:
            logger.info('no unprocessed img found. exiting...')
            break
        logger.info('loading the encoding file: {}'.format(args["encodings"]))
        data = pickle.loads(open(args["encodings"], "rb").read())

        logger.info('start processing image [{}]'.format(path))
        process_image(path, data, args["detection_method"], args["working_directory"], args["display"])
        logger.info('completed processing image [{}].'.format(path))
