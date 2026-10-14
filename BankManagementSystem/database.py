"""
database.py — DatabaseConnection class
Responsibility:
  - Read MySQL credentials from environment variables (never from hardcoded values).
  - Connect to the MySQL server.
  - Create the database and tables if they don't already exist.
  - Provide a cursor to other modules for running queries.
  - Close the connection cleanly when the application exits.

Why a class?
  One DatabaseConnection object is created at startup and shared across all
  operation modules. This avoids opening a new connection for every single query,
  which is slow and wasteful.
"""

import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

# Load the .env file so os.getenv() can read our credentials.
# If .env doesn't exist, it silently skips (no crash) — environment variables
# set in the OS directly are also picked up.
load_dotenv()


class DatabaseConnection:
    """
    Manages the MySQL connection lifecycle.

    Usage:
        db = DatabaseConnection()
        db.connect()
        db.setup_tables()
        cursor = db.get_cursor()
        ...
        db.close()
    """

    def __init__(self):
        """Read config from environment variables. No connection is opened yet."""
        self.host     = os.getenv("DB_HOST", "localhost")
        self.port     = int(os.getenv("DB_PORT", 3306))
        self.user     = os.getenv("DB_USER", "root")
        self.password = os.getenv("DB_PASSWORD", "")
        self.db_name  = os.getenv("DB_NAME", "bank_management")

        # These will be set once connect() is called.
        self.connection = None

    

    def connect(self) -> bool:
        """
        Open the MySQL connection.

        Returns True on success, False on failure.
        Prints a helpful message instead of exposing the raw MySQL error
        (which might include the password in some configurations).
        """
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                # autocommit=False means we control commit/rollback manually.
                # This is essential for safe deposit/withdrawal transactions.
                autocommit=False,
            )
            print(f"[DB] Connected to MySQL server at {self.host}:{self.port}")
            return True

        except Error as e:
            # We print the error CODE, not the full message, to avoid leaking
            # connection details like the password.
            print(f"\n[ERROR] Could not connect to MySQL (Error code: {e.errno}).")
            print("  ► Check that MySQL is running.")
            print("  ► Verify your credentials in the .env file.")
            print(f"  ► Host: {self.host}  Port: {self.port}  User: {self.user}\n")
            return False

    def setup_tables(self) -> bool:
        """
        Create the database and both tables if they don't already exist.
        Safe to call multiple times — IF NOT EXISTS prevents duplicate-table errors.

        Returns True on success, False on failure.
        """
        cursor = None
        try:
            cursor = self.connection.cursor()

            # Step 1 — Create database
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{self.db_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            cursor.execute(f"USE `{self.db_name}`")

            # Tell the connector to use this database for ALL future cursors.
            # This removes the need for 'USE db' calls in every operation method.
            self.connection.database = self.db_name

            # Step 2 — Create accounts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    account_number  VARCHAR(12)                  NOT NULL,
                    customer_name   VARCHAR(100)                 NOT NULL,
                    phone           VARCHAR(15)                  NOT NULL,
                    address         VARCHAR(255)                 NOT NULL,
                    balance         DECIMAL(12,2)                NOT NULL DEFAULT 0.00,
                    created_at      DATETIME                     NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    status          ENUM('active', 'inactive')   NOT NULL DEFAULT 'active',
                    CONSTRAINT pk_accounts  PRIMARY KEY (account_number),
                    CONSTRAINT chk_balance  CHECK (balance >= 0.00)
                )
            """)

            # Step 3 — Create transactions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    transaction_id   INT                              NOT NULL AUTO_INCREMENT,
                    account_number   VARCHAR(12)                      NOT NULL,
                    transaction_type ENUM('deposit', 'withdrawal')    NOT NULL,
                    amount           DECIMAL(12,2)                    NOT NULL,
                    transaction_date DATETIME                         NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    description      VARCHAR(255)                     DEFAULT NULL,
                    CONSTRAINT pk_transactions  PRIMARY KEY (transaction_id),
                    CONSTRAINT fk_account       FOREIGN KEY (account_number)
                                                REFERENCES accounts (account_number)
                                                ON DELETE RESTRICT
                                                ON UPDATE CASCADE,
                    CONSTRAINT chk_amount       CHECK (amount > 0.00),
                    INDEX idx_account_number    (account_number),
                    INDEX idx_transaction_date  (transaction_date)
                )
            """)

            self.connection.commit()
            print(f"[DB] Database '{self.db_name}' and tables are ready.")
            return True

        except Error as e:
            print(f"[ERROR] Failed to set up database tables: {e.msg}")
            return False

        finally:
            # Always close the cursor, even if an exception was raised.
            if cursor:
                cursor.close()

    def get_cursor(self, dictionary: bool = False):
        """
        Return a new cursor for running queries.

        Args:
            dictionary: If True, rows are returned as dicts {column: value}
                        instead of plain tuples. Easier to work with by name.

        The caller is responsible for closing the cursor after use.
        """
        if not self.connection or not self.connection.is_connected():
            raise ConnectionError(
                "[ERROR] No active database connection. Call connect() first."
            )
        return self.connection.cursor(dictionary=dictionary)

    def commit(self):
        """Commit the current transaction — saves all pending changes to disk."""
        if self.connection:
            self.connection.commit()

    def rollback(self):
        """
        Roll back the current transaction — undoes all pending changes.
        Called in the except block when a deposit or withdrawal partially fails.
        """
        if self.connection:
            self.connection.rollback()

    def close(self):
        """
        Cleanly close the database connection.
        Called by main.py when the user chooses 'Exit'.
        """
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("[DB] Connection closed. Goodbye!")

if __name__ == "__main__":
    print("=" * 55)
    print("  Bank Management System — Database Connection Test")
    print("=" * 55)

    db = DatabaseConnection()

    if db.connect():
        if db.setup_tables():
            print("\n[OK] All checks passed. Your database is ready.")
        else:
            print("\n[FAIL] Table setup failed. See error above.")
    else:
        print("\n[FAIL] Could not connect to MySQL. See error above.")

    db.close()
