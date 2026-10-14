"""
test_accounts.py — Unit and integration tests for account operations.
"""

from decimal import Decimal
from account_operations import AccountOperations


def test_account_creation_and_view(test_db, monkeypatch):
    ops = AccountOperations(test_db)

    # Mock inputs: customer_name, phone, address, opening_bal
    inputs = iter(["Vinit Bhosale", "9876543210", "123 MG Road, Pune", "1000.00"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    ops.create_account()

    cursor = test_db.get_cursor(dictionary=True)
    cursor.execute("SELECT * FROM accounts WHERE phone = '9876543210'")
    row = cursor.fetchone()
    cursor.close()

    assert row is not None
    assert row["customer_name"] == "Vinit Bhosale"
    assert Decimal(str(row["balance"])) == Decimal("1000.00")
    assert row["status"] == "active"

    # Test silent get_account
    acc = ops.get_account(row["account_number"])
    assert acc is not None
    assert acc.phone == "9876543210"


def test_update_customer_details(test_db, monkeypatch):
    ops = AccountOperations(test_db)
    cursor = test_db.get_cursor(dictionary=True)
    cursor.execute("SELECT account_number FROM accounts LIMIT 1")
    acc_num = cursor.fetchone()["account_number"]
    cursor.close()

    # Inputs: account_number, choice [1 = Name], new name
    inputs = iter([acc_num, "1", "Vinit B. Updated"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    ops.update_account()

    acc = ops.get_account(acc_num)
    assert acc.customer_name == "Vinit B. Updated"


def test_deactivate_account(test_db, monkeypatch):
    ops = AccountOperations(test_db)
    cursor = test_db.get_cursor(dictionary=True)
    cursor.execute("SELECT account_number FROM accounts LIMIT 1")
    acc_num = cursor.fetchone()["account_number"]
    cursor.close()

    # Inputs: account_number, confirm ("yes")
    inputs = iter([acc_num, "yes"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    ops.deactivate_account()

    acc = ops.get_account(acc_num)
    assert acc.status == "inactive"
