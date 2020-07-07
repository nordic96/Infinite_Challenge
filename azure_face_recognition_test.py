import asyncio
import io
import glob
import os
import sys
import time
import uuid
import requests
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
KNOWN_FACES_DIR = os.path.join(config['MAIN']['path_images'], 'known_faces')


# Create an authenticated FaceClient.
def authenticate_client():
    logger.info('authenticating azure face client at {}...'.format(ENDPOINT))
    fc = FaceClient(ENDPOINT, CognitiveServicesCredentials(KEY))
    return fc


def init_person_group(fc):
    person_group_list = fc.person_group.list()
    if len(person_group_list) == 0:
        logger.info('Person Group ID {} does not exist, creating a new one in azure...'.format(PERSON_GROUP_ID))
        fc.person_group.create(person_group_id=PERSON_GROUP_ID, name=PERSON_GROUP_ID)

    for member in os.listdir(KNOWN_FACES_DIR):
        logger.info('Creating person object in azure: ' + member)
        member_obj = fc.person_group_person.create(PERSON_GROUP_ID, member)

        member_path = os.path.join(KNOWN_FACES_DIR, member)
        for img in os.listdir(member_path):
            member_img_path = os.path.join(member_path, img)
            try:
                ch = open(member_img_path, 'r+b')
                detected_face = face_client.face.detect_with_stream(ch)
                if not detected_face:
                    raise Exception('No face detected from image {}, skipping...'.format(member_img_path))
                else:
                    logger.info('adding face image: ' + member_img_path)
                    fc.person_group_person.add_face_from_stream(PERSON_GROUP_ID, member_obj.person_id, ch)
            except Exception as ex:
                logger.info('Exception: ' + ex)
                continue


if __name__ == '__main__':
    face_client = authenticate_client()
    # Create empty Person Group. Person Group ID must be lower case, alphanumeric, and/or with '-', '_'.
    face_client.person_group.delete(PERSON_GROUP_ID)
    init_person_group(face_client)


