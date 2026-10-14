"""
main.py - Application entry point and BankManagementSystem class
=================================================================
Responsibility:
  - Display the main menu in a loop.
  - Route user choices to the correct operation class.
  - Start up the database connection and tear it down cleanly on exit.

Stage note:
  Options 3, 4, 5, 6, 8 show a "Coming soon" stub until Stage 4 & 5.
  Option 1, 2, 7 are fully working right now.
"""

import os
import sys

from database import DatabaseConnection
from account_operations import AccountOperations
from transaction_operations import TransactionOperations


# -----------------------------------------------------------------------------
# Helper: clear the console so the menu always appears at the top
# -----------------------------------------------------------------------------
def clear_screen() -> None:
    """Works on both Windows (cls) and Linux/Mac (clear)."""
    os.system("cls" if os.name == "nt" else "clear")


# -----------------------------------------------------------------------------
# BankManagementSystem - the main controller class
# -----------------------------------------------------------------------------

class BankManagementSystem:
    """
    Top-level controller.
    Owns the DatabaseConnection and all operation objects.
    Runs the main menu loop until the user chooses Exit.
    """

    MENU = """
+------------------------------------------+
|      BANK MANAGEMENT SYSTEM              |
|      Educational Banking Simulation      |
+------------------------------------------+
|  [1]  Create Bank Account                |
|  [2]  View Account Details               |
|  [3]  Deposit Amount                     |
|  [4]  Withdraw Amount                    |
|  [5]  Check Balance                      |
|  [6]  View Transaction History           |
|  [7]  Update Customer Details            |
|  [8]  Deactivate Account                 |
|  [9]  Exit                               |
+------------------------------------------+"""

    def __init__(self):
        """Set up the database connection and operation handlers."""
        self.db = DatabaseConnection()
        self.account_ops = None
        self.txn_ops = None

    def start(self) -> None:
        """
        Entry point called by the if __name__ == '__main__' block.
        1. Connect to MySQL.
        2. Create tables if needed.
        3. Run the menu loop.
        4. Close connection on exit.
        """
        clear_screen()
        print("\n  Welcome to Bank Management System")
        print("  Connecting to database...\n")

        # Step 1 - Connect
        if not self.db.connect():
            print("\n  Cannot start without a database connection. Exiting.")
            sys.exit(1)

        # Step 2 - Create tables if first run
        if not self.db.setup_tables():
            print("\n  Database setup failed. Exiting.")
            self.db.close()
            sys.exit(1)

        # Step 3 - Initialize operation classes
        self.account_ops = AccountOperations(self.db)
        self.txn_ops = TransactionOperations(self.db, self.account_ops)

        # Step 4 - Run menu loop
        self._run_menu()

        # Step 5 - Clean shutdown
        self.db.close()

    def _run_menu(self) -> None:
        """
        Display the menu, read user input, and dispatch to the right handler.
        Loops forever until the user picks option 9.
        """
        while True:
            print(self.MENU)
            choice = input("  Enter your choice (1-9): ").strip()

            if choice == "1":
                self.account_ops.create_account()

            elif choice == "2":
                self.account_ops.view_account()

            elif choice == "3":
                self.txn_ops.deposit()

            elif choice == "4":
                self.txn_ops.withdraw()

            elif choice == "5":
                self.txn_ops.check_balance()

            elif choice == "6":
                self.txn_ops.view_transactions()

            elif choice == "7":
                self.account_ops.update_account()

            elif choice == "8":
                self.account_ops.deactivate_account()

            elif choice == "9":
                print("\n  Thank you for using Bank Management System.")
                print("  Closing connection and exiting...\n")
                break

            else:
                print("\n  [ERROR] Invalid choice. Please enter a number between 1 and 9.")

            # Pause so the user can read the output before the menu redraws
            input("\n  Press Enter to continue...")
            clear_screen()


# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    app = BankManagementSystem()
    app.start()
