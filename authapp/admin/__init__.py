from .locality import LocalityAdmin
from .profiles import FarmerProfileAdmin, FpoProfileAdmin
from .user import AppUserAdmin

__all__ = [
    "LocalityAdmin",
    "AppUserAdmin",
    "FpoProfileAdmin",
    "FarmerProfileAdmin",
]
