
import datetime
import httpx

from .models import Account, ExistingTransaction, Transaction


class ActualAPI:
    def __init__(self, host: str, api_key: str) -> None:
        self.host = host
        self.api_key = api_key
        self.client = httpx.AsyncClient(headers={"x-api-key": api_key})

    async def get_actual_accounts(self, budget_sync_id: str) -> list[Account]:
        url = f"{self.host}/budgets/{budget_sync_id}/accounts"
        r = await self.client.get(url)
        r.raise_for_status()
        return [Account(**account) for account in r.json()["data"]]

    async def get_actual_open_accounts(self, budget_sync_id: str) -> list[Account]:
        accounts = await self.get_actual_accounts(budget_sync_id)
        return [a for a in accounts if a.closed is False]

    async def get_payees_for_budget(self, budget_sync_id: str) -> list[dict]:
        url = f"{self.host}/budgets/{budget_sync_id}/payees"
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()["data"]

    async def get_transactions_for_account(
        self,
        budget_sync_id: str,
        account_id: str,
        since_date: datetime.date,
        until_date: datetime.date | None = None,
    ) -> list[ExistingTransaction]:
        url = f"{self.host}/budgets/{budget_sync_id}/accounts/{account_id}/transactions"
        params = {"since_date": since_date.isoformat()}
        if until_date:
            params["until_date"] = until_date.isoformat()
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return [ExistingTransaction(**transaction) for transaction in response.json()["data"]]

    async def import_transactions_to_actual(
        self, account_id: str, transactions: list[Transaction], budget_sync_id: str
    ) -> httpx.Response:
        data = {"transactions": [t.model_dump(mode="json") for t in transactions]}
        url = f"{self.host}/budgets/{budget_sync_id}/accounts/{account_id}/transactions/import"
        response = await self.client.post(url, json=data)
        response.raise_for_status()
        return response
