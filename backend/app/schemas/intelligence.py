from typing import Literal

from pydantic import BaseModel, Field


Category = Literal[
    "Food", "Transport", "Shopping", "Bills", "Education",
    "Entertainment", "Health", "Travel", "Other",
]


class CategorySuggestionRequest(BaseModel):
    description: str = Field(min_length=2, max_length=255)
    merchant: str | None = Field(default=None, max_length=120)
    transaction_type: Literal["expense", "income"] = "expense"


class CategorySuggestionResponse(BaseModel):
    category: Category
    confidence: float = Field(ge=0, le=1)
    reason: str
    source: Literal["ollama", "rules"]
