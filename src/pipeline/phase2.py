import os
import model.azure_face_recognition as afr
from model.vid_recognition import Timestamp
from logger.result_logger import ResultLogger
from tempfile import TemporaryDirectory, NamedTemporaryFile
from logger.base_logger import logger
from utils.gdrivefile_util import GDrive
import shutil


class Phase2:
    def __init__(self, config):
        logger.info('Initializing phase 2 parameters')
        self.config = config
        try:
            self.config['episode_number'] = os.environ['IC_EPISODE_NUMBER']
            self.config['azure_key'] = os.environ['IC_AZURE_KEY_FACE']
            self.config['token_path'] = os.environ['IC_GDRIVE_AUTH_TOKEN_PATH']
            self.config['client_secrets_path'] = os.environ['IC_GDRIVE_CLIENT_SECRETS_PATH']
        except KeyError as ex:
            logger.error('Missing required environment variable')
            raise ex
        # input
        self.config['input_directory_path'] = os.path.join(config['input_directory_path'],
                                                           f'episode{config["episode_number"]}')
        # prepare directory for caching
        self.cache_dir = TemporaryDirectory()
        self.result_cache = os.path.join(self.cache_dir.name, 'results.csv')
        self.config['results_file_path'] = os.path.join(self.config['input_directory_path'], 'results.csv')
        shutil.copy(self.config['results_file_path'], self.result_cache)
        self.result_logger = ResultLogger(self.result_cache)
        # prepare directory for local saving
        if config.getboolean('save_images') or config.getboolean('save_results'):
            self.config['save_cached_files'] = 'True'
            out_dir_path = os.path.join(config['output_directory_path'], f'episode{config["episode_number"]}')
            if not os.path.exists(out_dir_path):
                os.makedirs(out_dir_path, exist_ok=True)
            self.config['output_directory_path'] = out_dir_path
        else:
            self.config['save_cached_files'] = 'False'
        self.gdrive = GDrive(token_path=config['token_path'], client_secrets_path=config['client_secrets_path'])
        if config.getboolean('upload_images') or config.getboolean('upload_results'):
            self.config['upload_cached_files'] = 'True'
        else:
            self.config['upload_cached_files'] = 'False'

    def upload_cached_files(self, upload_labelled=True, upload_results=True):
        dir_path = self.cache_dir.name
        dst_dir = f'episode{self.config["episode_number"]}_output'
        for file in os.listdir(dir_path):
            path = os.path.join(dir_path, file)
            if file == 'results.csv' and upload_results:
                self.gdrive.upload_file(path, remote_filepath=os.path.join(dst_dir, 'phase2_results.csv'))
            elif file.endswith('face.jpg') and upload_labelled:
                self.gdrive.upload_file(path, remote_filepath=os.path.join(dst_dir, file))

    def save_cached_files(self, save_images=True, save_results=True):
        config = self.config
        out_dir_path = config['output_directory_path']
        if not os.path.isdir(out_dir_path):
            raise FileNotFoundError(f'The specified output path is not a directory: {out_dir_path}')
        for file in os.listdir(self.cache_dir.name):
            if (file.endswith('.jpg') and save_images) or (file == 'results.csv' and save_results):
                dst = os.path.join(out_dir_path, file)
                dst = os.path.abspath(dst)
                logger.info(f'Saving {file} to {dst}')
                shutil.move(os.path.join(self.cache_dir.name, file), dst)

    def process_images(self, image_paths):
        fc = afr.authenticate_client(self.config['endpoint'], self.config['azure_key'])
        mappings = {}
        for path in image_paths:
            in_dir_path, filename = os.path.split(path)
            logger.info(f'Processing {filename}')
            faces = afr.recognise_faces(fc, path, self.config['person_group_id'])
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
        in_dir_path = self.config['input_directory_path']
        paths = [os.path.join(in_dir_path, filename) for filename in os.listdir(in_dir_path)]
        return list(filter(lambda x: x.endswith('.jpg') and not x.endswith('_skull.jpg'), paths))

    def run(self):
        try:
            logger.info('Phase 2 start')
            config = self.config
            paths = self.get_imagepaths()
            logger.info('Processing images in input directory')
            up_results = self.process_images(paths)
            logger.info('Updating result CSV file')
            self.update_results(up_results)
            if config['upload_cached_files']:
                up_labelled = config['upload_images']
                up_results = config['upload_results']
                logger.info(f'Uploading cached files: labelled_images={up_labelled}, results={up_results}')
                self.upload_cached_files(upload_labelled=up_labelled, upload_results=up_results)
            if config['save_cached_files']:
                save_labelled = config['save_images']
                save_results = config['save_results']
                logger.info(f'Saving cached files: labelled_images={save_labelled}, results={save_results}')
                self.save_cached_files(save_images=save_labelled, save_results=save_results)
            logger.info('Phase 2 complete')
        except Exception as ex:
            logger.error('Phase 2 failed')
            raise ex


if __name__ == '__main__':
    import configparser
    config = configparser.ConfigParser()
    config.read('../strings.ini')
    p1 = Phase2(config['Phase2'])
    p1.run()