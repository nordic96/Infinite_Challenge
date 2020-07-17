import os
import sys
import shutil
import configparser
import cv2
from tempfile import TemporaryDirectory, NamedTemporaryFile
from infinitechallenge.pipeline import Results
from infinitechallenge.logging import logger
from infinitechallenge.model import vid_recognition as vr
from infinitechallenge.utils.gdrivefile_util import GDrive


# 1. process a single video using model
# 2. cache images with skulls
# 3. update result.csv for each image
class Phase1:
    def __init__(self, config, episode_number):
        logger.info('Initializing phase 1 parameters')
        self.episode_number = episode_number

        # prepare directory for caching
        self.cache_dir = TemporaryDirectory()
        self.results = Results.blank()
        # prepare directory for local saving
        self.save_images = config.getboolean('save_images')
        self.save_results = config.getboolean('save_results')
        if self.save_images or self.save_results:
            out_dir_path = os.path.join(config['output_directory_path'], f'episode{self.episode_number}')
            if not os.path.exists(out_dir_path):
                os.makedirs(out_dir_path, exist_ok=True)
            self.output_directory_path = out_dir_path
        # for uploading cached files
        self.upload_unlabelled = config.getboolean('upload_unlabelled')
        self.upload_labelled = config.getboolean('upload_labelled')
        self.upload_results = config.getboolean('upload_results')
        # for video processing
        self.display = config.getboolean('display')
        self.video_sample_rate = config.getint('video_sample_rate')
        self.skull_confidence_threshold = config.getfloat('skull_confidence_threshold')
        self.skull_model_version = config['skull_model_version']
        try:
            self.azure_key = os.environ['IC_AZURE_KEY_SKULL']
        except KeyError as ex:
            logger.error('Missing required environment variable')
            raise ex
        # for google drive
        self.gdrive = GDrive(token_path=os.environ['IC_GDRIVE_AUTH_TOKEN_PATH'],
                             client_secrets_path=os.environ['IC_GDRIVE_CLIENT_SECRETS_PATH'])

    def download_episode(self):
        episode_filename = f'episode{self.episode_number}.mp4'
        remote_path = os.path.join('episodes', episode_filename)
        cached_video_path = os.path.join(self.cache_dir.name, episode_filename)
        self.gdrive.download_file(remote_path, cached_video_path)
        return cached_video_path

    def process_episode(self, episode_filepath):
        extracted_frames = vr.process_stream(
            video_path=episode_filepath,
            azure_key=self.azure_key,
            confidence=self.skull_confidence_threshold,
            model_version=self.skull_model_version,
            sample_rate=self.video_sample_rate,
            display=self.display
        )
        return extracted_frames

    def cache_extracted_frames(self, extracted_frames):
        for frame in extracted_frames:
            filename = f"{self.episode_number}_{frame.timestamp.with_delimiter('_')}.jpg"
            dst_path = os.path.join(self.cache_dir.name, filename)
            cv2.imwrite(dst_path, frame.frame)
            lfilename = f"{self.episode_number}_{frame.timestamp.with_delimiter('_')}_skull.jpg"
            dst_path = os.path.join(self.cache_dir.name, lfilename)
            cv2.imwrite(dst_path, frame.labelled_frame)

    def update_results(self, extracted_frames):
        for frame in extracted_frames:
            self.results.add_skull_entry(self.episode_number, str(frame.timestamp), frame.coord)

    def upload_cached_files(self):
        dir_path = self.cache_dir.name
        dst_dir = f'episode{self.episode_number}_output'
        for file in os.listdir(dir_path):
            path = os.path.join(dir_path, file)
            if file.endswith('skull.jpg') and self.upload_labelled:
                self.gdrive.upload_file(path, remote_filepath=os.path.join(dst_dir, file))
            elif file.endswith('.jpg') and not file.endswith('skull.jpg') and self.upload_unlabelled:
                self.gdrive.upload_file(path, remote_filepath=os.path.join(dst_dir, file))
        if self.upload_results:
            tempfile = NamedTemporaryFile()
            self.results.write(tempfile)
            tempfile.seek(0)
            self.gdrive.upload_file(tempfile.name, remote_filepath=os.path.join(dst_dir, 'phase1_results.csv'))

    def save_cached_files(self):
        out_dir_path = self.output_directory_path
        if not os.path.isdir(out_dir_path):
            raise FileNotFoundError(f'The specified output path is not a directory: {out_dir_path}')
        if self.save_results:
            for file in os.listdir(self.cache_dir.name):
                if file.endswith('.jpg'):
                    dst = os.path.join(out_dir_path, file)
                    dst = os.path.abspath(dst)
                    logger.info(f'Saving {file} to {dst}')
                    shutil.move(os.path.join(self.cache_dir.name, file), dst)
        if self.save_results:
            self.results.write(os.path.join(out_dir_path, 'results.csv'))

    def run(self):
        try:
            logger.info('Phase 1 start')
            ep_no = self.episode_number
            # get episode from google drive
            logger.info(f'Downloading episode {ep_no} from Google Drive')
            episode_filepath = self.download_episode()
            # process episode
            logger.info(f'Finding frames with skulls in episode {ep_no}')
            extracted_frames = self.process_episode(episode_filepath)
            # update results and cache image locally on container
            logger.info(f'Caching frames with skulls in episode {ep_no}')
            self.cache_extracted_frames(extracted_frames)

            logger.info(f'Updating results CSV file')
            self.update_results(extracted_frames)

            self.upload_cached_files()
            self.save_cached_files()

            logger.info('Phase 1 complete')
        except Exception as ex:
            logger.error('Phase 1 failed')
            raise ex


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read(sys.argv[1])
    p1 = Phase1(config['Phase1'], sys.argv[2])
    p1.run()
