"""분석 결과를 SQLite에 저장/조회한다.

DB 파일 위치는 DB_PATH 환경변수로 바꿀 수 있다 (기본: backend/data/analyses.db).
"""

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.schemas import AnalysisResponse, AnalysisSummary

_DEFAULT_PATH = Path(__file__).resolve().parents[1] / "data" / "analyses.db"


def _db_path() -> Path:
    return Path(os.environ.get("DB_PATH") or _DEFAULT_PATH)


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row  # 조회 결과를 row["url"]처럼 열 이름으로 꺼낼 수 있게
    return conn


def init_db() -> None:
    """테이블이 없으면 만든다. 이미 있으면 아무 일도 하지 않는다."""
    conn = _connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analyses (
                id          TEXT PRIMARY KEY,
                url         TEXT NOT NULL,
                verdict     TEXT,
                created_at  TEXT NOT NULL,
                client_id   TEXT,
                is_public   INTEGER NOT NULL DEFAULT 0,
                result_json TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def save_analysis(result: AnalysisResponse, client_id: str | None) -> None:
    """client_id는 응답(result_json)에 넣지 않고 별도 열에만 저장한다."""
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO analyses (id, url, verdict, created_at, client_id, is_public, result_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.id,
                result.url,
                result.verdict,
                datetime.now(timezone.utc).isoformat(),
                client_id,
                int(result.is_public),
                result.model_dump_json(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_analysis(analysis_id: str, client_id: str | None) -> AnalysisResponse | None:
    """공개 결과이거나 요청한 브라우저가 만든 결과만 반환한다. 아니면 None."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT result_json FROM analyses WHERE id = ? AND (is_public = 1 OR client_id = ?)",
            (analysis_id, client_id),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None
    return AnalysisResponse.model_validate_json(row["result_json"])


def list_analyses(limit: int, client_id: str | None = None) -> list[AnalysisSummary]:
    """client_id가 있으면 그 브라우저의 기록을, 없으면 공개 기록을 최근 순으로 반환한다."""
    if client_id is None:
        where, params = "is_public = 1", ()
    else:
        where, params = "client_id = ?", (client_id,)

    conn = _connect()
    try:
        rows = conn.execute(
            f"SELECT id, url, verdict, created_at FROM analyses WHERE {where} "
            # 저장 시각이 같으면(빠르게 연달아 저장) 나중에 저장된 행(rowid가 큰 쪽)을 앞에
            "ORDER BY created_at DESC, rowid DESC LIMIT ?",
            (*params, limit),
        ).fetchall()
    finally:
        conn.close()

    return [
        AnalysisSummary(
            id=row["id"], url=row["url"], verdict=row["verdict"], created_at=row["created_at"]
        )
        for row in rows
    ]
