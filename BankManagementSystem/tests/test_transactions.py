"""
test_transactions.py — Unit and integration tests for transaction operations.
"""

from decimal import Decimal
from account_operations import AccountOperations
from transaction_operations import TransactionOperations


def test_deposit_and_withdrawal_flow(test_db, monkeypatch):
    acc_ops = AccountOperations(test_db)
    txn_ops = TransactionOperations(test_db, acc_ops)

    # 1. Create a fresh active account
    inputs = iter(["Alice Sharma", "9123456789", "45 Park Street, Mumbai", "500.00"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    acc_ops.create_account()

    cursor = test_db.get_cursor(dictionary=True)
    cursor.execute("SELECT account_number FROM accounts WHERE phone = '9123456789'")
    acc_num = cursor.fetchone()["account_number"]
    cursor.close()

    # 2. Deposit 250.50
    inputs = iter([acc_num, "250.50", "Salary bonus"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    txn_ops.deposit()

    acc = acc_ops.get_account(acc_num)
    assert acc.balance == Decimal("750.50")

    # 3. Withdraw 100.00
    inputs = iter([acc_num, "100.00", "Groceries"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    txn_ops.withdraw()

    acc = acc_ops.get_account(acc_num)
    assert acc.balance == Decimal("650.50")

    # 4. Attempt withdrawal exceeding balance (should fail safely)
    inputs = iter([acc_num, "10000.00", "Too much"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    txn_ops.withdraw()

    # Balance must remain unchanged
    acc = acc_ops.get_account(acc_num)
    assert acc.balance == Decimal("650.50")

    # 5. Check transactions table records
    cursor = test_db.get_cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM transactions WHERE account_number = %s ORDER BY transaction_id ASC",
        (acc_num,)
    )
    txns = cursor.fetchall()
    cursor.close()

    # Should have 3 records: Opening deposit (500), Deposit (250.50), Withdrawal (100)
    assert len(txns) == 3
    assert txns[0]["transaction_type"] == "deposit"
    assert Decimal(str(txns[0]["amount"])) == Decimal("500.00")
    assert txns[1]["transaction_type"] == "deposit"
    assert Decimal(str(txns[1]["amount"])) == Decimal("250.50")
    assert txns[2]["transaction_type"] == "withdrawal"
    assert Decimal(str(txns[2]["amount"])) == Decimal("100.00")


def test_inactive_account_rejection(test_db, monkeypatch):
    acc_ops = AccountOperations(test_db)
    txn_ops = TransactionOperations(test_db, acc_ops)

    cursor = test_db.get_cursor(dictionary=True)
    cursor.execute("SELECT account_number FROM accounts WHERE status = 'inactive' LIMIT 1")
    row = cursor.fetchone()
    cursor.close()

    if row:
        acc_num = row["account_number"]
        initial_balance = acc_ops.get_account(acc_num).balance

        # Try to deposit
        inputs = iter([acc_num, "100.00", "Trying on inactive"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        txn_ops.deposit()

        # Balance remains unchanged
        assert acc_ops.get_account(acc_num).balance == initial_balance
