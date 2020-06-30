import face_recognition  # temporarily used in place of skull_detection
import argparse
import imutils
import os
import re
import cv2
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


def milli_to_timestamp(ms):
    h, ms = divmod(ms, 60*60*1000)
    m, ms = divmod(ms, 60*1000)
    s, ms = divmod(ms, 1000)
    timestamp = "{}:{}:{}:{}".format(h,m,s,ms)
    return timestamp


def get_episode_number(filename):
    # get base file name
    episode_num = os.path.basename(filename)
    # strip file extension
    episode_num = episode_num.split('.')[0]
    # strip non-digits
    episode_num = re.sub('[^0-9]', '', episode_num)
    return episode_num


# returns the video stream of an unprocessed episode
def fetch_unprocessed_img(img_path):
    ep, timestamp = get_metadata(img_path)
    img = cv2.imread(img_path)
    return ep, timestamp, img


# temporarily uses face detection model before skull detection is complete
def detect_skull(frame, detection_method):
    # Frame scaling
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    rgb = imutils.resize(frame, width=280)
    r = frame.shape[1] / float(rgb.shape[1])

    # Detection
    boxes = face_recognition.face_locations(rgb, model=detection_method)

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


def display_sampled_frame(frame, timestamp, skull_coords, display):
    if display == 0:
        pass
    cv2.imshow("Frame", label_frame(frame, timestamp, skull_coords))
    key = cv2.waitKey(1) & 0xFF
    if key == ord("q"):
        return True
    else:
        return False


# returns relevant frames and data (coordinates)
def process_stream(video_path, sample_period, detection_method, display):
    video_stream = cv2.VideoCapture(video_path)
    episode_number = get_episode_number(video_path)
    extracted_frames = []
    while video_stream.isOpened():
        success, frame = video_stream.read()

        if not success:
            logger.info("No more frames from source file. Exiting...")
            break

        frame_number = int(video_stream.get(cv2.CAP_PROP_POS_FRAMES))
        millisecond = int(video_stream.get(cv2.CAP_PROP_POS_MSEC))

        if millisecond % sample_period != 0:
            continue

        # Time stamping
        timestamp = milli_to_timestamp(millisecond)

        # Determine skull coordinates
        retval = detect_skull(frame, detection_method)
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
        interrupted = display_sampled_frame(frame, timestamp, skull_coords, display)
        if interrupted:
            logger.info('processing of video stream interrupted.')
            break

    if display != 0:
        cv2.destroyAllWindows()

    return extracted_frames


if __name__ == "__main__":
    # Initializing arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input", required=True, type=str, help="path to unprocessed episode file")
    ap.add_argument("-y", "--display", type=int, default=1, help="whether or not to display output frame to screen")
    ap.add_argument("-d", "--detection_method", type=str, default="cnn",
                    help="skull detection model to use: either 'hog'/'cnn'")
    ap.add_argument("-s", "--sample_period", type=int, default=100,
                    help="milliseconds between each sampled frame, default: 100")
    args = vars(ap.parse_args())

    logger.info('video processing [{}] starts..'.format(args["input"]))
    process_stream(args['input'], args["sample_period"], args["detection_method"], args["display"])
