import os

import pytest
from sqlalchemy import text

from app.core.database import engine


def test_database_connection():
    if not os.getenv("DB_HOST"):
        pytest.skip("Configure backend/.env to run the PostgreSQL connection test")

    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        assert result.scalar() == 1
