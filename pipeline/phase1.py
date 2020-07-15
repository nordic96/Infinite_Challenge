import os
import cv2
from logger.result_logger import ResultLogger
from tempfile import TemporaryDirectory, NamedTemporaryFile
from logger.base_logger import logger
from model import vid_recognition as vr
from utils.gdrivefile_util import GDrive


# 1. process a single video using model
# 2. cache images with skulls
# 3. update result.csv for each image
class Phase1:
    def __init__(self, config):
        logger.info('initializing phase1 parameters')
        self.config = config

        try:
            self.config['episode_number'] = os.environ['IC_EPISODE_NUMBER']
            self.config['azure_key'] = os.environ['IC_AZURE_KEY_SKULL']
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

    def download_episode(self):
        config = self.config
        episode_filename = f'episode{config["episode_number"]}.mp4'
        cached_video_path = os.path.join(config["output_directory_path"], episode_filename)
        self.gdrive.download_file(episode_filename, cached_video_path)
        return cached_video_path

    def process_episode(self, episode_filepath):
        config = self.config
        extracted_frames = vr.process_stream(
            video_path=episode_filepath,
            azure_key=config['azure_key'],
            confidence=float(config['skull_confidence_threshold']),
            model_version=config['skull_model_version'],
            sample_rate=int(config['video_sample_rate']),
            display=config['display'] == 'True'
        )
        return extracted_frames

    def save_extracted_frames(self, extracted_frames):
        config = self.config
        for frame in extracted_frames:
            filename = f"{config['episode_number']}_{frame.timestamp.with_delimiter('_')}.jpg"
            dst_path = os.path.join(config['output_directory_path'], filename)
            cv2.imwrite(dst_path, frame.frame)
            lfilename = f"{config['episode_number']}_{frame.timestamp.with_delimiter('_')}_labelled.jpg"
            dst_path = os.path.join(config['output_directory_path'], lfilename)
            cv2.imwrite(dst_path, frame.labelled_frame)

    def update_results(self, extracted_frames):
        for frame in extracted_frames:
            self.result_logger.add_skull_entry(self.config['episode_number'], frame.timestamp, frame.coord)

    def upload_output_files(self, upload_images=True):
        dir_path = self.config['output_directory_path']
        for file in os.listdir(dir_path):
            if (file.endswith('labelled.jpg') and upload_images):
                self.gdrive.upload_file(os.path.join(dir_path, file), folder_name="Test")
        self.gdrive.upload_file(self.config['result_file_path'],
                                folder_name="Test",
                                file_name=f'ep{self.config["episode_number"]}_phase1_results.csv')

    def run(self):
        try:
            # get episode from google drive
            episode_filepath = self.download_episode()
            # process episode
            extracted_frames = self.process_episode(episode_filepath)
            # update results and cache image locally on container
            self.save_extracted_frames(extracted_frames)
            self.update_results(extracted_frames)
            self.upload_output_files(upload_images=self.config['upload_images'] == 'True')
        except Exception as ex:
            logger.error('Phase 1 failed')
            raise ex


if __name__ == '__main__':
    import configparser
    config = configparser.ConfigParser()
    config.read('../strings.ini')
    p1 = Phase1(config['Phase1'])
    p1.run()