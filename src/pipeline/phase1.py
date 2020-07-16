import os
import shutil
import cv2
from logger.result_logger import ResultLogger
from tempfile import TemporaryDirectory
from logger.base_logger import logger
from model import vid_recognition as vr
from utils.gdrivefile_util import GDrive


# 1. process a single video using model
# 2. cache images with skulls
# 3. update result.csv for each image
class Phase1:
    def __init__(self, config):
        logger.info('Initializing phase 1 parameters')
        self.config = config
        try:
            self.config['episode_number'] = os.environ['IC_EPISODE_NUMBER']
            self.config['azure_key'] = os.environ['IC_AZURE_KEY_SKULL']
            self.config['token_path'] = os.environ['IC_GDRIVE_AUTH_TOKEN_PATH']
            self.config['client_secrets_path'] = os.environ['IC_GDRIVE_CLIENT_SECRETS_PATH']
        except KeyError as ex:
            logger.error('Missing required environment variable')
            raise ex

        # prepare directory for caching
        self.cache_dir = TemporaryDirectory()
        self.result_cache = os.path.join(self.cache_dir.name, 'results.csv')
        with open(self.result_cache, 'w') as f:
            f.write('')
        self.result_logger = ResultLogger(self.result_cache)
        # prepare directory for local saving
        if config.getboolean('save_images') or config.getboolean('save_results'):
            self.config['save_cached_files'] = 'True'
            out_dir_path = os.path.join(config['output_directory_path'], f'episode{config["episode_number"]}')
            if not os.path.exists(out_dir_path):
                os.makedirs(out_dir_path, exist_ok=True)
            self.config['output_directory_path'] = out_dir_path
        self.gdrive = GDrive(token_path=config['token_path'], client_secrets_path=config['client_secrets_path'])
        if config.getboolean('upload_labelled') or config.getboolean('upload_unlabelled') \
                or config.getboolean('upload_results'):
            self.config['upload_cached_files'] = 'True'

    def download_episode(self):
        config = self.config
        episode_filename = f'episode{config["episode_number"]}.mp4'
        remote_path = os.path.join('episodes', episode_filename)
        cached_video_path = os.path.join(self.cache_dir.name, episode_filename)
        self.gdrive.download_file(remote_path, cached_video_path)
        return cached_video_path

    def process_episode(self, episode_filepath):
        config = self.config
        extracted_frames = vr.process_stream(
            video_path=episode_filepath,
            azure_key=config['azure_key'],
            confidence=float(config['skull_confidence_threshold']),
            model_version=config['skull_model_version'],
            sample_rate=int(config['video_sample_rate']),
            display=config.getboolean('display')
        )
        return extracted_frames

    def cache_extracted_frames(self, extracted_frames):
        config = self.config
        for frame in extracted_frames:
            filename = f"{config['episode_number']}_{frame.timestamp.with_delimiter('_')}.jpg"
            dst_path = os.path.join(self.cache_dir.name, filename)
            cv2.imwrite(dst_path, frame.frame)
            lfilename = f"{config['episode_number']}_{frame.timestamp.with_delimiter('_')}_skull.jpg"
            dst_path = os.path.join(self.cache_dir.name, lfilename)
            cv2.imwrite(dst_path, frame.labelled_frame)

    def update_results(self, extracted_frames):
        for frame in extracted_frames:
            self.result_logger.add_skull_entry(self.config['episode_number'], frame.timestamp, frame.coord)

    def upload_cached_files(self, upload_unlabelled=True, upload_labelled=True, upload_results=True):
        dir_path = self.cache_dir.name
        dst_dir = f'episode{self.config["episode_number"]}_output'
        for file in os.listdir(dir_path):
            path = os.path.join(dir_path, file)
            if file == 'results.csv' and upload_results:
                self.gdrive.upload_file(path, remote_filepath=os.path.join(dst_dir, 'phase1_results.csv'))
            elif file.endswith('skull.jpg') and upload_labelled:
                self.gdrive.upload_file(path, remote_filepath=os.path.join(dst_dir, file))
            elif file.endswith('.jpg') and not file.endswith('skull.jpg') and upload_unlabelled:
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
        
    def run(self):
        try:
            logger.info('Phase 1 start')
            config = self.config
            # get episode from google drive
            logger.info(f'Downloading {config["episode_number"]} from Google Drive')
            episode_filepath = self.download_episode()
            # process episode
            logger.info(f'Finding frames with skulls in {config["episode_number"]}')
            extracted_frames = self.process_episode(episode_filepath)
            # update results and cache image locally on container
            logger.info(f'Caching frames with skulls in {config["episode_number"]}')
            self.cache_extracted_frames(extracted_frames)

            logger.info(f'Updating results CSV file')
            self.update_results(extracted_frames)

            if config.getboolean('upload_cached_files'):
                up_unlabelled = config.getboolean('upload_unlabelled')
                up_labelled = config.getboolean('upload_labelled')
                up_res = config.getboolean('upload_results')
                logger.info(f'Uploading cached files: '
                            f'unlabelled_images={up_unlabelled}, labelled_images={up_labelled}, results={up_res}')
                self.upload_cached_files(upload_unlabelled=up_unlabelled,
                                         upload_labelled=up_labelled,
                                         upload_results=up_res)

            if config.getboolean('save_cached_files'):
                save_imgs = config.getboolean('save_images')
                save_res = config.getboolean('save_results')
                logger.info(f'Saving cached files: unlabelled_images={save_imgs}, results={save_res}')
                self.save_cached_files(save_images=save_imgs, save_results=save_res)

            logger.info('Phase 1 complete')
        except Exception as ex:
            logger.error('Phase 1 failed')
            raise ex


if __name__ == '__main__':
    import configparser
    config = configparser.ConfigParser()
    config.read('../strings.ini')
    p1 = Phase1(config['Phase1'])
    p1.run()