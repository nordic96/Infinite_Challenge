from utils.csv_logger import CsvLogger
from model import frame_recognition as fr
from logger.base_logger import logger
import face_recognition
import argparse
import pickle
import cv2
import os
import imutils

ap = argparse.ArgumentParser()
ap.add_argument("-e", "--encodings", required=True, help="path to serialized db of facial encodings")
ap.add_argument("-i", "--input", required=True, help="input directory for recognition process")
ap.add_argument("-d", "--detection-method", type=str, default="cnn")
args = vars(ap.parse_args())

if __name__ == "__main__":
    # 1. Retrieve list of file paths in dir for recognition
    img_files = os.listdir(args["input"])
    # 2. Load the encodings
    logger.info('loading the encoding file: {}'.format(args["encodings"]))
    data = pickle.loads(open(args["encodings"], "rb").read())

    for img_fname in img_files:

        img_path = os.path.join(args["input"], img_fname)
        logger.info("processing {}".format(img_path))

        image = cv2.imread(img_path)
        #image = imutils.resize(image, width=500)
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Detecting the coordinatesof the bounding boxes corresponding to each face in the input image
        # then compute the facial embeddings for each face
        boxes = face_recognition.face_locations(
            rgb,
            model=args["detection_method"]
        )
        encodings = face_recognition.face_encodings(rgb, boxes)
        # Initializing the list of names for each face detected
        # Recognition and Comparing faces in the database
        names = []
        names = fr.process_recognition(names, data, encodings)
        logger.info("detected known faces: {}".format(names))