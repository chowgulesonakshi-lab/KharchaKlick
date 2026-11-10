from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Category = Literal[
    "Food", "Transport", "Shopping", "Bills", "Education",
    "Entertainment", "Health", "Travel", "Other",
]
PaymentMethod = Literal[
    "Cash",
    "UPI",
    "Credit Card",
    "Debit Card",
    "Card",
    "Net Banking",
    "Wallet",
    "Other",
]
TransactionType = Literal["expense", "income"]


class TransactionCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    description: str = Field(min_length=1, max_length=255)
    merchant: str | None = Field(default=None, max_length=120)
    category: Category
    payment_method: PaymentMethod
    transaction_type: TransactionType = "expense"
    transaction_date: datetime


class TransactionUpdate(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    description: str | None = Field(default=None, min_length=1, max_length=255)
    merchant: str | None = Field(default=None, max_length=120)
    category: Category | None = None
    payment_method: PaymentMethod | None = None
    transaction_type: TransactionType | None = None
    transaction_date: datetime | None = None


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    amount: Decimal
    description: str
    merchant: str | None
    category: str
    payment_method: str
    transaction_type: str
    transaction_date: datetime
    created_at: datetime


class PaginatedTransactionResponse(BaseModel):
    items: list[TransactionResponse]
    total: int
    total_count: int | None = None
    page: int
    page_size: int
    total_pages: int
    has_previous: bool
    has_next: bool
    has_prev: bool | None = None
    transactions: list[TransactionResponse] | None = None
