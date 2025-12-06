import datetime

from pydantic import BaseModel


class Account(BaseModel):
    id: str
    name: str
    offbudget: bool
    closed: bool


class ExistingTransaction(BaseModel):
    id: str
    account: str
    amount: int
    payee: str
    date: datetime.date
    cleared: bool
    imported_id: str | None
    notes: str | None


class Payee(BaseModel):
    id: str | None = None
    name: str | None = None
    category: str | None = None
    transfer_acct: str | None = None


class Transaction(BaseModel):
    account: str
    amount: int
    payee_name: str
    date: datetime.date
    cleared: bool
    imported_id: str
    notes: str | None = None
