import glob
import os
import sys
import time
from infinitechallenge.utils import label_image as label_image_util
from azure.cognitiveservices.vision.face import FaceClient
from msrest.authentication import CognitiveServicesCredentials
from azure.cognitiveservices.vision.face.models import TrainingStatusType, Person, SnapshotObjectType, \
    OperationStatusType, APIError, APIErrorException
from infinitechallenge.logging import logger

# Use recognise_face() to handle Phase 2
# frame_detection will no longer be needed, but keep it as backup
# Date: 7 Jul 2020
# Ko Gi Hun

# Initialise strings from config file


# Create an authenticated FaceClient.
def authenticate_client(endpoint, key):
    logger.info('Authenticating Azure Face Client at {}...'.format(endpoint))
    fc = FaceClient(endpoint, CognitiveServicesCredentials(key))
    return fc


def init_person_group(fc, person_group_id, known_faces_dir):
    train_required = 1
    person_group_list = fc.person_group.list()
    if len(person_group_list) == 0:
        logger.info('Person Group ID {} does not exist, creating a new one in azure...'.format(person_group_id))
        fc.person_group.create(person_group_id=person_group_id, name=person_group_id)
    else:
        logger.info('Person Group initialized for {}. Proceeding with person object creation..'.format(person_group_id))

    person_group_list = fc.person_group.list()
    if len(person_group_list) != 0:
        train_required = 0
        logger.info(person_group_list)
        logger.info('people objects are already added. Skipping creation...')

    else:
        for member in os.listdir(known_faces_dir):
            logger.info('Creating person object in azure: ' + member)
            member_obj = fc.person_group_person.create(person_group_id, member)

            member_path = os.path.join(known_faces_dir, member)
            member_images = [file for file in glob.glob('{}/*.*'.format(member_path))]
            count = 0
            for member_image in member_images:
                ch = open(member_image, 'r+b')
                try:
                    fc.person_group_person.add_face_from_stream(person_group_id, member_obj.person_id, ch)
                except Exception as ex:
                    logger.info(ex)
                    continue
                count += 1
            logger.info('Member {} total {} images.. added in person group'.format(member, count))
    return train_required


def train(fc, person_group_id):
    logger.info('Training the person group...')
    # Train the person group
    fc.person_group.train(person_group_id)

    while True:
        training_status = fc.person_group.get_training_status(person_group_id)
        logger.info("Training status: {}.".format(training_status.status))
        if training_status.status is TrainingStatusType.succeeded:
            break
        elif training_status.status is TrainingStatusType.failed:
            sys.exit('Training the person group has failed.')
        time.sleep(5)


def get_name_by_id(fc, person_id, person_group_id):
    person = fc.person_group_person.get(person_group_id, person_id)
    return person.name


# Convert width height to a point in a rectangle
def getRectangle(face_dictionary):
    rect = face_dictionary.face_rectangle
    left = rect.left
    top = rect.top
    right = left + rect.width
    bottom = top + rect.height
    return (top, right, bottom, left)


def recognise_faces(fc, image_path, person_group_id):
    """ Recognize faces in an image

    :param fc: FaceClient
    :param image_path: path to image to recognize faces in
    :param person_group_id: the id of the trained person group
    :return: results of detect and identify
    """
    data = open(image_path, 'rb')
    face_ids = []
    faces = {}

    logger.info(f'Detecting faces using Azure Face Client...')
    detect_results = fc.face.detect_with_stream(data)
    for face in detect_results:
        rect = face.face_rectangle
        l = rect.left
        t = rect.top
        r = l + rect.width
        b = t + rect.height
        bounding_box = (t, r, b, l)
        id = face.face_id
        face_ids.append(id)
        faces[id] = {'bounding_box': bounding_box}
    if not faces:
        logger.info(f'No faces to identify')
        return faces

    logger.info(f'Identifying faces using Azure Face Client...')
    identify_results = fc.face.identify(face_ids, person_group_id=person_group_id)
    for person in identify_results:
        name = 'unknown'
        face_id = person.face_id
        logger.info(f'person: {person}')
        try:
            # get the highest probability person_id
            person_id = person.candidates[0].person_id
            name = get_name_by_id(fc, person_id, person_group_id)
            logger.info(f'{name} was identified at {faces[face_id]["bounding_box"]}')
        except IndexError:
            logger.info(f'Unable to recognize face at {faces[face_id]["bounding_box"]}.')
        faces[face_id]['name'] = name
    return [faces[id] for id in faces]


def label_image(faces, image_path, output_path):
    label_list = [(face['name'], face['bounding_box'], 'green') for face in faces]
    label_image_util(image_path, output_path, label_list)


def recognise_faces_many(fc, img_dir_path, person_group_id, out_dir_path, label_and_save=False):
    """
    Identify a face against a defined PersonGroup for all images in a specified directory
    """
    logger.info(f'Preparing images in {img_dir_path} ...')
    test_image_array = [file for file in glob.glob('{}/*.*'.format(img_dir_path))]
    no_files = len(test_image_array)
    no_fails = 0
    result_dict = {}

    for image_path in test_image_array:
        if not image_path.endswith('.jpg'):
            continue
        basename = os.path.basename(image_path)
        logger.info(f'Processing {image_path}...')
        try:
            faces = recognise_faces(fc, image_path, person_group_id)
            if label_and_save:
                label_image(faces, image_path,os.path.join(out_dir_path, basename))
            result_dict[os.path.basename(basename)] = faces
        except (APIErrorException, APIError) as ex:
            logger.error(f'Failed to process {basename}', ex)
            no_fails += 1
    logger.info('Result: Total {} images, {} processing failed...'.format(no_files, no_fails))
    # Returns the face & coord dict
    return result_dict
