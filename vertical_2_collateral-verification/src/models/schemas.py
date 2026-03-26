from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

class PyObjectId(str):
    """Coerces a MongoDB ObjectId to a plain string for serialisation."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, _info=None):
        return str(v)


# ---------------------------------------------------------------------------
# Asset – response models
# ---------------------------------------------------------------------------

class AssetBaseResponse(BaseModel):
    """Fields common to every asset response (both types)."""
    id: str
    applicant_name: str
    pan_number: str
    asset_type: str
    status: str
    submitted_at: datetime
    document_urls: List[str] = []

    model_config = {"populate_by_name": True}


class GoldAssetResponse(AssetBaseResponse):
    declared_weight: float
    declared_purity: str
    structure: str
    measured_weight: Optional[float] = None
    tested_purity: Optional[str] = None


class LandAssetResponse(AssetBaseResponse):
    property_address: str
    gps_lat: float
    gps_long: float
    declared_size: float
    land_use_type: str


class CertifiedAssetPublicResponse(BaseModel):
    """
    Public-facing certificate view.
    PAN is masked (first 6 chars replaced with X).
    MongoDB _id is excluded.
    """
    applicant_name: str
    pan_number: str       # will be masked before returning
    asset_type: str
    status: str
    submitted_at: datetime
    certificate_id: str
    certified_on: datetime
    document_urls: List[str] = []

    # Gold optional fields
    declared_weight: Optional[float] = None
    declared_purity: Optional[str] = None
    structure: Optional[str] = None
    measured_weight: Optional[float] = None
    tested_purity: Optional[str] = None

    # Land optional fields
    property_address: Optional[str] = None
    gps_lat: Optional[float] = None
    gps_long: Optional[float] = None
    declared_size: Optional[float] = None
    land_use_type: Optional[str] = None

    @field_validator("pan_number", mode="before")
    @classmethod
    def mask_pan(cls, v: str) -> str:
        if len(v) > 6:
            return "X" * 6 + v[6:]
        return "X" * len(v)

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Field-agent certification inputs
# ---------------------------------------------------------------------------

class GoldCertifyInput(BaseModel):
    measured_weight: float = Field(..., gt=0)
    tested_purity: str


class LandCertifyInput(BaseModel):
    verified_gps_lat: float
    verified_gps_long: float


# ---------------------------------------------------------------------------
# Generic message
# ---------------------------------------------------------------------------

class MessageResponse(BaseModel):
    message: str
