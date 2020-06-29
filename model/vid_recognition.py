import os.path
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import face_recognition
import argparse
import imutils
import pickle
import cv2
from model import frame_recognition as fr
from logger.base_logger import logger

# Description: Facial Recognition with video stream input
# Developed Date: 25 June 2020
# Last Modified: 29 June 2020

# Initializing arguments
ap = argparse.ArgumentParser()
ap.add_argument("-e", "--encodings", required=True, help="path to serialized db of facial encodings")
ap.add_argument("-i", "--input", required=True, help="path to the input stream video file")
ap.add_argument("-o", "--output", type=str, help="path to output video")
ap.add_argument("-y", "--display", type=int, default=1, help="whether or not to display output frame to screen")
ap.add_argument("-d", "--detection_method", type=str, default="cnn", help="face detection model to use: either 'hog'/'cnn'")
ap.add_argument("-s", "--sample_period", type=int, default=100, help="milliseconds between each sampled frame, default: 100")
args = vars(ap.parse_args())


class ExtractedFrame:
    def __init__(self, frame, frame_number, timestamp, coord):
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


# returns relevant frames and data (coordinates)
def process_stream(video_stream, sample_period, detection_method):
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
            extracted_frames.append(ExtractedFrame(frame, frame_number, timestamp, skull_coords))

        logger.info('sampled_frame: {} | timestamp: {} | skulls detected: {}'.format(frame_number, timestamp, skull_coords))

        for (top, right, bottom, left) in skull_coords:
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            y = top - 15 if top - 15 > 15 else top + 15
            cv2.putText(frame, "skull", (left, y), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)

        cv2.putText(frame, timestamp, (5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)
        #if args["display"] > 0:
        cv2.imshow("Frame", frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

    cv2.destroyAllWindows()
    return extracted_frames


if __name__ == "__main__":
    logger.info('loading encodings')
    data = pickle.loads(open(args["encodings"], "rb").read())

    #Initializing video stream
    logger.info('initializing video stream...')
    vs = cv2.VideoCapture(args["input"])
    logger.info('video processing [{}] starts..'.format(args["input"]))
    process_stream(vs, args["sample_period"], data, args["detection_method"])
