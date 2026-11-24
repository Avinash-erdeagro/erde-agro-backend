from decouple import config

from .base import *

DEBUG = config("DEBUG", default=True, cast=bool)

CORS_ALLOW_ALL_ORIGINS = True

SATELLITE_SYNC_LOCAL_FARMS_ONLY = config(
    "SATELLITE_SYNC_LOCAL_FARMS_ONLY", default=True, cast=bool
)

# Never create real IrriWatch orders from a local machine.
# Set to True in .env only if you deliberately need to.
IRRIWATCH_ALLOW_ORDER_CREATION = config(
    "IRRIWATCH_ALLOW_ORDER_CREATION", default=False, cast=bool
)
