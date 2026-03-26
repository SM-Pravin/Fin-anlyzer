from enum import Enum


class AssetStatus(str, Enum):
    DIGITAL_PENDING  = "DIGITAL_PENDING"
    PHYSICAL_PENDING = "PHYSICAL_PENDING"
    CERTIFIED        = "CERTIFIED"
    REJECTED         = "REJECTED"


class AssetType(str, Enum):
    GOLD = "gold"
    LAND = "land"


class UserRole(str, Enum):
    USER  = "user"
    ADMIN = "admin"
    AGENT = "agent"
