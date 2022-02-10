from ke.settings.base import *

ALLOWED_HOSTS = ["*"]
DEBUG = True

DATABASES = {
'default': {
    'ENGINE': os.environ['RDS_DB_ENGINE'],
    'NAME': os.environ['RDS_DB_NAME'],
    'USER': os.environ['RDS_USERNAME'],
    'PASSWORD': os.environ['RDS_PASSWORD'],
    'HOST': os.environ['RDS_HOSTNAME'],
    'PORT': os.environ['RDS_PORT'],
    }
}