from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate, TransactionResponse, TransactionUpdate

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.post("/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(payload: TransactionCreate, db: Session = Depends(get_db)):
    transaction = Transaction(**payload.model_dump())
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.get("/", response_model=list[TransactionResponse])
def list_transactions(
    category: str | None = None,
    merchant: str | None = None,
    transaction_type: str | None = Query(default=None, pattern="^(expense|income)$"),
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Transaction)

    if category:
        query = query.filter(Transaction.category == category)
    if merchant:
        query = query.filter(Transaction.merchant.ilike(f"%{merchant}%"))
    if transaction_type:
        query = query.filter(Transaction.transaction_type == transaction_type)
    if date_from:
        query = query.filter(Transaction.transaction_date >= datetime.combine(date_from, time.min))
    if date_to:
        query = query.filter(
            Transaction.transaction_date < datetime.combine(date_to + timedelta(days=1), time.min)
        )

    return query.order_by(Transaction.transaction_date.desc(), Transaction.id.desc()).all()


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(transaction_id: int, db: Session = Depends(get_db)):
    transaction = db.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction


@router.patch("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: int,
    payload: TransactionUpdate,
    db: Session = Depends(get_db),
):
    transaction = db.get(Transaction, transaction_id)
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
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    transaction = db.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    db.delete(transaction)
    db.commit()
