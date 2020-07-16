import os
import sys
import shutil
import configparser
from tempfile import TemporaryDirectory
from src.model import azure_face_recognition as afr
from src.model.vid_recognition import Timestamp
from src.logger.result_logger import ResultLogger
from src.logger.base_logger import logger
from src.utils.gdrivefile_util import GDrive


class Phase2:
    def __init__(self, config, episode_number):
        logger.info('Initializing phase 2 parameters')
        self.episode_number = episode_number
        # input
        self.input_directory_path = os.path.join(config['input_directory_path'],  f'episode{episode_number}')
        # prepare directory for caching
        self.cache_dir = TemporaryDirectory()
        self.result_cache = os.path.join(self.cache_dir.name, 'results.csv')
        results_file_path = os.path.join(self.input_directory_path, 'results.csv')
        shutil.copy(results_file_path, self.result_cache)
        self.result_logger = ResultLogger(self.result_cache)
        # prepare directory for local saving
        self.save_images = config.getboolean('save_images')
        self.save_results = config.getboolean('save_results')
        if self.save_images or self.save_results:
            out_dir_path = os.path.join(config['output_directory_path'], f'episode{self.episode_number}')
            if not os.path.exists(out_dir_path):
                os.makedirs(out_dir_path, exist_ok=True)
            self.output_directory_path = out_dir_path
        # for uploading cached files
        self.upload_labelled = config.getboolean('upload_labelled')
        self.upload_results = config.getboolean('upload_results')
        # for google drive
        self.gdrive = GDrive(token_path=os.environ['IC_GDRIVE_AUTH_TOKEN_PATH'],
                             client_secrets_path=os.environ['IC_GDRIVE_CLIENT_SECRETS_PATH'])
        # for face recognition
        self.person_group_id = config['person_group_id']
        self.faceclient = afr.authenticate_client(config['endpoint'], os.environ['IC_AZURE_KEY_FACE'])

    def upload_cached_files(self):
        dir_path = self.cache_dir.name
        dst_dir = f'episode{self.episode_number}_output'
        for file in os.listdir(dir_path):
            path = os.path.join(dir_path, file)
            if file == 'results.csv' and self.upload_results:
                self.gdrive.upload_file(path, remote_filepath=os.path.join(dst_dir, 'phase2_results.csv'))
            elif file.endswith('face.jpg') and self.upload_labelled:
                self.gdrive.upload_file(path, remote_filepath=os.path.join(dst_dir, file))

    def save_cached_files(self):
        out_dir_path = self.output_directory_path
        if not os.path.isdir(out_dir_path):
            raise FileNotFoundError(f'The specified output path is not a directory: {out_dir_path}')
        for file in os.listdir(self.cache_dir.name):
            if (file.endswith('.jpg') and self.save_images) or (file == 'results.csv' and self.save_results):
                dst = os.path.join(out_dir_path, file)
                dst = os.path.abspath(dst)
                logger.info(f'Saving {file} to {dst}')
                shutil.move(os.path.join(self.cache_dir.name, file), dst)

    def process_images(self, image_paths):
        mappings = {}
        for path in image_paths:
            in_dir_path, filename = os.path.split(path)
            logger.info(f'Processing {filename}')
            faces = afr.recognise_faces(self.faceclient, path, self.person_group_id)
            mappings[filename] = faces
            logger.info(f'Caching labelled images')
            name, ext = filename.split('.')
            face_labelled_image_path = os.path.join(self.cache_dir.name, f'{name}_face.{ext}')
            skull_labelled_image_path = os.path.join(in_dir_path, f'{name}_skull.{ext}')
            # overlay face labels over skull labels from previous phase
            afr.label_image(faces, skull_labelled_image_path, face_labelled_image_path)
        return mappings

    def update_results(self, mappings):
        for filename in mappings:
            faces = mappings[filename]
            bounding_boxes = []
            names = []
            for face in faces:
                names.append(face['name'])
                bounding_boxes.append(face['bounding_box'])
            entry_id = filename.split('.')[0]
            ep, h, m, s, ms = entry_id.split('_')
            self.result_logger.update_face_entry(ep, Timestamp(h, m, s, ms), bounding_boxes, names)

    def get_imagepaths(self):
        in_dir_path = self.input_directory_path
        paths = [os.path.join(in_dir_path, filename) for filename in os.listdir(in_dir_path)]
        return list(filter(lambda x: x.endswith('.jpg') and not x.endswith('_skull.jpg'), paths))

    def run(self):
        try:
            logger.info('Phase 2 start')
            paths = self.get_imagepaths()
            logger.info('Processing images in input directory')
            results = self.process_images(paths)
            logger.info('Updating result CSV file')
            self.update_results(results)
            self.upload_cached_files()
            self.save_cached_files()
            logger.info('Phase 2 complete')
        except Exception as ex:
            logger.error('Phase 2 failed')
            raise ex


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read(sys.argv[2])
    p1 = Phase2(config['Phase2'], sys.argv[3])
    p1.run()
