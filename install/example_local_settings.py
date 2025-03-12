import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': '',
        'USER': 'pgadmin',
        'PASSWORD': '',
        'HOST': 'postgresql-oqulabs.postgres.database.azure.com',
        'PORT': '5432',
    }
}
DEBUG = False
ALLOWED_HOSTS = [".oqulabs.kz"]
CSRF_TRUSTED_ORIGINS = ['https://.oqulabs.kz', 'http://.oqulabs.kz']


s3_endpoint = "https://screenshots.object.pscloud.io"
s3_bucket = ""
s3_key_id = ""
s3_application_key = ""
