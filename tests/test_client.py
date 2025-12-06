import datetime
from decimal import Decimal
from http import HTTPStatus
from typing import TYPE_CHECKING

from src.actual_http_wrapper.client import ActualAPI
from src.actual_http_wrapper.models import Account, ExistingTransaction, Transaction

if TYPE_CHECKING:
    from requests_mock import Mocker


def test_get_actual_accounts(requests_mock: "Mocker"):
    actual_api = ActualAPI("http://example.com", "key")
    account = {"id": "1", "name": "Checking", "offbudget": False, "closed": False}
    requests_mock.get(
        "http://example.com/budgets/123/accounts",
        json={"data": [account]},
    )
    actual_accounts = actual_api.get_actual_accounts("123")
    assert actual_accounts == [Account(**account)]


def test_get_actual_open_accounts(requests_mock: "Mocker"):
    actual_api = ActualAPI("http://example.com", "key")
    accounts = [
        {"id": "1", "name": "Checking", "offbudget": False, "closed": False},
        {"id": "2", "name": "Savings", "offbudget": False, "closed": True},
    ]
    requests_mock.get(
        "http://example.com/budgets/123/accounts",
        json={"data": accounts},
    )

    open_accounts = actual_api.get_actual_open_accounts("123")

    expected_accounts = [Account(**accounts[0])]
    assert open_accounts == expected_accounts


def test_import_transactions_to_actual(requests_mock: "Mocker"):
    actual_api = ActualAPI("http://example.com", "key")
    transactions = [
        Transaction(
            account="1",
            amount=1000,
            payee_name="Test Payee",
            date=datetime.date(2024, 1, 1),
            imported_id="txn1",
            cleared=True,
        ),
    ]
    requests_mock.post(
        "http://example.com/budgets/123/accounts/1/transactions/import",
        status_code=200,
    )

    response = actual_api.import_transactions_to_actual("1", transactions, "123")

    assert response.status_code == HTTPStatus.OK
    assert requests_mock.called
    assert requests_mock.last_request.json() == {  # pyright: ignore[reportOptionalMemberAccess]
        "transactions": [t.model_dump(mode="json") for t in transactions],
    }


def test_get_transactions_for_account_success(requests_mock: "Mocker"):
    actual_api = ActualAPI("http://example.com", "key")
    budget_id = "budget1"
    account_id = "acc1"
    since_date = datetime.date(2024, 1, 1)
    until_date = datetime.date(2024, 2, 1)
    url = f"http://example.com/budgets/{budget_id}/accounts/{account_id}/transactions"
    data = [
        {
            "id": "t1",
            "amount": 100,
            "date": "2024-01-02",
            "imported_id": "txn1",
            "cleared": True,
            "notes": None,
            "payee": "Payee1",
            "account": account_id,
        },
        {
            "id": "t2",
            "amount": 200,
            "date": "2024-01-03",
            "imported_id": "txn2",
            "cleared": False,
            "notes": "Test",
            "payee": "Payee2",
            "account": account_id,
        },
    ]
    requests_mock.get(url, json={"data": data})

    result = actual_api.get_transactions_for_account(
        budget_id,
        account_id,
        since_date,
        until_date,
    )

    assert result == [
        ExistingTransaction(
            id="t1",
            account=account_id,
            amount=100,
            payee="Payee1",
            date=datetime.date(2024, 1, 2),
            imported_id="txn1",
            cleared=True,
            notes=None,
        ),
        ExistingTransaction(
            id="t2",
            account=account_id,
            amount=200,
            payee="Payee2",
            date=datetime.date(2024, 1, 3),
            imported_id="txn2",
            cleared=False,
            notes="Test",
        ),
    ]


def test_get_payees_for_budget(requests_mock: "Mocker"):
    actual_api = ActualAPI("http://example.com", "key")
    budget_id = "budget1"
    url = f"http://example.com/budgets/{budget_id}/payees"
    payees = [
        {"id": "p1", "name": "Payee 1"},
        {"id": "p2", "name": "Payee 2"},
    ]
    requests_mock.get(url, json={"data": payees})

    result = actual_api.get_payees_for_budget(budget_id)

    assert result == payees


def test_get_account_balance(requests_mock: "Mocker"):
    actual_api = ActualAPI("http://example.com", "key")
    budget_id = "budget1"
    account_id = "acc1"
    url = f"http://example.com/budgets/{budget_id}/accounts/{account_id}/balance"
    requests_mock.get(url, json={"data": 12345})

    balance = actual_api.get_account_balance(budget_id, account_id)

    assert balance == Decimal("123.45")


def test_trigger_all_bank_syncs(requests_mock: "Mocker"):
    actual_api = ActualAPI("http://example.com", "key")
    budget_id = "budget1"
    url = f"http://example.com/budgets/{budget_id}/accounts/banksync"
    requests_mock.post(url, status_code=200)

    response = actual_api.trigger_all_bank_syncs(budget_id)

    assert response.status_code == HTTPStatus.OK
