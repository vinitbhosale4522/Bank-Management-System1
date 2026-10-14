"""
models.py — BankAccount and Transaction data models
=====================================================
Responsibility:
  - Define simple Python dataclasses that mirror the MySQL table rows.
  - Provide clean __str__ methods for displaying data on the console.
  - No database logic lives here — these are pure data containers.

Why dataclasses?
  Python's @dataclass decorator auto-generates __init__, __repr__, and
  comparison methods so we don't have to write boilerplate code manually.
  Perfect for students — less code, same power.
"""

from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# BankAccount — mirrors one row in the `accounts` table
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BankAccount:
    """
    Represents a single bank account record fetched from MySQL.

    Fields match the `accounts` table columns exactly so there is no
    confusion between what Python holds and what the database stores.
    """
    account_number: str
    customer_name:  str
    phone:          str
    address:        str
    balance:        Decimal          # Always Decimal, never float — exact money math
    created_at:     datetime
    status:         str              # 'active' or 'inactive'

    # ── Display helper ────────────────────────────────────────────────────────
    def __str__(self) -> str:
        """
        Pretty-print an account for the console menu.
        Called automatically when you do:  print(account_object)
        """
        status_icon = "[Active]" if self.status == "active" else "[Inactive]"
        separator   = "-" * 50

        return (
            f"\n{separator}\n"
            f"  ACCOUNT DETAILS\n"
            f"{separator}\n"
            f"  Account Number : {self.account_number}\n"
            f"  Customer Name  : {self.customer_name}\n"
            f"  Phone          : {self.phone}\n"
            f"  Address        : {self.address}\n"
            f"  Balance        : Rs. {self.balance:,.2f}\n"
            f"  Opened On      : {self.created_at.strftime('%d %b %Y, %I:%M %p')}\n"
            f"  Status         : {status_icon}\n"
            f"{separator}"
        )


# -----------------------------------------------------------------------------
# Transaction - mirrors one row in the `transactions` table
# -----------------------------------------------------------------------------

@dataclass
class Transaction:
    """
    Represents a single transaction record fetched from MySQL.
    """
    transaction_id:   int
    account_number:   str
    transaction_type: str            # 'deposit' or 'withdrawal'
    amount:           Decimal
    transaction_date: datetime
    description:      Optional[str]  # Can be None if no description was given

    # -- Display helper --------------------------------------------------------
    def __str__(self) -> str:
        """
        Pretty-print a single transaction row.
        """
        type_icon = "[+] Deposit   " if self.transaction_type == "deposit" else "[-] Withdrawal"
        desc      = self.description if self.description else "-"

        return (
            f"  [{self.transaction_id:>6}]  "
            f"{type_icon}  "
            f"Rs. {self.amount:>12,.2f}  "
            f"{self.transaction_date.strftime('%d %b %Y %I:%M %p')}  "
            f"{desc}"
        )
