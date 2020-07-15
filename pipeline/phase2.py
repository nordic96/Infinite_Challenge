import os
import model.azure_face_recognition as afr
from model.vid_recognition import Timestamp
from logger.result_logger import ResultLogger
from tempfile import TemporaryDirectory, NamedTemporaryFile
from logger.base_logger import logger
from utils.gdrivefile_util import GDrive


class Phase2:
    def __init__(self, config):
        logger.info('initializing phase2 parameters')
        self.config = config
        try:
            self.config['azure_key'] = os.environ['IC_AZURE_KEY_FACE']
            self.config['token_path'] = os.environ['IC_GDRIVE_AUTH_TOKEN_PATH']
            self.config['client_secrets_path'] = os.environ['IC_GDRIVE_CLIENT_SECRETS_PATH']
        except KeyError as ex:
            logger.error('Missing required environment variable')
            raise ex

        self.cache_dir = None
        self.result_cache = None
        out_dir_path = self.config['output_directory_path']
        if not os.path.exists(out_dir_path):
            logger.warning(f'Output directory path does not exist, making directories')
            os.makedirs(out_dir_path, exist_ok=True)
        if not os.path.isdir(out_dir_path):
            self.cache_dir = TemporaryDirectory()
            self.config['output_directory_path'] = self.cache_dir.name
            logger.warning(f'Specified path is not a directory, output files will be cached at {self.cache_dir.name}')
        result_file_path = self.config['result_file_path']
        if not os.path.exists(result_file_path):
            with open(result_file_path, 'w') as f:
                f.write('')
        if not os.path.isfile(result_file_path):
            self.result_cache = NamedTemporaryFile()
            self.config['result_file_path'] = self.result_cache.name

        self.result_logger = ResultLogger(self.config['result_file_path'])
        self.gdrive = GDrive(token_path=self.config['token_path'],
                             client_secrets_path=self.config['client_secrets_path'])

    def upload_output_files(self, upload_images=True):
        dir_path = self.config['output_directory_path']
        for file in os.listdir(dir_path):
            if file.endswith('mp4') or (file.endswith('.jpg') and upload_images is False):
                continue
            self.gdrive.upload_file(os.path.join(dir_path, file), folder_name="Test")
        self.gdrive.upload_file(self.config['result_file_path'], folder_name="Test", file_name='phase2_results.csv')

    def process_images(self):
        fc = afr.authenticate_client(self.config['endpoint'], self.config['azure_key'])
        mappings = afr.recognise_faces(fc,
                                       self.config['input_directory_path'],
                                       self.config['person_group_id'],
                                       self.config['output_directory_path'],
                                       label_and_save=self.config['label_and_save'] == 'True')
        return mappings

    def update_results(self, mappings):
        for filename in mappings:
            names, faces = mappings[filename]
            entry_id = filename.split('.')[0]
            ep, h, m, s, ms = entry_id.split('_')
            self.result_logger.update_face_entry(
                ep,
                Timestamp(h, m, s, ms),
                faces,
                names
            )

    def run(self):
        try:
            filename_to_names_and_faces_mappings = self.process_images()
            self.update_results(filename_to_names_and_faces_mappings)
            self.upload_output_files(upload_images=False)
        except Exception as ex:
            logger.error('Phase 2 failed')
            raise ex


if __name__ == '__main__':
    import configparser
    config = configparser.ConfigParser()
    config.read('../strings.ini')
    p1 = Phase2(config['Phase2'])
    p1.run()