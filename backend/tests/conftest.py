import pytest

from app import db


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """모든 테스트가 실제 DB 대신 테스트마다 새로 만든 임시 DB를 쓰게 한다."""
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
