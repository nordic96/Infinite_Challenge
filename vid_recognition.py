
from imutils.video import VideoStream
import face_recognition
import argparse
import imutils
import pickle
import time
import cv2
from logger.base_logger import logger
import frame_recognition as fr

# Description: Facial Recognition with video stream input
# Developed Date: 25 June 2020

# Initializing arguments
ap = argparse.ArgumentParser()
ap.add_argument("-e", "--encodings", required=True, help="path to serialized db of facial encodings")
ap.add_argument("-o", "--output", type=str, help="path to output video")
ap.add_argument("-y", "--display", type=int, default=1, help="whether or not to display output frame to screen")
ap.add_argument("-d", "--detection_method", type=str, default="cnn", help="face detection model to use: either 'hog'/'cnn'")
args = vars(ap.parse_args())

if __name__ == "__main__":
    logger.info('loading encodings')
    data = pickle.loads(open(args["encodings"], "rb").read())

    #Initializing video stream
    vs = VideoStream(src='test/test.mp4').start()
    writer = None
    time.sleep(2.0)

    logger.info('video processing starts..')
    while True:
        frame = vs.read()

        # Frame conversion
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb = imutils.resize(frame, width = 750)
        r = frame.shape[1] / float(rgb.shape[1])

        #Detection
        boxes = face_recognition.face_locations(rgb, model=args["detection_method"])
        encodings = face_recognition.face_encodings(rgb, boxes)
        names = []
        names = fr.process_recognition(names, data, encodings)

        for((top, right, bottom, left), name) in zip(boxes, names):
            top = int(top * r)
            right = int(right * r)
            bottom = int(bottom * r)
            left = int(left * r)

            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            y = top - 15 if top - 15 > 15 else top + 15
            cv2.putText(frame, name, (left, y), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)

        if writer is None and args["output"] is not None:
            fourcc = cv2.VideoWriter_fourcc(*"MJPG")
            writer = cv2.VideoWriter(args["output"], fourcc, 20, (frame.shape[1], frame.shape[0]), True)

        if writer is not None:
            writer.write(frame)

        if args["display"] > 0:
            cv2.imshow("Frame", frame)
            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break
    cv2.destroyAllWindows()
    vs.stop()
    logger.info('Stopped video writing..')
    if writer is not None:
        writer.release()