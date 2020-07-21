import os
import sys
import configparser
import infinitechallenge.logging
from tempfile import NamedTemporaryFile
from infinitechallenge.utils.estimation import estimate_burned_member
from infinitechallenge.utils.sql_connecter import SqlConnector
from infinitechallenge.pipeline.results import Results
from infinitechallenge.logging import logger
from infinitechallenge.utils.gdrivefile_util import GDrive
from infinitechallenge.utils.parsing import get_episode_number_from_filename


class Phase3:
    def __init__(self, config, episode_filename):
        logger.info('initializing phase3 parameters')
        self.episode_number = get_episode_number_from_filename(episode_filename)

        input_directory_path = os.path.join(config['input_directory_path'], f'episode{self.episode_number}')
        self.save_results = config['save_results']
        self.upload_results = config['upload_results']
        self.output_directory_path = os.path.join(config['output_directory_path'], f'episode{self.episode_number}')
        if self.save_results:
            os.makedirs(self.output_directory_path, exist_ok=True)
        self.results = Results.read(os.path.join(input_directory_path, 'results.csv'))
        self.database = SqlConnector(config['db_endpoint'],
                                     config['db_name'],
                                     config['db_username'],
                                     os.environ['IC_RDS_PASSWORD'])
        self.db_tablename = config['db_tablename']
        # for uploading
        self.upload_results = config['upload_results']
        self.gdrive = GDrive(token_path=os.environ['IC_GDRIVE_AUTH_TOKEN_PATH'],
                             client_secrets_path=os.environ['IC_GDRIVE_CLIENT_SECRETS_PATH'])

    def upload_cached_files(self):
        remote_dir = f'episode{self.episode_number}_output'
        if self.upload_results:
            tempfile = NamedTemporaryFile(suffix='.csv')
            self.results.write(tempfile.name)
            tempfile.seek(0)
            self.gdrive.upload_file(tempfile.name, remote_filepath=os.path.join(remote_dir, 'phase3_results.csv'))

    def save_cached_files(self):
        if self.save_results:
            self.results.write(os.path.join(self.output_directory_path, 'results.csv'))

    def process_results(self):
        entries = self.results.get_entries()
        for idx in entries:
            entry = entries[idx]
            burned = estimate_burned_member(entry[Results.FIELDNAME_SC_LIST], entry[Results.FIELDNAME_FC_LIST], entry[Results.FIELDNAME_NAME_LIST])
            ep, time = idx
            if burned:
                self.results.update_burned_member(ep, time, burned)
            else:
                self.results.update_burned_member(ep, time, 'NO_BURN')

    def update_database(self):
        tempfile = NamedTemporaryFile(suffix='.csv')
        self.results.write(tempfile.name)
        tempfile.seek(0)
        self.database.bulk_insert_csv(tempfile.name, self.db_tablename, [Results.FIELDNAME_EP, Results.FIELDNAME_TIME, Results.FIELDNAME_BURNED_MEMBER])

    def run(self):
        try:
            logger.info('Estimating burned members...')
            self.process_results()
            logger.info('Updating database...')
            self.update_database()
            self.upload_cached_files()
            self.save_cached_files()
        except Exception as ex:
            logger.error('Phase 3 failed')
            raise ex


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read(sys.argv[1])
    infinitechallenge.logging.add_file_handler(config['LOG']['logfile_directory'])
    p3 = Phase3(config['Phase3'], sys.argv[2])
    p3.run()
