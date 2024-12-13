import json

import requests


class XNAT:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.auth_url = f"{base_url}/data/JSESSION"
        self.inbox_url = f"{base_url}/data/services/import"
        self.username = username
        self.password = password
        self._create_session()
        self.inbox_sessions = []

    def _create_session(self):
        self.session = requests.Session()
        self.session.auth = (self.username, self.password)
        self.session.headers.update({'Content-Type': 'application/json'})
        response = self.session.post(self.auth_url)
        if response.status_code != 200:
            raise Exception("Failed to authenticate with XNAT")

    def get_session(self):
        return self.session

    def close(self):
        self.session.close()

    def create_scan_resource(self, project_id, experiment_id, scan_id, resource_label):
        pass

    def refresh_catalog(self, project_id, experiment_id, scan_id):
        pass

    # ~ DICOM Inbox methods
    def post_to_inbox(self, project_id, subject_id, expt_label, inbox_path):
        params = {
            'import-handler': 'inbox',
            'cleanupAfterImport': 'true',
            'PROJECT_ID': project_id,
            'SUBJECT_ID': subject_id,
            'EXPT_LABEL': expt_label,
            'path': inbox_path
        }
        return self.session.post(self.inbox_url, params=params)

    def get_inbox_session_status(self, inbox_id):
        url = f"{self.base_url}/{inbox_id}"
        response = self.session.get(url)
        if response:
            try:
                status = response.json().get('status')
                resolution = response.json().get('resolution')
                return f'{status} : {resolution}'
            except json.JSONDecodeError:
                return 'Failed : JSON decode error'




