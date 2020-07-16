import os.path
from mimetypes import guess_type
from pickle import dump as p_dump, load as p_load
from io import FileIO
from logger.base_logger import logger
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.metadata',
    'https://www.googleapis.com/auth/drive.readonly'
]


class AuthenticationError(Exception):
    def __init__(self, *args):
        super().__init__('Failed to authenticate Google Drive v3 credentials.', *args)


class DuplicateError(Exception):
    def __init__(self, *args):
        super().__init__(*args)


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
                except (AttributeError, FileNotFoundError, IsADirectoryError) as ex:
                    if attempt == len(authentication_methods):
                        raise AuthenticationError from ex
            else:
                self.drive = build('drive', 'v3', credentials=self.credentials)

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
            raise IsADirectoryError(f'Serialized token file was expected. \'{self.token_path}\' is a directory')
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
            self.credentials = credentials
            with open(self.token_path, 'wb') as token:
                p_dump(self.credentials, token)
            return True
        return False

    def _get_file_id(self, remote_filepath, folder_id=None):
        """
        Gets the fileId of the first file matching the file name specified

        :param remote_filepath: path of the file in the drive whose fileId is to be retrieved
        :return: file_id of the file if it exists
        """
        folder_name, file_name = os.path.split(remote_filepath)
        if not folder_id:
            folder_id = self._get_folder_id(folder_name)
        logger.debug(f'searching for {file_name} in {folder_name}')
        page_token = None
        while True:
            response = self.drive.files().list(q=f"name='{file_name}' and '{folder_id}' in parents and trashed = false",
                                               spaces='drive',
                                               fields='nextPageToken, files(id, name, parents)',
                                               pageToken=page_token).execute()
            results = response.get('files', [])
            if len(results) > 1:
                logger.critical(f'Duplicates of {remote_filepath} found. File paths should be unique')
                raise DuplicateError('File paths should be unique')
            elif len(results) == 1:
                return results[0]['id']
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                raise FileNotFoundError(f'{remote_filepath} cannot be found')
            logger.debug(f'{file_name} not found, searching in next page...')

    def list_files(self, page_size=10):
        """
        Lists the first {page_size} files in the drive

        :param page_size: The number of items to list
        :return: None
        """
        results = self.drive.files().list(
            pageSize=page_size, fields="nextPageToken, files(id, name, mimeType)").execute()
        items = results.get('files', [])
        if not items:
            logger.info('No files found.')
        else:
            logger.info('Files:')
            for item in items:
                logger.info(u'{0} ({1} || {2})'.format(item['name'], item['mimeType'], item['id']))

    def download_file(self, remote_filepath, output_path):
        """Attempts to download the specified file to the specified output path

        :param remote_filepath: Filepath of the file in the drive to be downloaded
        :param output_path: Destination where the downloaded file will be saved
        """
        folder_name, file_name = os.path.split(remote_filepath)
        file_id = self._get_file_id(remote_filepath)
        request = self.drive.files().get_media(fileId=file_id)
        fh = FileIO(output_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if done:
                logger.info(f'Downloading {file_name}[{file_id}] completed.')
            else:
                logger.info(f"Downloading {file_name}[{file_id}] {str(int(status.progress() * 100))}%")

    def mkdir(self, folder_name):
        """ Makes a directory as specified by folder_name if the directory does not exist.

        :param folder_name: absolute path of the directory to be created
        :return: folder id of the directory created, or existing directory if one already exists with the same name
        """
        try:
            id = self._get_folder_id(folder_name)
            logger.warning('Folder already exists')
            return id
        except FileNotFoundError:
            metadata = {
                "mimeType": "application/vnd.google-apps.folder",
                "name": folder_name
            }
            folder = self.drive.files().create(body=metadata, fields='id').execute()
            return folder['id']

    def _get_folder_id(self, folder_name):
        """ Retrieves the folder id of the specified folder

        :param folder_name: Name of the folder whose id is to be retrieved
        :return: Id of the specified folder
        """
        if not folder_name or folder_name == 'root':
            return 'root'
        # Search for folder id in Drive
        page_token = None
        folders = []
        while True:
            response = self.drive.files().list(
                q=f"trashed = false and mimeType='application/vnd.google-apps.folder' and name='{folder_name}'",
                spaces='drive',
                fields='nextPageToken, files(id, name)',
                pageToken=page_token).execute()
            for folder in response.get('files', []):
                folders.append(folder)
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break

        if not folders:
            logger.debug(f'Unable to find folder named{folder_name}')
            raise FileNotFoundError(f'{folder_name} does not exist')

        elif len(folders) != 1:
            raise DuplicateError(f'Multiple folders with the name \'{folder_name}\' found. '
                                 f'Folder names should be unique.')

        folder = folders[0]
        logger.debug(f'{folder["name"]}[{folder["id"]}]')
        return folder["id"]

    def upload_file(self, filepath, remote_filepath=None, replace_if_exists=True):
        """ Uploads a file located at the specified filepath to the remote_filepath specified. If no remote_filepath is
        specified, the file is uploaded to the root directory on the drive

        :param filepath: The path of the local file to be uploaded
        :param remote_filepath: The filepath where the file is to be uploaded
        :return:
        """
        if remote_filepath is None:
            filename = os.path.basename(filepath)
            folder_name = 'root'
        else:
            folder_name, filename = os.path.split(remote_filepath)
        logger.info(f'Uploading {filename}')
        try:
            folder_id = self._get_folder_id(folder_name)
        except FileNotFoundError:
            logger.info(f'Target folder [{folder_name}] not found, creating directory')
            folder_id = self.mkdir(folder_name)
        file_metadata = {'name': [filename], 'parents': [folder_id]}

        media = MediaFileUpload(filepath, mimetype=guess_type(filepath)[0])
        response_fields = 'id, name, parents'
        try:
            # attempt to update file if one with the same name exists
            file_id = self._get_file_id(filepath, folder_id=folder_id)
            # if FileNotFoundError was not raised

            metadata = self.drive.files().get(fileId=file_id).execute()
            if not replace_if_exists:
                logger.info(f"[{filename}] already exists and was not overwritten")
                return {'id': file_id, 'name': filename, 'parents': [folder_id]}
            del metadata['id']
            file = self.drive.files().update(fileId=file_id,
                                             body=metadata,
                                             media_body=media,
                                             fields=response_fields).execute()
            logger.info(f"[{file['name']}] already exists and was overwritten")
        except FileNotFoundError:
            file = self.drive.files().create(body=file_metadata,
                                             media_body=media,
                                             fields=response_fields).execute()
            logger.info(f"[{file['name']}] was uploaded to {folder_name}")
        return file


if __name__ == '__main__':
    drive = GDrive(token_path='../../token.pickle', client_secrets_path='../../credentials.json')

    # Call the Drive v3 API
    file_name = 'episode10.mp4'
    path = os.path.join('..', 'resources', 'sample_episodes', file_name)
    #drive.download_file(os.path.join('episodes', file_name), path)
    #drive.upload_file(path, os.path.join('test/directory/here', file_name))
