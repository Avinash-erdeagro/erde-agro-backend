from decouple import config

from .base import *

DEBUG = config("DEBUG", default=True, cast=bool)

CORS_ALLOW_ALL_ORIGINS = True

SATELLITE_SYNC_LOCAL_FARMS_ONLY = config(
    "SATELLITE_SYNC_LOCAL_FARMS_ONLY", default=True, cast=bool
)