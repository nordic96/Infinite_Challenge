import os
from tempfile import NamedTemporaryFile
from src.utils.sql_connecter import SqlConnector
from src.logger.result_logger import ResultLogger, FIELDNAME_EP, FIELDNAME_TIME, FIELDNAME_BURNED_MEMBER
from src.logger.base_logger import logger
from src.utils.gdrivefile_util import GDrive


class Phase2:
    def __init__(self, config):
        logger.info('initializing phase3 parameters')
        self.config = config
        try:
            self.config['episode_number'] = os.environ['IC_EPISODE_NUMBER']
            self.config['db_password'] = os.environ['IC_RDS_PASSWORD']
            self.config['token_path'] = os.environ['IC_GDRIVE_AUTH_TOKEN_PATH']
            self.config['client_secrets_path'] = os.environ['IC_GDRIVE_CLIENT_SECRETS_PATH']
        except KeyError as ex:
            logger.error('Missing required environment variable')
            raise ex

        self.result_cache = None
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

    def upload_output_files(self):
        self.gdrive.upload_file(self.config['result_file_path'],
                                folder_name="Test",
                                file_name=f'ep{self.config["episode_number"]}_phase3_results.csv')

    def run(self):
        try:
            logger.info('Estimating burned members...')
            list_of_dict = self.result_logger.estimate_burned_member()
            self.result_logger.bulk_update_entries(list_of_dict)
            logger.info('Updating database...')
            con = SqlConnector(self.config['result_file_path'],
                               self.config['db_endpoint'],
                               self.config['db_name'],
                               self.config['db_username'],
                               self.config['db_password'])
            con.bulk_insert_csv(self.config['db_tablename'], [FIELDNAME_EP, FIELDNAME_TIME, FIELDNAME_BURNED_MEMBER])
            self.upload_output_files()
        except Exception as ex:
            logger.error('Phase 3 failed')
            raise ex


if __name__ == '__main__':
    import configparser
    config = configparser.ConfigParser()
    config.read('../strings.ini')
    p1 = Phase2(config['Phase3'])
    p1.run()