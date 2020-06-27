import face_recognition
import argparse
import pickle
import cv2
from logger import base_logger

def process_recognition(names, data, encodings):
    # Recognition and Comparing faces in the database
    for encoding in encodings:
        #attempt to match each face in the input image to our known encodings
        matches = face_recognition.compare_faces(data["encodings"], encoding)
        name = "Unknown"

        if True in matches:
            matchedIdxs = [i for (i, b) in enumerate(matches) if b]
            counts = {}

            for i in matchedIdxs:
                name = data["names"][i]
                counts[name] = counts.get(name, 0) + 1

            name = max(counts, key=counts.get)
        names.append(name)
    return names

if __name__ == "__main__":
    # Initialize arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-e", "--encodings", required=True, help="path to serialized db of facial encodings")
    ap.add_argument("-i", "--image", required=True, help="path to input image for recognition")
    ap.add_argument("-d", "--detection-method", type=str, default="cnn")
    args = vars(ap.parse_args())

    base_logger.logger.info('loading encodings...')
    data = pickle.loads(open(args["encodings"], "rb").read())

    # loading the image that we want for recognition
    image = cv2.imread(args["image"])
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # Detecting the coordinatesof the bounding boxes corresponding to each face in the input image
    # then compute the facial embeddings for each face
    base_logger.logger.info("recognizing faces... for {}".format(args["image"]))
    boxes = face_recognition.face_locations(
        rgb,
        model=args["detection_method"]
    )
    encodings = face_recognition.face_encodings(rgb, boxes)

    # Initializing the list of names for each face detected
    # Recognition and Comparing faces in the database
    names = []
    names = process_recognition(names, data, encodings)

    for ((top, right, bottom, left), name) in zip(boxes, names):
        cv2.rectangle(image, (left, top), (right, bottom), (0, 255, 0), 2)
        y = top - 15 if top - 15 > 15 else top + 15
        cv2.putText(image, name, (left, y), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)

    #cv2.imshow("Image", image)
    cv2.imwrite("../test/img_output.jpg", image)
    #cv2.waitKey(0)