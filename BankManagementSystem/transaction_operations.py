
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional, List
from mysql.connector import Error

from database import DatabaseConnection
from account_operations import AccountOperations
from models import Transaction


class TransactionOperations:
    """
    Handles deposit, withdrawal, balance inquiry, and transaction history.
    """

    def __init__(self, db: DatabaseConnection, account_ops: AccountOperations):
        self.db = db
        self.account_ops = account_ops

    # MENU OPTION 3 - Deposit Amount

    def deposit(self) -> None:
        """
        Deposit funds into an existing, active account.
        Updates balance and logs transaction atomically in a single DB commit.
        """
        print("\n" + "=" * 50)
        print("   DEPOSIT AMOUNT")
        print("=" * 50)

        account_number = input("  Enter account number : ").strip().upper()
        if not account_number:
            print("  [ERROR] Account number cannot be empty.")
            return

        account = self.account_ops.get_account(account_number)
        if not account:
            print(f"  [NOT FOUND] Account '{account_number}' does not exist.")
            return

        if account.status == "inactive":
            print(f"  [ERROR] Account '{account_number}' is inactive. Cannot deposit.")
            return

        amount = self._get_valid_amount("Enter deposit amount (Rs. ) : ")
        description = input("  Enter description (optional): ").strip()
        if not description:
            description = "Cash Deposit"

        cursor = None
        try:
            cursor = self.db.get_cursor()

            # 1. Row-level lock: select current balance for update
            cursor.execute(
                "SELECT balance FROM accounts WHERE account_number = %s FOR UPDATE",
                (account_number,)
            )
            row = cursor.fetchone()
            current_balance = Decimal(str(row[0]))
            new_balance = current_balance + amount

            # 2. Update balance
            cursor.execute(
                "UPDATE accounts SET balance = %s WHERE account_number = %s",
                (str(new_balance), account_number)
            )

            # 3. Insert transaction log
            cursor.execute(
                """
                INSERT INTO transactions (account_number, transaction_type, amount, description)
                VALUES (%s, 'deposit', %s, %s)
                """,
                (account_number, str(amount), description)
            )

            # 4. Commit atomic transaction
            self.db.commit()

            print("\n  [OK] Deposit successful!")
            print(f"  -> Account Number : {account_number}")
            print(f"  -> Deposited      : Rs. {amount:,.2f}")
            print(f"  -> New Balance    : Rs. {new_balance:,.2f}")

        except Error as e:
            self.db.rollback()
            print(f"\n  [ERROR] Deposit failed: {e.msg}")

        finally:
            if cursor:
                cursor.close()

    # MENU OPTION 4 - Withdraw Amount
.
    def withdraw(self) -> None:
        """
        Withdraw funds from an existing, active account.
        Checks for sufficient funds, updates balance and records transaction atomically.
        """
        print("\n" + "=" * 50)
        print("   WITHDRAW AMOUNT")
        print("=" * 50)

        account_number = input("  Enter account number : ").strip().upper()
        if not account_number:
            print("  [ERROR] Account number cannot be empty.")
            return

        account = self.account_ops.get_account(account_number)
        if not account:
            print(f"  [NOT FOUND] Account '{account_number}' does not exist.")
            return

        if account.status == "inactive":
            print(f"  [ERROR] Account '{account_number}' is inactive. Cannot withdraw.")
            return

        amount = self._get_valid_amount("Enter withdrawal amount (Rs. ) : ")
        description = input("  Enter description (optional): ").strip()
        if not description:
            description = "Cash Withdrawal"

        cursor = None
        try:
            cursor = self.db.get_cursor()

            # 1. Lock account row to safely inspect and update balance
            cursor.execute(
                "SELECT balance FROM accounts WHERE account_number = %s FOR UPDATE",
                (account_number,)
            )
            row = cursor.fetchone()
            current_balance = Decimal(str(row[0]))

            if amount > current_balance:
                print("\n  [ERROR] Insufficient funds!")
                print(f"  -> Available Balance : Rs. {current_balance:,.2f}")
                print(f"  -> Requested Amount  : Rs. {amount:,.2f}")
                self.db.rollback()
                return

            new_balance = current_balance - amount

            # 2. Update balance
            cursor.execute(
                "UPDATE accounts SET balance = %s WHERE account_number = %s",
                (str(new_balance), account_number)
            )

            # 3. Insert transaction record
            cursor.execute(
                """
                INSERT INTO transactions (account_number, transaction_type, amount, description)
                VALUES (%s, 'withdrawal', %s, %s)
                """,
                (account_number, str(amount), description)
            )

            # 4. Commit atomic transaction
            self.db.commit()

            print("\n  [OK] Withdrawal successful!")
            print(f"  -> Account Number    : {account_number}")
            print(f"  -> Withdrawn Amount  : Rs. {amount:,.2f}")
            print(f"  -> Remaining Balance : Rs. {new_balance:,.2f}")

        except Error as e:
            self.db.rollback()
            print(f"\n  [ERROR] Withdrawal failed: {e.msg}")

        finally:
            if cursor:
                cursor.close()

    # MENU OPTION 5 - Check Balance
    

    def check_balance(self) -> None:
        """
        Retrieve and display the latest live balance directly from MySQL.
        """
        print("\n" + "=" * 50)
        print("   CHECK BALANCE")
        print("=" * 50)

        account_number = input("  Enter account number : ").strip().upper()
        if not account_number:
            print("  [ERROR] Account number cannot be empty.")
            return

        cursor = None
        try:
            cursor = self.db.get_cursor(dictionary=True)
            cursor.execute(
                """
                SELECT account_number, customer_name, balance, status
                FROM accounts
                WHERE account_number = %s
                """,
                (account_number,)
            )
            row = cursor.fetchone()

            if not row:
                print(f"  [NOT FOUND] Account '{account_number}' does not exist.")
                return

            balance = Decimal(str(row["balance"]))
            status_text = "Active" if row["status"] == "active" else "Inactive"

            print("\n  " + "-" * 40)
            print(f"  Account Number : {row['account_number']}")
            print(f"  Customer Name  : {row['customer_name']}")
            print(f"  Current Balance: Rs. {balance:,.2f}")
            print(f"  Account Status : {status_text}")
            print("  " + "-" * 40)

        except Error as e:
            print(f"\n  [ERROR] Failed to check balance: {e.msg}")

        finally:
            if cursor:
                cursor.close()

    # MENU OPTION 6 - View Transactions (History & Filtering)

    def view_transactions(self) -> None:
        """
        Display transactions with newest first.
        Supports filtering by account number and transaction type (deposit/withdrawal).
        """
        print("\n" + "=" * 50)
        print("   TRANSACTION HISTORY")
        print("=" * 50)

        account_number = input("  Enter account number (or press Enter for all): ").strip().upper()
        if account_number:
            acc = self.account_ops.get_account(account_number)
            if not acc:
                print(f"  [NOT FOUND] Account '{account_number}' does not exist.")
                return

        print("\n  Filter by transaction type:")
        print("  [1] All transactions")
        print("  [2] Deposits only")
        print("  [3] Withdrawals only")
        type_choice = input("  Choose filter (1-3, default 1): ").strip()

        txn_type = None
        if type_choice == "2":
            txn_type = "deposit"
        elif type_choice == "3":
            txn_type = "withdrawal"

        cursor = None
        try:
            cursor = self.db.get_cursor(dictionary=True)

            query = (
                "SELECT transaction_id, account_number, transaction_type, amount, "
                "       transaction_date, description "
                "FROM transactions WHERE 1=1 "
            )
            params: list = []

            if account_number:
                query += " AND account_number = %s "
                params.append(account_number)

            if txn_type:
                query += " AND transaction_type = %s "
                params.append(txn_type)

            query += " ORDER BY transaction_date DESC, transaction_id DESC"

            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()

            if not rows:
                print("\n  [INFO] No transactions found matching the criteria.")
                return

            print("\n" + "-" * 80)
            print(f"  {'ID':>6}  {'Type':<12}  {'Amount':>14}  {'Date & Time':<22}  Description")
            print("-" * 80)

            for r in rows:
                txn = Transaction(
                    transaction_id=r["transaction_id"],
                    account_number=r["account_number"],
                    transaction_type=r["transaction_type"],
                    amount=Decimal(str(r["amount"])),
                    transaction_date=r["transaction_date"],
                    description=r["description"]
                )
                print(txn)

            print("-" * 80)
            print(f"  Total records: {len(rows)}")

        except Error as e:
            print(f"\n  [ERROR] Failed to load transactions: {e.msg}")

        finally:
            if cursor:
                cursor.close()

    # Private input-validation helpers

    def _get_valid_amount(self, prompt: str) -> Decimal:
        """
        Validate positive monetary amount (rejects zero, negatives, and invalid formats).
        """
        while True:
            raw = input(f"  {prompt}").strip()
            try:
                amt = Decimal(raw)
                if amt <= Decimal("0"):
                    print("    [ERROR] Amount must be strictly greater than zero.")
                else:
                    return amt.quantize(Decimal("0.01"))
            except InvalidOperation:
                print("    [ERROR] Invalid format. Enter a valid number (e.g., 500 or 1200.50).")
