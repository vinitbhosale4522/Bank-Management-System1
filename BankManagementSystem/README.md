# Bank Management System (Python, Flask & MySQL)

A clean, beginner-friendly, educational **Bank Management Web Application** and **Console System** built with **Python**, **Flask**, **MySQL**, **HTML5**, and **CSS3**.

---

##  Project Overview
This project provides both an interactive **Web Portal** and a **Console Interface** sharing the same robust MySQL backend:
- **Clean Frontend**: Professional white background canvas with navy-blue headings, cards, and buttons.
- **Relational MySQL Database**: Normalized tables with foreign key constraints, positive amount checks, and composite indexes.
- **ACID Financial Transactions**: Atomic commits and rollbacks ensuring balance changes and transaction logs succeed or fail together.
- **Concurrency & Overdraft Protection**: Row-level locking (`SELECT ... FOR UPDATE`) preventing race conditions and overdrafts.
- **Exact Monetary Precision**: Python's `Decimal` paired with MySQL's `DECIMAL(12,2)` avoiding floating-point rounding errors.
- **Security**: Strictly parameterized SQL queries (`%s`) preventing SQL injection and environment variables via `.env`.
- **Soft-Delete Architecture**: Inactive accounts are frozen while 100% preserving historical audit records.

---

##  Technologies Used
- **Python 3.9+** (Tested on Python 3.9 & 3.11)
- **Flask 3.0.3** (Lightweight WSGI web framework)
- **MySQL 8.0+**
- **mysql-connector-python** (Official MySQL driver)
- **HTML5 & CSS3** (Responsive, no heavy external dependencies)
- **pytest** (Automated unit and integration testing)

---

##  Project Structure
```text
BankManagementSystem/
│
├── app.py                      # Flask Web Application entry point (All 9 routes)
├── main.py                     # Console Interface entry point
├── database.py                 # MySQL DatabaseConnection class & table schema init
├── models.py                   # BankAccount & Transaction data classes
├── account_operations.py       # Core account logic (shared)
├── transaction_operations.py   # Core financial logic (shared)
├── schema.sql                  # MySQL DDL definition (tables, constraints, indexes)
├── requirements.txt            # Project dependencies
├── .env                        # Local database credentials (excluded from git)
├── .env.example                # Template for environment configuration
├── .gitignore                  # Git ignore rules
│
├── static/
│   └── style.css               # Clean styling: white background, navy-blue headers & buttons
│
├── templates/
│   ├── base.html               # Base layout with navbar and flash messages
│   ├── dashboard.html          # Feature 9: Central banking dashboard with feature cards
│   ├── create_account.html     # Feature 1: Register customer form
│   ├── view_account.html       # Feature 2: Account lookup & details table
│   ├── deposit.html            # Feature 3: Deposit amount form
│   ├── withdraw.html           # Feature 4: Withdrawal form with balance safety
│   ├── check_balance.html      # Feature 5: Fast live balance inquiry
│   ├── transactions.html       # Feature 6: Filterable transaction history table
│   ├── update_details.html     # Feature 7: Edit customer name, phone, or address
│   └── deactivate.html         # Feature 8: Confirmation form to freeze account
│
└── tests/
    ├── conftest.py             # Isolated test database fixture (bank_management_test)
    ├── test_accounts.py        # Account lifecycle tests
    └── test_transactions.py    # Deposit/withdrawal/concurrency tests
```

---

##  Setup & How to Run

### 1. Install Dependencies
```powershell
cd d:\bank\BankManagementSystem
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Ensure your `.env` contains your MySQL credentials:
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_actual_password
DB_NAME=bank_management
TEST_DB_NAME=bank_management_test
```

### 3. Run the Web Application
```powershell
python app.py
```
Open your browser and navigate to:
 **`http://127.0.0.1:5000`**

### 4. Run the Console Version (Optional)
```powershell
python main.py
```

### 5. Run Automated Tests
```powershell
python -m pytest tests/ -v
```

---

##  The Nine Features Explained

1. **Create Bank Account** (`/account/create`): Validates customer name (2-100 chars), phone (10 digits), address, and opening balance (>= 0). Auto-generates unique sequential IDs (`ACC000000001`).
2. **View Account Details** (`/account/view`): Displays account details in a clean responsive table.
3. **Deposit Amount** (`/deposit`): Credits funds to active accounts with atomic transaction logging.
4. **Withdraw Amount** (`/withdraw`): Prevents withdrawals exceeding current balance with row-locking (`FOR UPDATE`).
5. **Check Balance** (`/balance`): Real-time balance inquiry queried directly from MySQL.
6. **Transaction History** (`/transactions`): Filterable ledger supporting account ID and transaction type (`deposit`/`withdrawal`).
7. **Update Customer Details** (`/account/update`): Modifies name, phone, or address without touching balances or history.
8. **Deactivate Account** (`/account/deactivate`): Soft-deletes account to freeze transactions while preserving historical records.
9. **Dashboard / Navigation** (`/`): Centralized hub with quick navigation links and feature cards.
