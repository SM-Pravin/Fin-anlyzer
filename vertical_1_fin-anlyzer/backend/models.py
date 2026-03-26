"""
Pydantic V2 models for the Financial Command Center.
All IDs are UUID strings generated at object creation time.
"""

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, Any
from enum import Enum
from datetime import datetime
import uuid


# ── Enums ────────────────────────────────────────────────────────────────────

class AssetType(str, Enum):
    Cash = "Cash"
    Bank = "Bank"
    Gold = "Gold"
    Land = "Land"


class PayableStatus(str, Enum):
    Pending = "Pending"
    Paid = "Paid"


class ReceivableStatus(str, Enum):
    Pending = "Pending"
    Received = "Received"


class ConfidenceLevel(str, Enum):
    High = "High"
    Med = "Med"
    Low = "Low"


# ── Domain models ─────────────────────────────────────────────────────────────

class AssetModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: AssetType
    value: float = Field(ge=0)
    liquidity_score: int = Field(ge=1, le=5)


class PayableModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    creditor: str
    amount: float = Field(gt=0)
    due_date: datetime
    penalty_fee: float = Field(default=0.0, ge=0)
    status: PayableStatus = PayableStatus.Pending


class ReceivableModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str
    amount: float = Field(gt=0)
    expected_date: datetime
    confidence: ConfidenceLevel
    status: ReceivableStatus = ReceivableStatus.Pending


class TransactionModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    type: str   # "payment" | "income"
    amount: float
    asset_id: str
    description: str


# ── Request schemas ────────────────────────────────────────────────────────────

class AddEntryRequest(BaseModel):
    """Polymorphic entry creation payload."""
    entry_type: str          # "asset" | "payable" | "receivable"
    data: dict[str, Any]


class PaymentAllocation(BaseModel):
    """A single asset deduction within a split payment."""
    asset_id: str
    amount: float = Field(gt=0)


class ProcessPaymentRequest(BaseModel):
    payable_id: str
    allocations: list[PaymentAllocation] = Field(
        min_length=1,
        description="One or more (asset_id, amount) pairs that together cover the payable amount.",
    )


class ProcessIncomeRequest(BaseModel):
    receivable_id: str
    asset_id: str


class ChatRequest(BaseModel):
    message: str
    custom_instruction: str = ""