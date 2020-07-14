import pickle
import io
import os.path
# from logger.base_logger import logger
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


def authenticate():
    """Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('drive', 'v3', credentials=creds)
    return service


def search_file_by_name(drive_service, file_name):
    print('searching file name {} in gdrive...'.format(file_name))
    page_token = None
    results = {}
    try:
        while True:
            response = drive_service.files().list(q="name='{}'".format(file_name),
                                                  spaces='drive',
                                                  fields='nextPageToken, files(id, name)',
                                                  pageToken=page_token).execute()
            results = response.get('files', [])
            for file in results:
                # Process change
                print('Found file: %s (%s)' % (file.get('name'), file.get('id')))
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
    except Exception as ex:
        print(ex)
    print(results)
    return results


def download_file(drive_service, file_name, path_to_download):
    file_id = search_file_by_name(drive_service, file_name)[0]['id']
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.FileIO(path_to_download, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False

    try:
        while done is False:
            status, done = downloader.next_chunk()
            print("Download %d%%." % int(status.progress() * 100))
    except Exception as ex:
        print(ex)

def upload_file(file_name, drive_service, folder_name, file_path, file_mime_type):
    # Search for folder id in Drive
    page_token = None
    folders = []
    while True:
        response = drive_service.files().list(
            q=f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}'",
            spaces='drive',
            fields='nextPageToken, files(id, name)',
            pageToken=page_token).execute()
        for folder in response.get('files', []):
            folders.append(folder)
        page_token = response.get('nextPageToken', None)
        if page_token is None:
            break
    if not len(folders):
        raise Exception('Specified Google Drive folder not found')
    if len(folders) > 1:
        raise Exception('Exists duplicate folders with the given name')
    folder_id = ''
    for folder in folders:
        folder_id = folder.get('id')
    # Upload file to designated folder
    file_metadata = {
        'name': [file_name],
        'parents': [folder_id]
    }
    media = MediaFileUpload(file_path,
                            mimetype=file_mime_type,
                            resumable=True)
    file = drive_service.files().create(body=file_metadata,
                                        media_body=media,
                                        fields='id').execute()
    print(f"Successfully uploaded file {file_name} to {folder_name}.")

def main():
    service = authenticate()

    # Call the Drive v3 API
    results = service.files().list(
        pageSize=10, fields="nextPageToken, files(id, name)").execute()
    items = results.get('files', [])

    if not items:
        print('No files found.')
    else:
        print('Files:')
        for item in items:
            print(u'{0} ({1})'.format(item['name'], item['id']))

    path = os.path.join('resources', 'sample_episodes')

    file_name = 'ENV_GDRIVE_TEST.txt'
    path = os.path.join(path, file_name)
    download_file(service, 'ENV_GDRIVE_TEST.txt', path)


if __name__ == '__main__':
    main()