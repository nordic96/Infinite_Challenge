import subprocess
import os
import re
import cv2
import model.skull_detection as sd
from logger.base_logger import logger


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


class Timestamp:
    DEFAULT_DELIMITER = ':'

    def __init__(self, h, m, s, ms, delimiter=DEFAULT_DELIMITER):
        self.delimiter = delimiter
        self.h = int(h)
        self.m = int(m)
        self.s = int(s)
        self.ms = int(ms)

    @staticmethod
    def from_milliseconds(ms, delimiter=DEFAULT_DELIMITER):
        ms = int(ms)
        h, ms = divmod(ms, 60 * 60 * 1000)
        m, ms = divmod(ms, 60 * 1000)
        s, ms = divmod(ms, 1000)
        return Timestamp(h, m, s, ms, delimiter)

    def with_delimiter(self, delimiter):
        return Timestamp(self.h, self.m, self.s, self.ms, delimiter)

    def __str__(self):
        return "{}{delim}{:02d}{delim}{:02d}{delim}{:03d}".format(self.h, self.m, self.s, self.ms, delim=self.delimiter)


def get_episode_number(filename):
    # get base file name
    episode_num = os.path.basename(filename)
    # strip file extension
    episode_num = episode_num.split('.')[0]
    # strip non-digits
    episode_num = re.sub('[^0-9]', '', episode_num)
    return episode_num


# Skull detection with Azure Cognitive Services
def detect_skull(frame, key, confidence, model_version):
    # resize_factor format: [height, width, channel]
    r = frame.shape
    ret, jpeg = cv2.imencode('.jpg', frame)
    boxes = sd.detect(jpeg.tobytes(), key, confidence, model_version)
    return r, boxes


# Skull detection with local YOLOv5 component
def detect_skull_yolo(frame, timestamp, confidence, image_num, yolov5_path, cache_path, result_path):
    # resize_factor format: [height, width, channel]
    r = frame.shape
    # Get paths
    coord_path = f"{result_path}/skull_detect_cache.txt"
    cv2.imwrite(f"{cache_path}/skull_detect_cache.png", frame)
    # Bash command to yolov5 detect.py for object detection in frame
    logger.info(f"\nProcessing: {timestamp}")
    subprocess.check_call([
        "python", f"{yolov5_path}/detect.py",
        "--weights", f"{yolov5_path}/weights/last_yolov5s_results.pt",
        "--img", image_num,
        "--conf", confidence,
        "--source", cache_path,
        "--save-txt",
        "--out", result_path])
    # Read skull coordinates from cached result
    boxes = []
    if os.path.isfile(coord_path):
        with open(coord_path) as f:
            for line in f:
                inner_list = [elt.strip() for elt in line.split(" ")]
                inner_list = list(map(float, filter(None, inner_list[1:])))
                # Convert nx4 boxes from xywh to yxyx
                # Original: [x_center, y_center, width, height]
                # Output: [tpo_y, right_x, bottom_y, left_x]
                assert len(inner_list) == 4
                x1 = (2 * inner_list[0] + inner_list[2]) / 2
                x2 = x1 - inner_list[2]
                y2 = (2 * inner_list[1] + inner_list[3]) / 2
                y1 = y2 - inner_list[3]
                boxes.append([y1, x1, y2, x2])
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
    cv2.waitKey(1000)


def calculate_skip_rate(vid, ms_skip_rate):
    return int(vid.get(cv2.CAP_PROP_FPS) * (ms_skip_rate / 1000))


# returns relevant frames and data (coordinates)
def process_stream(video_path, azure_key, confidence, model_version, sample_rate=1000, display=False):
    logger.info(f'Processing {os.path.basename(video_path)} with these settings: Sample rate={sample_rate}ms; Confidence={confidence}; Model Version={model_version}')
    vid_cap = cv2.VideoCapture(video_path)
    # initialize output list
    extracted_frames = []
    # processing parameters
    episode_number = get_episode_number(video_path)
    frame_skip_rate = calculate_skip_rate(vid_cap, sample_rate)
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
        timestamp = Timestamp.from_milliseconds(millisecond)

        # Determine skull coordinates
        retval = detect_skull(frame, azure_key, confidence, model_version)
        skull_coords = []
        if retval:
            resize_factor, skull_coords_resized = retval
            for (top, right, bottom, left) in skull_coords_resized:
                top = int(top * resize_factor[0])
                right = int(right * resize_factor[1])
                bottom = int(bottom * resize_factor[0])
                left = int(left * resize_factor[1])
                skull_coords.append((top, right, bottom, left))
            if len(skull_coords) > 0:
                extracted_frames.append(ExtractedFrame(episode_number, frame, frame_number, timestamp, skull_coords))
        logger.info('[{}] skulls detected: {}'.format(timestamp, skull_coords))

        # Display squares on sampled frames where skulls are located
        if display:
            display_sampled_frame(frame, timestamp, skull_coords)

    cv2.destroyAllWindows()
    return extracted_frames


if __name__ == "__main__":
    import argparse
    # Initializing arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input", required=True, type=str, help="path to unprocessed episode file")
    ap.add_argument("-y", "--display", type=bool, default=True, help="whether or not to display output frame to screen")
    ap.add_argument("-m", "--model_version", type=str)
    ap.add_argument("-c", "--confidence", type=float)
    args = vars(ap.parse_args())

    logger.info('video processing [{}] starts..'.format(args["input"]))
    process_stream(args['input'], args["display"], args['confidence'], args['model_version'])
