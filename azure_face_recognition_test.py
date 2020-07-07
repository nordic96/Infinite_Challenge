import asyncio
import io
import glob
import os
import sys
import time
import uuid
import requests
import cv2
from urllib.parse import urlparse
from io import BytesIO
from PIL import Image, ImageDraw
import configparser
from azure.cognitiveservices.vision.face import FaceClient
from msrest.authentication import CognitiveServicesCredentials
from azure.cognitiveservices.vision.face.models import TrainingStatusType, Person, SnapshotObjectType, \
    OperationStatusType
from logger.base_logger import logger

# Initialise strings from config file
config = configparser.ConfigParser()
config.read('strings.ini')

ENDPOINT = config['FACE']['endpoint']
KEY = config['FACE']['key']
PERSON_GROUP_ID = 'infinite-challenge-group'
DATASET_DIR = config['MAIN']['path_images']
KNOWN_FACES_DIR = os.path.join(DATASET_DIR, 'known_faces')
UNKNOWN_FACES_DIR = os.path.join(DATASET_DIR, 'unknown_faces')


# Create an authenticated FaceClient.
def authenticate_client():
    logger.info('authenticating azure face client at {}...'.format(ENDPOINT))
    fc = FaceClient(ENDPOINT, CognitiveServicesCredentials(KEY))
    return fc


def init_person_group(fc):
    train_req = 1
    person_group_list = fc.person_group.list()
    if len(person_group_list) == 0:
        logger.info('Person Group ID {} does not exist, creating a new one in azure...'.format(PERSON_GROUP_ID))
        fc.person_group.create(person_group_id=PERSON_GROUP_ID, name=PERSON_GROUP_ID)
    else:
        logger.info('Person Group initialized for {}. Proceeding with person object creation..'.format(PERSON_GROUP_ID))

    person_group_list = fc.person_group.list()
    if len(person_group_list) != 0:
        train_required = 0
        logger.info(person_group_list)
        logger.info('people objects are already added. Skipping creation...')

    else:
        for member in os.listdir(KNOWN_FACES_DIR):
            logger.info('Creating person object in azure: ' + member)
            member_obj = fc.person_group_person.create(PERSON_GROUP_ID, member)

            member_path = os.path.join(KNOWN_FACES_DIR, member)
            member_images = [file for file in glob.glob('{}/*.*'.format(member_path))]
            count = 0
            for member_image in member_images:
                ch = open(member_image, 'r+b')
                try:
                    face_client.person_group_person.add_face_from_stream(PERSON_GROUP_ID, member_obj.person_id, ch)
                except Exception as ex:
                    logger.info(ex)
                    continue
                count += 1
            logger.info('Member {} total {} images.. added in person group'.format(member, count))
    return train_required


def train(fc):
    logger.info('Training the person group...')
    # Train the person group
    fc.person_group.train(PERSON_GROUP_ID)

    while True:
        training_status = fc.person_group.get_training_status(PERSON_GROUP_ID)
        logger.info("Training status: {}.".format(training_status.status))
        if training_status.status is TrainingStatusType.succeeded:
            break
        elif training_status.status is TrainingStatusType.failed:
            sys.exit('Training the person group has failed.')
        time.sleep(5)


def get_name_by_id(fc, person_id):
    person = fc.person_group_person.get(PERSON_GROUP_ID, person_id)
    return person.name


def detect_faces(fc, img_path_dir):
    """
    Identify a face against a defined PersonGroup
    """
    test_image_array = [file for file in glob.glob('{}/*.*'.format(img_path_dir))]
    for image_path in test_image_array:
        try:
            image = open(image_path, 'r+b')
            # Detect faces
            face_ids = []
            faces = fc.face.detect_with_stream(image)
            if len(faces) == 0:
                raise Exception('No faces detected for {}. Skipping...'.format(image_path))
            for face in faces:
                face_ids.append(face.face_id)

            # Identify faces
            results = fc.face.identify(face_ids, PERSON_GROUP_ID)
        except Exception as ex:
            logger.info(ex)
            continue

        logger.info('Identifying faces in {}'.format(os.path.basename(image.name)))
        if not results:
            logger.info('No person identified in the person group for faces from {}.'.format(os.path.basename(image.name)))
        for person in results:
            logger.info('Person for face ID {} is identified in {} with a confidence of {}: {}.'.format(
                person.face_id,
                os.path.basename(image.name),
                person.candidates[0].confidence,
                get_name_by_id(fc, person.candidates[0].person_id)
            ))


if __name__ == '__main__':
    face_client = authenticate_client()
    # Create empty Person Group. Person Group ID must be lower case, alphanumeric, and/or with '-', '_'.
    # face_client.person_group.delete(PERSON_GROUP_ID)

    training_required = init_person_group(face_client)
    if training_required:
        logger.info('Training required. Proceed to training...')
        train(face_client)

    detect_faces(face_client, UNKNOWN_FACES_DIR)


