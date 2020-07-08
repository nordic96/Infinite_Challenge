import glob
import os
import sys
import time
from PIL import Image, ImageDraw
from azure.cognitiveservices.vision.face import FaceClient
from msrest.authentication import CognitiveServicesCredentials
from azure.cognitiveservices.vision.face.models import TrainingStatusType, Person, SnapshotObjectType, \
    OperationStatusType
from logger.base_logger import logger

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

    return (left, top), (right, bottom)


def recognise_faces(fc, img_dir_path, person_group_id, unknown_faces_dir, label_and_save=False):
    """
    Identify a face against a defined PersonGroup
    """
    logger.info(f'Preparing images in {img_dir_path} ...')
    test_image_array = [file for file in glob.glob('{}/*.*'.format(img_dir_path))]
    no_files = len(test_image_array)
    no_skips = 0
    no_fails = 0
    result_dict = {}

    for image_path in test_image_array:
        basename = os.path.basename(image_path)
        logger.info(f'Processing {image_path}...')
        faces_coord_dict = {}
        draw = None
        labelled_image = None
        try:
            image = open(image_path, 'r+b')
            # Detect faces
            face_ids = []
            logger.info(f'Detecting faces using Azure Face Client...')
            detected_faces = fc.face.detect_with_stream(image)
            if len(detected_faces) == 0:
                no_skips += 1
                logger.info('No faces detected.')
                continue
            logger.info(f'Detected {len(detected_faces)} faces.')
            # Store bounds of detected faces in mapping of face-id to rectangle (pair of points) of detected faces
            for face in detected_faces:
                face_ids.append(face.face_id)
                faces_coord_dict[face.face_id] = getRectangle(face)
                # logger.info('Face ID: {}, coordinates: {}'.format(face.face_id, getRectangle(face)))
            # Identify faces
            logger.info('Identifying faces using Azure Face Client...')
            results = fc.face.identify(face_ids, person_group_id=person_group_id)
            if results is None:
                logger.info('No faces were identified in {}.'.format(basename))
                continue
        except BaseException as ex:
            logger.warning(f'Error occurred while processing {basename}: {ex.__class__.__name__}')
            no_fails += 1
            raise ex

        if label_and_save:
            labelled_image = Image.open(image_path)
            draw = ImageDraw.Draw(labelled_image)

        person_detected_arr = []
        person_coord_arr = []
        for person in results:
            try:
                detected_name = get_name_by_id(fc, person.candidates[0].person_id, person_group_id)
                logger.info('{} is identified in {} {}, with a confidence of {}'.format(
                    detected_name,
                    basename,
                    faces_coord_dict[person.face_id],
                    person.candidates[0].confidence,
                ))
            except IndexError:
                detected_name = 'unknown'
                logger.warning('Unable to identify a face [face_id = {}] which was detected in {}: No candidates found.'.format(person.face_id, basename))

            person_detected_arr.append(detected_name)
            person_coord_arr.append(faces_coord_dict[person.face_id])

            if label_and_save:
                draw.rectangle(faces_coord_dict[person.face_id], outline='red')
                labelled_image.save(os.path.join(unknown_faces_dir, '{}_output.png'.format(detected_name)))

        result_dict[os.path.basename(basename)] = (person_detected_arr, person_coord_arr)

    logger.info('Result: Total {} images, {} skipped images, {} processing failed...'.format(no_files, no_skips, no_fails))
    # Returns the face & coord dict
    return result_dict


if __name__ == '__main__':
    # from configparser import ConfigParser
    # config = ConfigParser()
    # config.read('strings.ini')
    # person_group_id = config['FACE']['person_group_id']
    # endpoint = config['FACE']['endpoint']
    # unknown_faces_dir = config['FACE']['unknown_faces_dir']
    # known_faces_dir = config['FACE']['known_faces_dir']
    # key = os.environ['IC_AZURE_KEY_FACE']
    #
    #
    # face_client = authenticate_client(endpoint, key)
    # # Create empty Person Group. Person Group ID must be lower case, alphanumeric, and/or with '-', '_'.
    # face_client.person_group.delete(person_group_id)
    #
    # training_required = init_person_group(face_client, person_group_id, known_faces_dir)
    # if training_required:
    #     logger.info('Training required. Proceed to training...')
    #     train(face_client, person_group_id)
    #
    # # path of directory containing images to use the model on
    # test_image_path_dir = ""
    #
    # results = recognise_faces(face_client, person_group_id, test_image_path_dir, unknown_faces_dir)
    # logger.info(results)
    exit(0)

