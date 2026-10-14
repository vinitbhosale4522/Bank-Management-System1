"""
Test suite configuration and fixtures for Bank Management System.
Uses a separate test database: bank_management_test.
Never touches or modifies production data.
"""

import os
import pytest
from database import DatabaseConnection


@pytest.fixture(scope="session")
def test_db():
    """
    Sets up and yields a dedicated test database connection.
    Drops test tables before and after test session to maintain clean state.
    """
    os.environ["DB_NAME"] = os.getenv("TEST_DB_NAME", "bank_management_test")
    db = DatabaseConnection()
    assert db.connect(), "Failed to connect to MySQL for testing"
    assert db.setup_tables(), "Failed to setup tables in test database"

    yield db

    # Teardown
    cursor = db.get_cursor()
    cursor.execute("DROP DATABASE IF EXISTS bank_management_test")
    db.commit()
    cursor.close()
    db.close()
