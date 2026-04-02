from pathlib import Path

import firebase_admin
from decouple import config
from firebase_admin import auth, credentials
from django.conf import settings


def get_firebase_app():
    if firebase_admin._apps:
        return firebase_admin.get_app()

    service_account_path = config("FIREBASE_SERVICE_ACCOUNT_PATH")
    absolute_path = Path(settings.BASE_DIR) / service_account_path

    cred = credentials.Certificate(str(absolute_path))
    return firebase_admin.initialize_app(cred)


def verify_firebase_id_token(id_token: str):
    get_firebase_app()
    return auth.verify_id_token(id_token)
