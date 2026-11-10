import calendar
from datetime import date, datetime, time, timedelta
import math
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transaction import (
    PaginatedTransactionResponse,
    PaymentMethod,
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
)

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.post("/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transaction = Transaction(**payload.model_dump(), user_id=current_user.id)
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.get("/", response_model=PaginatedTransactionResponse | list[TransactionResponse])
def list_transactions(
    category: str | None = None,
    merchant: str | None = None,
    transaction_type: str | None = Query(default=None, pattern="^(expense|income)$"),
    payment_method: PaymentMethod | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    view: Literal["daily", "weekly", "monthly"] | None = None,
    reference_date: date | None = None,
    sort_by: Literal["transaction_date", "date", "amount", "created_at", "created_date"] = "transaction_date",
    sort_order: Literal["asc", "desc"] | None = None,
    order: Literal["asc", "desc"] | None = None,
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    paginate: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Transaction).filter(Transaction.user_id == current_user.id)

    # Resolve date boundaries
    effective_start = start_date or date_from
    effective_end = end_date or date_to

    if view is not None:
        ref = reference_date or date.today()
        if view == "daily":
            if effective_start is None:
                effective_start = ref
            if effective_end is None:
                effective_end = ref
        elif view == "weekly":
            start_of_week = ref - timedelta(days=ref.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            if effective_start is None:
                effective_start = start_of_week
            if effective_end is None:
                effective_end = end_of_week
        elif view == "monthly":
            _, last_day = calendar.monthrange(ref.year, ref.month)
            if effective_start is None:
                effective_start = date(ref.year, ref.month, 1)
            if effective_end is None:
                effective_end = date(ref.year, ref.month, last_day)

    # Validate date range
    if effective_start is not None and effective_end is not None and effective_start > effective_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date cannot be after end date",
        )

    # Apply filters
    if category:
        query = query.filter(Transaction.category == category)
    if merchant:
        query = query.filter(Transaction.merchant.ilike(f"%{merchant}%"))
    if transaction_type:
        query = query.filter(Transaction.transaction_type == transaction_type)
    if payment_method:
        query = query.filter(Transaction.payment_method == payment_method)
    if effective_start:
        query = query.filter(Transaction.transaction_date >= datetime.combine(effective_start, time.min))
    if effective_end:
        query = query.filter(
            Transaction.transaction_date < datetime.combine(effective_end + timedelta(days=1), time.min)
        )

    # Apply sorting
    direction = (sort_order or order or "desc").lower()
    if sort_by == "amount":
        sort_col = Transaction.amount
    elif sort_by in ("created_at", "created_date"):
        sort_col = Transaction.created_at
    else:
        sort_col = Transaction.transaction_date

    if direction == "asc":
        query = query.order_by(sort_col.asc(), Transaction.id.asc())
    else:
        query = query.order_by(sort_col.desc(), Transaction.id.desc())

    # Apply pagination if requested
    is_paginated = (page is not None) or (page_size is not None) or paginate
    if is_paginated:
        actual_page = page if page is not None else 1
        actual_page_size = page_size if page_size is not None else 10
        total_items = query.count()
        total_pages = math.ceil(total_items / actual_page_size) if total_items > 0 else 0
        has_previous = actual_page > 1
        has_next = actual_page < total_pages
        items = query.offset((actual_page - 1) * actual_page_size).limit(actual_page_size).all()
        return PaginatedTransactionResponse(
            items=items,
            total=total_items,
            total_count=total_items,
            page=actual_page,
            page_size=actual_page_size,
            total_pages=total_pages,
            has_previous=has_previous,
            has_next=has_next,
            has_prev=has_previous,
            transactions=items,
        )

    return query.all()


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.user_id == current_user.id)
        .first()
    )
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction


@router.patch("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: int,
    payload: TransactionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.user_id == current_user.id)
        .first()
    )
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if value is None and field != "merchant":
            raise HTTPException(status_code=422, detail=f"{field} cannot be null")
        setattr(transaction, field, value)

    db.commit()
    db.refresh(transaction)
    return transaction


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.user_id == current_user.id)
        .first()
    )
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    db.delete(transaction)
    db.commit()
