"""
app.py — Flask Web Application for Bank Management System
===========================================================
Features:
  1. Create Bank Account
  2. View Account Details
  3. Deposit Amount
  4. Withdraw Amount
  5. Check Balance
  6. View Transaction History (Filterable)
  7. Update Customer Details
  8. Deactivate Account
  9. Dashboard / Exit Navigation

Design:
  - Uses existing DatabaseConnection, models, and real MySQL records.
  - Parameterized queries (%s) preventing SQL injection.
  - Decimal monetary precision matching DECIMAL(12,2).
  - Row locking (FOR UPDATE) & atomic commits/rollbacks for financial integrity.
"""

from __future__ import annotations

import os
import re
from decimal import Decimal, InvalidOperation
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from mysql.connector import Error

from database import DatabaseConnection

app = Flask(__name__)
# Secret key for flash messaging sessions
app.secret_key = os.getenv("FLASK_SECRET_KEY", "bank_super_secret_dev_key_2026")

# Shared Database Connection instance
db = DatabaseConnection()


def init_db():
    """Ensure database connection and table setup on startup."""
    if db.connect():
        db.setup_tables()
    else:
        print("[CRITICAL] Could not establish connection to MySQL on Flask launch.")


init_db()


# ═════════════════════════════════════════════════════════════════════════════
# 9. DASHBOARD / HOME (Feature 9)
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/")
def dashboard():
    """Renders the main banking operations dashboard."""
    return render_template("dashboard.html")


# ═════════════════════════════════════════════════════════════════════════════
# 1. CREATE BANK ACCOUNT (Feature 1)
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/account/create", methods=["GET", "POST"])
def create_account():
    if request.method == "POST":
        customer_name = request.form.get("customer_name", "").strip()
        phone = request.form.get("phone", "").strip().replace(" ", "").replace("-", "")
        address = request.form.get("address", "").strip()
        opening_balance_raw = request.form.get("opening_balance", "0.00").strip()

        # Validation
        if not re.match(r"^[A-Za-z\s.\-]{2,100}$", customer_name):
            flash("Customer Name must be 2-100 characters and contain letters only.", "error")
            return render_template("create_account.html")

        if not (phone.isdigit() and len(phone) == 10):
            flash("Phone Number must be exactly 10 digits.", "error")
            return render_template("create_account.html")

        if len(address) < 5:
            flash("Address must be at least 5 characters long.", "error")
            return render_template("create_account.html")

        try:
            opening_balance = Decimal(opening_balance_raw).quantize(Decimal("0.01"))
            if opening_balance < Decimal("0.00"):
                flash("Opening balance cannot be negative.", "error")
                return render_template("create_account.html")
        except InvalidOperation:
            flash("Invalid opening balance format.", "error")
            return render_template("create_account.html")

        cursor = None
        try:
            cursor = db.get_cursor()

            # Generate Next Account Number
            cursor.execute("SELECT account_number FROM accounts ORDER BY account_number DESC LIMIT 1")
            last_row = cursor.fetchone()
            if last_row:
                last_num = int(last_row[0][3:])
                new_acc_num = f"ACC{last_num + 1:09d}"
            else:
                new_acc_num = "ACC000000001"

            # Insert Account
            cursor.execute(
                """
                INSERT INTO accounts (account_number, customer_name, phone, address, balance, status)
                VALUES (%s, %s, %s, %s, %s, 'active')
                """,
                (new_acc_num, customer_name, phone, address, str(opening_balance))
            )

            # Insert Opening Deposit Transaction if balance > 0
            if opening_balance > Decimal("0.00"):
                cursor.execute(
                    """
                    INSERT INTO transactions (account_number, transaction_type, amount, description)
                    VALUES (%s, 'deposit', %s, 'Opening deposit')
                    """,
                    (new_acc_num, str(opening_balance))
                )

            db.commit()
            flash(f"Account {new_acc_num} created successfully for {customer_name} with balance Rs. {opening_balance:,.2f}!", "success")
            return redirect(url_for("view_account", account_number=new_acc_num))

        except Error as e:
            db.rollback()
            flash(f"Database error while creating account: {e.msg}", "error")
        finally:
            if cursor:
                cursor.close()

    return render_template("create_account.html")


# ═════════════════════════════════════════════════════════════════════════════
# 2. VIEW ACCOUNT DETAILS (Feature 2)
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/account/view")
def view_account():
    account_number = request.args.get("account_number", "").strip().upper()
    account = None

    if account_number:
        cursor = None
        try:
            cursor = db.get_cursor(dictionary=True)
            cursor.execute(
                """
                SELECT account_number, customer_name, phone, address, balance, created_at, status
                FROM accounts WHERE account_number = %s
                """,
                (account_number,)
            )
            account = cursor.fetchone()
            if not account:
                flash(f"No account found matching '{account_number}'.", "error")
        except Error as e:
            flash(f"Error fetching account: {e.msg}", "error")
        finally:
            if cursor:
                cursor.close()

    return render_template("view_account.html", account_number=account_number, account=account)


# ═════════════════════════════════════════════════════════════════════════════
# 3. DEPOSIT AMOUNT (Feature 3)
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/deposit", methods=["GET", "POST"])
def deposit():
    account_number = request.args.get("account_number", "").strip().upper()

    if request.method == "POST":
        account_number = request.form.get("account_number", "").strip().upper()
        amount_raw = request.form.get("amount", "").strip()
        description = request.form.get("description", "").strip() or "Cash Deposit"

        try:
            amount = Decimal(amount_raw).quantize(Decimal("0.01"))
            if amount <= Decimal("0.00"):
                flash("Deposit amount must be strictly greater than 0.", "error")
                return render_template("deposit.html", account_number=account_number)
        except InvalidOperation:
            flash("Invalid amount format. Please enter a valid number.", "error")
            return render_template("deposit.html", account_number=account_number)

        cursor = None
        try:
            cursor = db.get_cursor(dictionary=True)

            # Check and lock account row
            cursor.execute(
                "SELECT balance, status, customer_name FROM accounts WHERE account_number = %s FOR UPDATE",
                (account_number,)
            )
            row = cursor.fetchone()

            if not row:
                flash(f"Account '{account_number}' does not exist.", "error")
                return render_template("deposit.html", account_number=account_number)

            if row["status"] == "inactive":
                flash(f"Account '{account_number}' is inactive. Cannot deposit funds.", "error")
                return render_template("deposit.html", account_number=account_number)

            current_balance = Decimal(str(row["balance"]))
            new_balance = current_balance + amount

            # Update balance
            cursor.execute(
                "UPDATE accounts SET balance = %s WHERE account_number = %s",
                (str(new_balance), account_number)
            )

            # Record transaction
            cursor.execute(
                """
                INSERT INTO transactions (account_number, transaction_type, amount, description)
                VALUES (%s, 'deposit', %s, %s)
                """,
                (account_number, str(amount), description)
            )

            db.commit()
            flash(f"Successfully deposited Rs. {amount:,.2f} into {account_number}. New Balance: Rs. {new_balance:,.2f}.", "success")
            return redirect(url_for("view_account", account_number=account_number))

        except Error as e:
            db.rollback()
            flash(f"Transaction failed: {e.msg}", "error")
        finally:
            if cursor:
                cursor.close()

    return render_template("deposit.html", account_number=account_number)


# ═════════════════════════════════════════════════════════════════════════════
# 4. WITHDRAW AMOUNT (Feature 4)
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/withdraw", methods=["GET", "POST"])
def withdraw():
    account_number = request.args.get("account_number", "").strip().upper()

    if request.method == "POST":
        account_number = request.form.get("account_number", "").strip().upper()
        amount_raw = request.form.get("amount", "").strip()
        description = request.form.get("description", "").strip() or "Cash Withdrawal"

        try:
            amount = Decimal(amount_raw).quantize(Decimal("0.01"))
            if amount <= Decimal("0.00"):
                flash("Withdrawal amount must be strictly greater than 0.", "error")
                return render_template("withdraw.html", account_number=account_number)
        except InvalidOperation:
            flash("Invalid amount format. Please enter a valid number.", "error")
            return render_template("withdraw.html", account_number=account_number)

        cursor = None
        try:
            cursor = db.get_cursor(dictionary=True)

            cursor.execute(
                "SELECT balance, status, customer_name FROM accounts WHERE account_number = %s FOR UPDATE",
                (account_number,)
            )
            row = cursor.fetchone()

            if not row:
                flash(f"Account '{account_number}' does not exist.", "error")
                return render_template("withdraw.html", account_number=account_number)

            if row["status"] == "inactive":
                flash(f"Account '{account_number}' is inactive. Cannot withdraw funds.", "error")
                return render_template("withdraw.html", account_number=account_number)

            current_balance = Decimal(str(row["balance"]))

            if amount > current_balance:
                flash(f"Insufficient funds! Available balance is Rs. {current_balance:,.2f}.", "error")
                return render_template("withdraw.html", account_number=account_number)

            new_balance = current_balance - amount

            # Update balance
            cursor.execute(
                "UPDATE accounts SET balance = %s WHERE account_number = %s",
                (str(new_balance), account_number)
            )

            # Record transaction
            cursor.execute(
                """
                INSERT INTO transactions (account_number, transaction_type, amount, description)
                VALUES (%s, 'withdrawal', %s, %s)
                """,
                (account_number, str(amount), description)
            )

            db.commit()
            flash(f"Successfully withdrew Rs. {amount:,.2f} from {account_number}. Remaining Balance: Rs. {new_balance:,.2f}.", "success")
            return redirect(url_for("view_account", account_number=account_number))

        except Error as e:
            db.rollback()
            flash(f"Withdrawal failed: {e.msg}", "error")
        finally:
            if cursor:
                cursor.close()

    return render_template("withdraw.html", account_number=account_number)


# ═════════════════════════════════════════════════════════════════════════════
# 5. CHECK BALANCE (Feature 5)
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/balance", methods=["GET", "POST"])
def check_balance():
    result = None
    account_number = request.args.get("account_number", "").strip().upper()

    if request.method == "POST":
        account_number = request.form.get("account_number", "").strip().upper()

    if account_number:
        cursor = None
        try:
            cursor = db.get_cursor(dictionary=True)
            cursor.execute(
                "SELECT account_number, customer_name, balance, status FROM accounts WHERE account_number = %s",
                (account_number,)
            )
            result = cursor.fetchone()
            if not result:
                flash(f"Account '{account_number}' not found.", "error")
        except Error as e:
            flash(f"Database query error: {e.msg}", "error")
        finally:
            if cursor:
                cursor.close()

    return render_template("check_balance.html", account_number=account_number, result=result)


# ═════════════════════════════════════════════════════════════════════════════
# 6. VIEW TRANSACTIONS (Feature 6)
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/transactions")
def transactions():
    account_number = request.args.get("account_number", "").strip().upper()
    txn_type = request.args.get("type", "").strip().lower()

    rows = []
    cursor = None
    try:
        cursor = db.get_cursor(dictionary=True)

        query = (
            "SELECT transaction_id, account_number, transaction_type, amount, transaction_date, description "
            "FROM transactions WHERE 1=1 "
        )
        params = []

        if account_number:
            query += " AND account_number = %s "
            params.append(account_number)

        if txn_type in ("deposit", "withdrawal"):
            query += " AND transaction_type = %s "
            params.append(txn_type)

        query += " ORDER BY transaction_date DESC, transaction_id DESC"

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()

    except Error as e:
        flash(f"Error retrieving transactions: {e.msg}", "error")
    finally:
        if cursor:
            cursor.close()

    return render_template("transactions.html", rows=rows, account_number=account_number, txn_type=txn_type)


# ═════════════════════════════════════════════════════════════════════════════
# 7. UPDATE CUSTOMER DETAILS (Feature 7)
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/account/update", methods=["GET", "POST"])
def update_details():
    account_number = request.args.get("account_number", "").strip().upper()

    if request.method == "POST":
        account_number = request.form.get("account_number", "").strip().upper()
        field_name = request.form.get("field_name", "").strip()
        new_value = request.form.get("new_value", "").strip()

        if field_name not in ("customer_name", "phone", "address"):
            flash("Invalid field selected for update.", "error")
            return render_template("update_details.html", account_number=account_number)

        # Validate input
        if field_name == "customer_name":
            if not re.match(r"^[A-Za-z\s.\-]{2,100}$", new_value):
                flash("Customer Name must be 2-100 characters and contain letters only.", "error")
                return render_template("update_details.html", account_number=account_number)

        elif field_name == "phone":
            cleaned = new_value.replace(" ", "").replace("-", "")
            if not (cleaned.isdigit() and len(cleaned) == 10):
                flash("Phone must be exactly 10 digits.", "error")
                return render_template("update_details.html", account_number=account_number)
            new_value = cleaned

        elif field_name == "address":
            if len(new_value) < 5:
                flash("Address must be at least 5 characters.", "error")
                return render_template("update_details.html", account_number=account_number)

        cursor = None
        try:
            cursor = db.get_cursor(dictionary=True)
            cursor.execute("SELECT status FROM accounts WHERE account_number = %s", (account_number,))
            row = cursor.fetchone()

            if not row:
                flash(f"Account '{account_number}' does not exist.", "error")
                return render_template("update_details.html", account_number=account_number)

            if row["status"] == "inactive":
                flash(f"Cannot update details for an inactive account.", "error")
                return render_template("update_details.html", account_number=account_number)

            cursor.execute(
                f"UPDATE accounts SET {field_name} = %s WHERE account_number = %s",
                (new_value, account_number)
            )
            db.commit()
            flash(f"Successfully updated {field_name.replace('_', ' ').title()} for {account_number}!", "success")
            return redirect(url_for("view_account", account_number=account_number))

        except Error as e:
            db.rollback()
            flash(f"Update failed: {e.msg}", "error")
        finally:
            if cursor:
                cursor.close()

    return render_template("update_details.html", account_number=account_number)


# ═════════════════════════════════════════════════════════════════════════════
# 8. DEACTIVATE ACCOUNT (Feature 8)
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/account/deactivate", methods=["GET", "POST"])
def deactivate():
    account_number = request.args.get("account_number", "").strip().upper()

    if request.method == "POST":
        account_number = request.form.get("account_number", "").strip().upper()
        confirm = request.form.get("confirm_checkbox")

        if confirm != "yes":
            flash("Please check the confirmation box to proceed with deactivation.", "error")
            return render_template("deactivate.html", account_number=account_number)

        cursor = None
        try:
            cursor = db.get_cursor(dictionary=True)
            cursor.execute("SELECT status, customer_name FROM accounts WHERE account_number = %s", (account_number,))
            row = cursor.fetchone()

            if not row:
                flash(f"Account '{account_number}' does not exist.", "error")
                return render_template("deactivate.html", account_number=account_number)

            if row["status"] == "inactive":
                flash(f"Account '{account_number}' is already deactivated.", "info")
                return redirect(url_for("view_account", account_number=account_number))

            cursor.execute("UPDATE accounts SET status = 'inactive' WHERE account_number = %s", (account_number,))
            db.commit()

            flash(f"Account '{account_number}' ({row['customer_name']}) has been successfully deactivated.", "success")
            return redirect(url_for("view_account", account_number=account_number))

        except Error as e:
            db.rollback()
            flash(f"Deactivation failed: {e.msg}", "error")
        finally:
            if cursor:
                cursor.close()

    return render_template("deactivate.html", account_number=account_number)


# ═════════════════════════════════════════════════════════════════════════════
# Application Entry Point
# ═════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n  =======================================================")
    print("    Bank Management System Web Server (Flask + MySQL)    ")
    print("    Running on: http://127.0.0.1:5000                   ")
    print("  =======================================================\n")
    app.run(host="127.0.0.1", port=5000, debug=True)
