from decouple import config

from .base import *

DEBUG = config("DEBUG", default=True, cast=bool)

CORS_ALLOW_ALL_ORIGINS = True
