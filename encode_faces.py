from imutils import paths
import face_recognition
import argparse
import pickle
import cv2
import os
from logger.base_logger import logger

#ENCODING FACES
#Developed: 24 June 2020
#Developer: Ko Gi Hun

#Initializing arg parser
ap = argparse.ArgumentParser()
ap.add_argument("-i", "--dataset", required=True, help = "path to input directory of faces + images")
ap.add_argument("-e", "--encodings", required=True, help = "path to serialized db of facial encodings")
ap.add_argument("-d", "--detection-method", type=str, default="cnn",
                help = "face detection model to use: either 'hog' or 'cnn'")
args = vars(ap.parse_args())

if __name__ == "__main__":
    logger.info('quantifying faces..')
    imagePaths = list(paths.list_images(args["dataset"]))

    #Initializing the list of known encodings and known names
    knownEncodings = []
    knownNames = []

    #Looping through the dataset images for encoding
    for (i, imagePath) in enumerate(imagePaths):
        name = imagePath.split(os.path.sep)[-2]
        logger.info("Processing image of {} {}: {}/{}".format(name, imagePath, i + 1, len(imagePaths)))

        #loading the image and convert it from BGR (Opencv ordering)
        #To dlib ordering(RGB)
        image = cv2.imread(imagePath)
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        #1. Detect the (x, y) coordinates of the bounding boxes
        #corresponding to each face in the input image
        boxes = face_recognition.face_locations(rgb, model = args["detection_method"])

        #2. Compute the facial embedding for the face
        encodings = face_recognition.face_encodings(rgb, boxes)

        #3. Loop over the encodings
        for encoding in encodings:
            # Add encoding + name to our set of known names and encodings
            knownEncodings.append(encoding)
            knownNames.append(name)

    # Serialization of encodings into file and save
    logger.info("serializing encodings...")
    data = {"encodings": knownEncodings, "names": knownNames}
    f = open(args["encodings"], "wb")
    f.write(pickle.dumps(data))
    f.close()