import face_recognition
import os
import cv2
import imutils
from infinitechallenge.logging import base_logger


class ProcessedImage:
    def __init__(self, image, episode_number, timestamp, name, coordinate):
        self.image = image
        self.episode_number = episode_number
        self.timestamp = timestamp
        self.name = name
        self.coordinate = coordinate


def get_metadata(filename):
    # get base file name
    basename = os.path.basename(filename)
    # strip file extension
    ep_and_timestamp = basename.split('.')[0]
    # strip non-digits
    ep, h, m, s, ms = ep_and_timestamp.split('_')
    timestamp = "{}:{}:{}:{}".format(h, m, s, ms)
    return ep, timestamp


# fetch an unprocessed image
def fetch_unprocessed_img(img_path):
    ep, timestamp = get_metadata(img_path)
    img = cv2.imread(img_path)
    return ep, timestamp, img


# matches unknown encodings (encoding) with known encodings in data
def process_recognition(data, encodings):
    names = []
    # Recognition and Comparing faces in the database
    for encoding in encodings:
        # attempt to match each face in the input image to our known encodings
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


def locate_faces(image, detection_method):
    base_logger.logger.info("Resizing face...")

    # convert to rgb
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    # resize
    rgb = imutils.resize(rgb, width=280)

    # resize factor
    r = image.shape[1] / float(rgb.shape[1])

    # Detecting the coordinates of the bounding boxes corresponding to each face in the input image
    # then compute the facial embeddings for each face
    base_logger.logger.info("Recognizing faces...")
    resized_boxes = face_recognition.face_locations(rgb, model=detection_method)
    encodings_of_detected_faces = face_recognition.face_encodings(rgb, resized_boxes)
    boxes = []
    for (a, b, c, d) in resized_boxes:
        a = int(a * r)
        b = int(b * r)
        c = int(c * r)
        d = int(d * r)
        boxes.append((a, b, c, d))
    return boxes, encodings_of_detected_faces


def label_image(image, title, boxes, names):
    # display
    labelled = image.copy()
    for ((top, right, bottom, left), name) in zip(boxes, names):
        cv2.rectangle(labelled, (left, top), (right, bottom), (0, 255, 0), 2)
        y = top - 15 if top - 15 > 15 else top + 15
        cv2.putText(labelled, name, (left, y), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)

    cv2.putText(labelled, title, (5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)
    return labelled


def display_results(processed_image):
    labelled = label_image(
        processed_image.image,
        "ep:{} {}".format(processed_image.episode_number, processed_image.timestamp),
        processed_image.coordinate,
        processed_image.name
    )
    cv2.imshow("Recognize faces", labelled)
    cv2.waitKey(1000)
    pass


def process_image(image_path, known_face_encoding_data, detection_method, display=False):
    episode_number, timestamp, image = fetch_unprocessed_img(image_path)
    boxes, encodings = locate_faces(image, detection_method)
    names = process_recognition(known_face_encoding_data, encodings)
    processed = ProcessedImage(image, episode_number, timestamp, names, boxes)
    if display:
        display_results(processed)
        cv2.destroyAllWindows()

    return processed


if __name__ == "__main__":
    import argparse
    import pickle
    # Initialize arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-e", "--encodings", required=True, help="path to serialized db of facial encodings")
    ap.add_argument("-y", "--display", type=int, default=1, help="whether or not to display output frame to screen")
    ap.add_argument("-i", "--image", required=True, help="path to input image for recognition <ep_num>_<hr>_<min>_<sec>_<ms>.jpg")
    ap.add_argument("-d", "--detection-method", type=str, default="cnn")
    args = vars(ap.parse_args())

    base_logger.logger.info('loading encodings...')
    data = pickle.loads(open(args["encodings"], "rb").read())
    
    base_logger.logger.info('processing image...')
    process_image(args['image'], data, args["detection_method"], args['display'])
