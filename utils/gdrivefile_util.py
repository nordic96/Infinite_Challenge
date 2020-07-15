import os.path
from pickle import dump as p_dump, load as p_load
from io import FileIO
from logger.base_logger import logger
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseDownload

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


class AuthenticationError(Exception):
    def __init__(self, *args):
        super().__init__('Failed to authenticate Google Drive v3 credentials.', *args)


class GDrive:

    def __init__(self, credentials: Credentials = None, token_path=None, client_secrets_path=None):
        self.credentials = credentials
        self.token_path = token_path
        self.client_secrets_path = client_secrets_path
        self.drive = None
        authentication_methods = [
            self.authenticate_by_token,
            self.authenticate_by_auth_flow
        ]
        attempt = 0
        for authenticate in authentication_methods:
            if self.credentials is None or not self.credentials.valid:
                try:
                    attempt += 1
                    if authenticate():
                        self.drive = build('drive', 'v3', credentials=self.credentials)
                        break
                except (FileNotFoundError, IsADirectoryError) as ex:
                    if attempt == len(authentication_methods):
                        raise AuthenticationError from ex

    def authenticate_by_token(self):
        """
        Attempt to authenticate GDrive v3 API using saved token (if one exists)
        """
        logger.debug(f'Attempting to authenticate by token @ {self.token_path} ...')
        # The file token.pickle stores the user's access and refresh tokens, and is created automatically when the
        # authorization flow completes for the first time.
        if os.path.isfile(self.token_path):
            with open(self.token_path, 'rb') as token:
                try:
                    credentials = p_load(token)
                    if credentials.expired and credentials.refresh_token:
                        logger.debug('Refreshing expired credentials ...')
                        credentials.refresh(Request())
                    if credentials.valid:
                        self.credentials = credentials
                        return True
                except AttributeError as ex:
                    logger.debug(f'Unable to unserialize {self.token_path} as {Credentials.__class__.__qualname__}')
                    raise ex
        elif os.path.isdir(self.token_path):
            raise IsADirectoryError(f'Serialized token file was expected \'{self.token_path}\' is a directory')
        elif not os.path.exists(self.token_path):
            raise FileNotFoundError(f'Serialized token file was expected. No such file: \'{self.token_path}\'')
        return False

    def authenticate_by_auth_flow(self):
        """
        Attempt to authenticate GDrive v3 API using authorization flow as specified in client secrets file
        """
        logger.debug(f'Attemping to authenticate by InstalledAppFlow @ {self.client_secrets_path} ...')
        flow = InstalledAppFlow.from_client_secrets_file(self.client_secrets_path, SCOPES)
        credentials = flow.run_local_server(port=0)
        # Save the credentials for the next run
        if credentials.valid:
            with open(self.token_path, 'wb') as token:
                p_dump(self.credentials, token)
            self.credentials = credentials
            return True
        return False

    def get_file_id(self, file_name):
        logger.debug(f'searching for {file_name} in gdrive...')
        page_token = None
        while True:
            response = self.drive.files().list(q=f"name='{file_name}'",
                                               spaces='drive',
                                               fields='nextPageToken, files(id, name)',
                                               pageToken=page_token).execute()
            results = response.get('files', [])
            for file in results:
                if file['name'] == file_name:
                    return file['id']
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                raise FileNotFoundError(file_name)
            logger.debug(f'{file_name} not found, searching in next page...')

    def list_files(self, page_size=10):
        results = self.drive.files().list(
            pageSize=page_size, fields="nextPageToken, files(id, name)").execute()
        items = results.get('files', [])
        if not items:
            logger.info('No files found.')
        else:
            logger.info('Files:')
            for item in items:
                logger.info(u'{0} ({1})'.format(item['name'], item['id']))

    def download_file(self, file_name, output_path):
        file_id = self.get_file_id(file_name)
        request = self.drive.files().get_media(fileId=file_id)
        fh = FileIO(output_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if done:
                logger.info(f'Downloading [{file_name}] completed.')
            else:
                logger.info(f"Downloading [{file_name}] {str(int(status.progress() * 100))}%")


if __name__ == '__main__':
    drive = GDrive(token_path='../token.pickle', client_secrets_path='../credentials.json')

    # Call the Drive v3 API
    file_name = 'ENV_GDRIVE_TEST.txt'
    path = os.path.join('..', 'resources', 'sample_episodes', file_name)
    drive.list_files()
    drive.download_file(file_name, path)
