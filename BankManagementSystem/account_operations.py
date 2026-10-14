"""
account_operations.py - AccountOperations class
================================================
Responsibility:
  - Menu Option 1: Create a new bank account
  - Menu Option 2: View account details by account number
  - Menu Option 7: Update customer name, phone, or address
  - Menu Option 8: Deactivate (soft-delete) an account

Design rule:
  All database queries in this file use parameterized placeholders (%s).
  This completely prevents SQL injection attacks.

  NEVER write:  f"SELECT * FROM accounts WHERE account_number = '{acc_no}'"
  ALWAYS write: "SELECT * FROM accounts WHERE account_number = %s", (acc_no,)
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Optional
from mysql.connector import Error

from database import DatabaseConnection
from models import BankAccount


class AccountOperations:
    """
    Handles all account-level operations: create, view, update, deactivate.

    Constructor receives a DatabaseConnection object so this class never
    opens its own connection - one shared connection for the whole app.
    """

    def __init__(self, db: DatabaseConnection):
        self.db = db

    # ==========================================================================
    # MENU OPTION 1 - Create Bank Account
    # ==========================================================================

    def create_account(self) -> None:
        """
        Collect customer details, generate a unique account number, and
        INSERT the new account (plus an opening transaction if balance > 0).

        Uses a database transaction so both the account INSERT and the
        optional opening-deposit INSERT succeed together or not at all.
        """
        print("\n" + "=" * 50)
        print("   CREATE NEW BANK ACCOUNT")
        print("=" * 50)

        # -- Collect and validate input -------------------------------------
        customer_name = self._get_valid_name("Enter customer name       : ")
        phone         = self._get_valid_phone("Enter phone number        : ")
        address       = self._get_valid_address("Enter address             : ")
        opening_bal   = self._get_valid_amount(
            "Enter opening balance (Rs. ) : ", allow_zero=True
        )

        cursor = None
        try:
            cursor = self.db.get_cursor()

            # -- Generate unique account number -----------------------------
            # Strategy: find the highest existing number and add 1.
            # ACC + 9-digit zero-padded number → max: ACC999999999
            cursor.execute(
                "SELECT account_number FROM accounts "
                "ORDER BY account_number DESC LIMIT 1"
            )
            last = cursor.fetchone()

            if last:
                # Extract the numeric part after "ACC" and increment
                last_num     = int(last[0][3:])
                new_num      = last_num + 1
            else:
                new_num = 1  # First account ever

            account_number = f"ACC{new_num:09d}"  # e.g. ACC000000001

            # -- Insert into accounts table ---------------------------------
            cursor.execute(
                """
                INSERT INTO accounts
                    (account_number, customer_name, phone, address, balance, status)
                VALUES
                    (%s, %s, %s, %s, %s, 'active')
                """,
                (account_number, customer_name, phone, address, str(opening_bal))
            )

            # -- If opening balance > 0, record it as a deposit transaction -
            if opening_bal > Decimal("0.00"):
                cursor.execute(
                    """
                    INSERT INTO transactions
                        (account_number, transaction_type, amount, description)
                    VALUES
                        (%s, 'deposit', %s, 'Opening deposit')
                    """,
                    (account_number, str(opening_bal))
                )

            # -- Commit only after BOTH inserts succeed ---------------------
            self.db.commit()

            print(f"\n  [OK] Account created successfully!")
            print(f"  -> Your Account Number : {account_number}")
            print(f"  -> Opening Balance     : Rs. {opening_bal:,.2f}")
            print(f"  -> Status              : Active")
            print("  Keep your account number safe - you'll need it for all operations.")

        except Error as e:
            # If anything went wrong, undo both inserts
            self.db.rollback()
            print(f"\n  [ERROR] Could not create account: {e.msg}")

        finally:
            if cursor:
                cursor.close()

    # ==========================================================================
    # MENU OPTION 2 - View Account Details
    # ==========================================================================

    def view_account(self, account_number: str = None) -> BankAccount | None:
        """
        Fetch and display full account details for a given account number.

        Args:
            account_number: Pre-supplied account number (used internally by
                            other methods). If None, prompts the user.

        Returns:
            BankAccount object if found, or None.
        """
        print("\n" + "=" * 50)
        print("   VIEW ACCOUNT DETAILS")
        print("=" * 50)

        if account_number is None:
            account_number = input("  Enter account number : ").strip().upper()

        if not account_number:
            print("  [ERROR] Account number cannot be empty.")
            return None

        cursor = None
        try:
            # dictionary=True → rows come back as {column: value} dicts
            cursor = self.db.get_cursor(dictionary=True)

            cursor.execute(
                """
                SELECT account_number, customer_name, phone, address,
                       balance, created_at, status
                FROM   accounts
                WHERE  account_number = %s
                """,
                (account_number,)
            )
            row = cursor.fetchone()

            if not row:
                print(f"\n  [NOT FOUND] No account found with number '{account_number}'.")
                print("  -> Double-check the account number and try again.")
                return None

            # Build a BankAccount object from the dict row
            account = BankAccount(
                account_number=row["account_number"],
                customer_name =row["customer_name"],
                phone         =row["phone"],
                address       =row["address"],
                balance       =Decimal(str(row["balance"])),
                created_at    =row["created_at"],
                status        =row["status"],
            )

            # __str__ of BankAccount prints the nicely formatted box
            print(account)
            return account

        except Error as e:
            print(f"\n  [ERROR] Could not fetch account details: {e.msg}")
            return None

        finally:
            if cursor:
                cursor.close()

    # ==========================================================================
    # MENU OPTION 7 - Update Customer Details
    # ==========================================================================

    def update_account(self) -> None:
        """
        Allow the user to update customer_name, phone, or address.
        The account_number, balance, and transaction history are never touched.
        """
        print("\n" + "=" * 50)
        print("   UPDATE CUSTOMER DETAILS")
        print("=" * 50)

        account_number = input("  Enter account number : ").strip().upper()

        # Re-use view_account to check existence and display current details
        account = self.view_account(account_number)
        if account is None:
            return  # view_account already printed the error

        if account.status == "inactive":
            print("\n  [ERROR] Cannot update an inactive account.")
            return

        print("\n  What would you like to update?")
        print("  [1] Customer Name")
        print("  [2] Phone Number")
        print("  [3] Address")
        print("  [4] Cancel - go back to main menu")

        choice = input("\n  Enter choice (1-4): ").strip()

        if choice == "4":
            print("  Update cancelled.")
            return

        update_map = {
            "1": ("customer_name", "Enter new name    : ",
                  self._get_valid_name),
            "2": ("phone",         "Enter new phone   : ",
                  self._get_valid_phone),
            "3": ("address",       "Enter new address : ",
                  self._get_valid_address),
        }

        if choice not in update_map:
            print("  [ERROR] Invalid choice.")
            return

        column, prompt, validator = update_map[choice]
        new_value = validator(prompt)

        cursor = None
        try:
            cursor = self.db.get_cursor()

            # Parameterized UPDATE - column name is from our own dict (safe),
            # value is a %s placeholder (SQL-injection safe).
            cursor.execute(
                f"UPDATE accounts SET {column} = %s WHERE account_number = %s",
                (new_value, account_number)
            )
            self.db.commit()

            print(f"\n  [OK] {column.replace('_', ' ').title()} updated successfully.")
            print(f"  -> New value : {new_value}")

        except Error as e:
            self.db.rollback()
            print(f"\n  [ERROR] Could not update account: {e.msg}")

        finally:
            if cursor:
                cursor.close()

    # ==========================================================================
    # MENU OPTION 8 - Deactivate Account
    # ==========================================================================

    def deactivate_account(self) -> None:
        """
        Soft-delete an account by updating status = 'inactive'.
        Preserves account and transaction records, preventing future deposits/withdrawals.
        """
        print("\n" + "=" * 50)
        print("   DEACTIVATE ACCOUNT")
        print("=" * 50)

        account_number = input("  Enter account number : ").strip().upper()
        if not account_number:
            print("  [ERROR] Account number cannot be empty.")
            return

        account = self.get_account(account_number)
        if not account:
            print(f"  [NOT FOUND] Account '{account_number}' does not exist.")
            return

        if account.status == "inactive":
            print(f"  [INFO] Account '{account_number}' is already deactivated.")
            return

        print(f"\n  Account holder: {account.customer_name}")
        print(f"  Current balance: Rs. {account.balance:,.2f}")
        print("\n  [WARNING] Deactivating will freeze this account.")
        print("  Deposits and withdrawals will no longer be permitted.")
        print("  All transaction history will remain intact.")

        confirm = input("\n  Are you sure you want to deactivate? (yes/no): ").strip().lower()
        if confirm != "yes":
            print("  Deactivation cancelled.")
            return

        cursor = None
        try:
            cursor = self.db.get_cursor()
            cursor.execute(
                "UPDATE accounts SET status = 'inactive' WHERE account_number = %s",
                (account_number,)
            )
            self.db.commit()
            print(f"\n  [OK] Account '{account_number}' has been deactivated successfully.")

        except Error as e:
            self.db.rollback()
            print(f"\n  [ERROR] Failed to deactivate account: {e.msg}")

        finally:
            if cursor:
                cursor.close()

    # ==========================================================================
    # Helper: fetch account without printing (used by transaction operations)
    # ==========================================================================

    def get_account(self, account_number: str) -> BankAccount | None:
        """
        Silently fetch a BankAccount by account number.
        Returns BankAccount or None. Does NOT print anything - callers decide
        how to display the result.
        Used internally by TransactionOperations.
        """
        cursor = None
        try:
            cursor = self.db.get_cursor(dictionary=True)
            cursor.execute(
                """
                SELECT account_number, customer_name, phone, address,
                       balance, created_at, status
                FROM   accounts
                WHERE  account_number = %s
                """,
                (account_number,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return BankAccount(
                account_number=row["account_number"],
                customer_name =row["customer_name"],
                phone         =row["phone"],
                address       =row["address"],
                balance       =Decimal(str(row["balance"])),
                created_at    =row["created_at"],
                status        =row["status"],
            )
        except Error:
            return None
        finally:
            if cursor:
                cursor.close()

    # ==========================================================================
    # Private input-validation helpers
    # ==========================================================================

    def _get_valid_name(self, prompt: str) -> str:
        """
        Keep asking until the user enters a non-empty name
        containing only letters, spaces, dots, and hyphens.
        """
        while True:
            name = input(f"  {prompt}").strip()
            if not name:
                print("    [ERROR] Name cannot be empty. Please try again.")
            elif not re.match(r"^[A-Za-z\s.\-]{2,100}$", name):
                print("    [ERROR] Name must be 2–100 characters, letters only.")
            else:
                return name

    def _get_valid_phone(self, prompt: str) -> str:
        """
        Validate a 10-digit phone number.
        Strips spaces and dashes before checking.
        """
        while True:
            phone = input(f"  {prompt}").strip().replace(" ", "").replace("-", "")
            if not phone.isdigit():
                print("    [ERROR] Phone must contain digits only.")
            elif len(phone) != 10:
                print("    [ERROR] Phone must be exactly 10 digits.")
            else:
                return phone

    def _get_valid_address(self, prompt: str) -> str:
        """Address must be at least 5 characters and not blank."""
        while True:
            address = input(f"  {prompt}").strip()
            if len(address) < 5:
                print("    [ERROR] Address must be at least 5 characters.")
            else:
                return address

    def _get_valid_amount(self, prompt: str, allow_zero: bool = False) -> Decimal:
        """
        Parse and validate a monetary amount.

        Args:
            allow_zero: If True, Rs. 0.00 is accepted (used for opening balance).
                        If False, amount must be strictly positive (deposits/withdrawals).
        """
        while True:
            raw = input(f"  {prompt}").strip()
            try:
                amount = Decimal(raw)
                if allow_zero and amount < Decimal("0"):
                    print("    [ERROR] Amount cannot be negative.")
                elif not allow_zero and amount <= Decimal("0"):
                    print("    [ERROR] Amount must be greater than zero.")
                else:
                    # Round to 2 decimal places - no floating-point surprises
                    return amount.quantize(Decimal("0.01"))
            except InvalidOperation:
                print("    [ERROR] Invalid amount. Enter a number like 500 or 1500.75")
