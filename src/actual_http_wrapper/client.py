import datetime
from decimal import ROUND_HALF_UP, Decimal

import requests

from .models import Account, ExistingTransaction, Payee, Transaction


class ActualAPI:
    def __init__(self, host: str, api_key: str, budget_sync_id: str) -> None:
        self.host = host
        self.session = requests.Session()
        self.session.headers.update({"x-api-key": api_key})
        self.budget_sync_id = budget_sync_id

    def create_payee_for_budget(self, payee: Payee) -> Payee:
        url = f"{self.host}/budgets/{self.budget_sync_id}/payees"
        data = {"payee": payee.model_dump(mode="json", exclude_none=True)}
        r = self.session.post(url, json=data)
        r.raise_for_status()
        return Payee(**r.json()["data"])

    def ensure_payee_exists(self, payee_name: str) -> Payee:
        payees = self.get_payees_for_budget()
        for payee in payees:
            if payee.name == payee_name:
                return payee
        new_payee = Payee(name=payee_name)
        created_payee = self.create_payee_for_budget(new_payee)
        new_payee.id = created_payee.id
        return new_payee

    def get_accounts(self) -> list[Account]:
        url = f"{self.host}/budgets/{self.budget_sync_id}/accounts"
        r = self.session.get(url)
        r.raise_for_status()
        return [Account(**account) for account in r.json()["data"]]

    def get_account_balance(self, account_id: str) -> Decimal:
        url = f"{self.host}/budgets/{self.budget_sync_id}/accounts/{account_id}/balance"
        r = self.session.get(url)
        r.raise_for_status()
        raw_balance = r.json()["data"]
        return Decimal(raw_balance / 100).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

    def get_open_accounts(self) -> list[Account]:
        accounts = self.get_accounts()
        return [a for a in accounts if a.closed is False]

    def get_payees_for_budget(self) -> list[Payee]:
        url = f"{self.host}/budgets/{self.budget_sync_id}/payees"
        response = self.session.get(url)
        response.raise_for_status()
        return [Payee(**payee) for payee in response.json()["data"]]

    def get_transactions_for_account(
        self,
        account_id: str,
        since_date: datetime.date,
        until_date: datetime.date | None = None,
    ) -> list[ExistingTransaction]:
        url = f"{self.host}/budgets/{self.budget_sync_id}/accounts/{account_id}/transactions"
        params = {"since_date": since_date.isoformat()}
        if until_date:
            params["until_date"] = until_date.isoformat()
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return [ExistingTransaction(**transaction) for transaction in response.json()["data"]]

    def import_transactions(
        self,
        account_id: str,
        transactions: list[Transaction],
    ) -> requests.Response:
        data = {"transactions": [t.model_dump(mode="json") for t in transactions]}
        url = f"{self.host}/budgets/{self.budget_sync_id}/accounts/{account_id}/transactions/import"
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response

    def trigger_all_bank_syncs(self) -> requests.Response:
        url = f"{self.host}/budgets/{self.budget_sync_id}/accounts/banksync"
        response = self.session.post(url)
        response.raise_for_status()
        return response
