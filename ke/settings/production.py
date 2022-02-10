from ke.settings.base import *

DEBUG = True

ALLOWED_HOSTS = ['*', 'keanalytics-env.eba-5ypwhrkj.us-east-1.elasticbeanstalk.com']

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