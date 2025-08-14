from google.oauth2 import service_account
from googleapiclient.discovery import build
import config

def debug_google_service_account():
    try:
        creds = config.get_google_service_account_credentials()
        print("Loaded service account credentials.")
        print("Service account email:", creds.service_account_email)
        print("Scopes:", creds.scopes)
        print("Impersonating:", creds._subject if hasattr(creds, '_subject') else 'N/A')
        # Try a simple API call
        admin_service = build('admin', 'directory_v1', credentials=creds)
        users = admin_service.users().list(customer='my_customer', maxResults=1).execute()
        print("API call succeeded. Example user:", users.get('users', [{}])[0].get('primaryEmail', 'N/A'))
    except Exception as e:
        print("ERROR:", e)

if __name__ == '__main__':
    debug_google_service_account()
