from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import os


class GoogleDriveManager:
    def __init__(self, creds_file="mycreds.txt"):
        self.creds_file = creds_file
        self.drive = None

    def authenticate(self):
        gauth = GoogleAuth()
        gauth.settings['get_refresh_token'] = True
        gauth.settings['oauth_scope'] = ['https://www.googleapis.com/auth/drive']
        gauth.LoadCredentialsFile(self.creds_file)

        if gauth.credentials is None:
            gauth.LocalWebserverAuth()
        elif gauth.access_token_expired:
            gauth.Refresh()
        else:
            gauth.Authorize()

        gauth.SaveCredentialsFile(self.creds_file)
        self.drive = GoogleDrive(gauth)

    def get_or_create_folder(self, name, parent_id=None):
        query = f"title='{name}' and trashed=false and mimeType='application/vnd.google-apps.folder'"
        if parent_id:
            query += f" and '{parent_id}' in parents"

        folders = self.drive.ListFile({'q': query}).GetList()
        if folders:
            return folders[0]['id']

        metadata = {'title': name, 'mimeType': 'application/vnd.google-apps.folder'}
        if parent_id:
            metadata['parents'] = [{'id': parent_id}]

        folder = self.drive.CreateFile(metadata)
        folder.Upload()
        return folder['id']

    def setup_company_folders(self, company):
        root = self.get_or_create_folder("Screener Data")
        company_folder = self.get_or_create_folder(company, root)

        return {
            "quarter": self.get_or_create_folder("Quarter", company_folder),
            "annual": self.get_or_create_folder("Annual", company_folder),
            "concall": self.get_or_create_folder("Concalls", company_folder)
        }

    def upload_file(self, local_path, folder_id):
        file = self.drive.CreateFile({
            'title': os.path.basename(local_path),
            'parents': [{'id': folder_id}]
        })
        file.SetContentFile(local_path)
        file.Upload()
        print(f"☁️ Uploaded → {file['title']}")
