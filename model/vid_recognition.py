import subprocess

import configparser
import face_recognition  # temporarily used in place of skull_detection
import argparse
import imutils
import os
import re
import cv2
from logger.base_logger import logger
from dataset.skull.yolov5.utils.utils import xywh2xyxy

# Description: Skull Recognition with video stream input
# Developed Date: 25 June 2020
# Last Modified: 30 June 2020


class ExtractedFrame:
    def __init__(self, episode_number, frame, frame_number, timestamp, coord):
        self.episode_number = episode_number
        self.frame = frame
        self.frame_number = frame_number
        self.timestamp = timestamp
        self.coord = coord


def milli_to_timestamp(ms):
    h, ms = divmod(ms, 60*60*1000)
    m, ms = divmod(ms, 60*1000)
    s, ms = divmod(ms, 1000)
    timestamp = "{}:{}:{}:{}".format(h, m, s, ms)
    return timestamp


def get_episode_number(filename):
    # get base file name
    episode_num = os.path.basename(filename)
    # strip file extension
    episode_num = episode_num.split('.')[0]
    # strip non-digits
    episode_num = re.sub('[^0-9]', '', episode_num)
    return episode_num


def detect_skull(frame, detection_method, config):
    r = 100
    yolov5_path = config.get("SKULL", "path_yolov5")
    cache_path = config.get("SKULL", "path_cache")
    result_path = config.get("SKULL", "path_result_cache")
    cv2.imwrite(f"{cache_path}/skull_detect_cache.png", frame)

    subprocess.check_call([
        "python", f"{yolov5_path}/detect.py", "--weights", f"{yolov5_path}/weights/last_yolov5s_results.pt",
        "--img", config.get("SKULL", "image_num"), "--conf", config.get("SKULL","confidence"), "--source", cache_path,
        "--save-txt", "--out", result_path])

    boxes = []
    coord_path = f"{result_path}/skull_detect_cache.txt"
    if os.path.isfile(coord_path):
        with open(coord_path) as f:
            for line in f:
                inner_list = [elt.strip() for elt in line.split(" ")]
                inner_list = list(map(float, filter(None, inner_list[1:])))
                inner_list = xywh2xyxy(inner_list)
                boxes.append(inner_list)

    if len(boxes) > 0:
        return r, boxes
    else:
        return None


def label_frame(frame, timestamp, boxes):
    labelled = frame.copy()
    for (top, right, bottom, left) in boxes:
        cv2.rectangle(labelled, (left, top), (right, bottom), (0, 255, 0), 2)
        y = top - 15 if top - 15 > 15 else top + 15
        cv2.putText(labelled, "skull", (left, y), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)

    cv2.putText(labelled, timestamp, (5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)
    return labelled


def display_sampled_frame(frame, timestamp, skull_coords):
    cv2.imshow("Frame", label_frame(frame, timestamp, skull_coords))
    key = cv2.waitKey(1) & 0xFF
    if key == ord("q"):
        return True
    else:
        return False


def calculate_skip_rate(vid, ms_skip_rate):
    return int(vid.get(cv2.CAP_PROP_FPS) * (ms_skip_rate / 1000))


# returns relevant frames and data (coordinates)
def process_stream(video_path, sample_period, detection_method, display):
    vid_cap = cv2.VideoCapture(video_path)
    # initialize output list
    extracted_frames = []
    # processing parameters
    episode_number = get_episode_number(video_path)
    frame_skip_rate = calculate_skip_rate(vid_cap, sample_period)
    while vid_cap.isOpened():
        success, frame = vid_cap.read()
        if not success:
            logger.info("No more frames from source file. Exiting...")
            break

        frame_number = int(vid_cap.get(cv2.CAP_PROP_POS_FRAMES))
        millisecond = int(vid_cap.get(cv2.CAP_PROP_POS_MSEC))
        if frame_number % frame_skip_rate != 0:
            continue

        # Time stamping
        timestamp = milli_to_timestamp(millisecond)

        # Determine skull coordinates
        config=configparser.ConfigParser()
        config.read('../strings.ini')
        retval = detect_skull(frame, detection_method, config)
        skull_coords = []
        if retval:
            resize_factor, skull_coords_resized = retval
            for (top, right, bottom, left) in skull_coords_resized:
                top = int(top * resize_factor)
                right = int(right * resize_factor)
                bottom = int(bottom * resize_factor)
                left = int(left * resize_factor)
                skull_coords.append((top, right, bottom, left))
            extracted_frames.append(ExtractedFrame(episode_number, frame, frame_number, timestamp, skull_coords))
        logger.info('sampled_frame: {} | timestamp: {} | skulls detected: {}'.format(frame_number, timestamp, skull_coords))

        # Display squares on sampled frames where skulls are located
        if display == 1:
            display_sampled_frame(frame, timestamp, skull_coords)

    cv2.destroyAllWindows()
    return extracted_frames


if __name__ == "__main__":
    # Initializing arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input", required=True, type=str, help="path to unprocessed episode file")
    ap.add_argument("-y", "--display", type=int, default=1, help="whether or not to display output frame to screen")
    ap.add_argument("-d", "--detection_method", type=str, default="cnn",
                    help="skull detection model to use: either 'hog'/'cnn'")
    ap.add_argument("-s", "--sample_period", type=int, default=1000,
                    help="milliseconds between each sampled frame, default: 100")
    args = vars(ap.parse_args())

    logger.info('video processing [{}] starts..'.format(args["input"]))
    process_stream(args['input'], args["sample_period"], args["detection_method"], args["display"])
