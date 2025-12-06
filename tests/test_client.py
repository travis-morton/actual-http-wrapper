import datetime
from decimal import Decimal
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest

from src.actual_http_wrapper.client import ActualAPI
from src.actual_http_wrapper.models import Account, ExistingTransaction, Payee, Transaction

if TYPE_CHECKING:
    from requests_mock import Mocker


BUDGET_SYNC_ID = "budget1"
HOST = "http://example.com"


@pytest.fixture
def actual_api() -> ActualAPI:
    return ActualAPI(host=HOST, api_key="test_api_key", budget_sync_id=BUDGET_SYNC_ID)


def test_get_accounts(requests_mock: "Mocker", actual_api: ActualAPI):
    account = {"id": "1", "name": "Checking", "offbudget": False, "closed": False}
    requests_mock.get(
        f"{HOST}/budgets/{BUDGET_SYNC_ID}/accounts",
        json={"data": [account]},
    )
    actual_accounts = actual_api.get_accounts()
    assert actual_accounts == [Account(**account)]


def test_get_open_accounts(requests_mock: "Mocker", actual_api: ActualAPI):
    accounts = [
        {"id": "1", "name": "Checking", "offbudget": False, "closed": False},
        {"id": "2", "name": "Savings", "offbudget": False, "closed": True},
    ]
    requests_mock.get(
        f"{HOST}/budgets/{BUDGET_SYNC_ID}/accounts",
        json={"data": accounts},
    )

    open_accounts = actual_api.get_open_accounts()

    expected_accounts = [Account(**accounts[0])]
    assert open_accounts == expected_accounts


def test_import_transactions(actual_api: ActualAPI, requests_mock: "Mocker"):
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
        f"{HOST}/budgets/{BUDGET_SYNC_ID}/accounts/1/transactions/import",
        status_code=200,
    )

    response = actual_api.import_transactions("1", transactions)

    assert response.status_code == HTTPStatus.OK
    assert requests_mock.called
    assert requests_mock.last_request.json() == {  # pyright: ignore[reportOptionalMemberAccess]
        "transactions": [t.model_dump(mode="json") for t in transactions],
    }


def test_get_transactions_for_account_success(requests_mock: "Mocker", actual_api: ActualAPI):
    account_id = "acc1"
    since_date = datetime.date(2024, 1, 1)
    until_date = datetime.date(2024, 2, 1)
    url = f"{HOST}/budgets/{BUDGET_SYNC_ID}/accounts/{account_id}/transactions"
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


def test_get_payees_for_budget(requests_mock: "Mocker", actual_api: ActualAPI):
    url = f"{HOST}/budgets/{BUDGET_SYNC_ID}/payees"
    payees = [
        {"id": "p1", "name": "Payee 1"},
        {"id": "p2", "name": "Payee 2"},
    ]
    requests_mock.get(url, json={"data": payees})

    result = actual_api.get_payees_for_budget()

    assert result == [Payee(**payee) for payee in payees]


def test_get_account_balance(requests_mock: "Mocker", actual_api: ActualAPI):
    account_id = "acc1"
    url = f"{HOST}/budgets/{BUDGET_SYNC_ID}/accounts/{account_id}/balance"
    requests_mock.get(url, json={"data": 12345})

    balance = actual_api.get_account_balance(account_id)

    assert balance == Decimal("123.45")


def test_trigger_all_bank_syncs(requests_mock: "Mocker", actual_api: ActualAPI):
    budget_id = BUDGET_SYNC_ID
    url = f"{HOST}/budgets/{budget_id}/accounts/banksync"
    requests_mock.post(url, status_code=200)

    response = actual_api.trigger_all_bank_syncs()

    assert response.status_code == HTTPStatus.OK


def test_create_payee_for_budget(requests_mock: "Mocker", actual_api: ActualAPI):
    url = f"{HOST}/budgets/{BUDGET_SYNC_ID}/payees"
    payee = Payee(name="New Payee")
    response_data = {"id": "p123"}
    requests_mock.post(url, json={"data": response_data})

    created_payee = actual_api.create_payee_for_budget(payee)

    assert created_payee == Payee(**response_data)
    assert requests_mock.last_request.json() == {  # pyright: ignore[reportOptionalMemberAccess]
        "payee": {"name": "New Payee"},
    }


def test_ensure_payee_exists_creates_new(requests_mock: "Mocker", actual_api: ActualAPI):
    budget_id = BUDGET_SYNC_ID
    payee_name = "Unique Payee"
    get_url = f"{HOST}/budgets/{budget_id}/payees"
    post_url = f"{HOST}/budgets/{budget_id}/payees"

    requests_mock.get(get_url, json={"data": []})

    response_data = {"id": "p456"}
    requests_mock.post(post_url, json={"data": response_data})

    ensured_payee = actual_api.ensure_payee_exists(payee_name)

    assert ensured_payee == Payee(name=payee_name, id="p456")
    assert requests_mock.last_request.json() == {  # pyright: ignore[reportOptionalMemberAccess]
        "payee": {"name": payee_name},
    }


def test_ensure_payee_exists_returns_existing(requests_mock: "Mocker", actual_api: ActualAPI):
    budget_id = BUDGET_SYNC_ID
    payee_name = "Existing Payee"
    get_url = f"{HOST}/budgets/{budget_id}/payees"
    existing_payee_data = {"id": "p789", "name": payee_name}
    requests_mock.get(get_url, json={"data": [existing_payee_data]})

    ensured_payee = actual_api.ensure_payee_exists(payee_name)
    assert ensured_payee == Payee(**existing_payee_data)
