import logging
import secrets
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

from app.schemas import AnalysisResponse, AnalysisSummary, ReportResponse

logger = logging.getLogger(__name__)

_DEFAULT_PATH = Path(__file__).resolve().parents[1] / "data" / "analyses.db"


def _database_url() -> str | None:
    return os.environ.get("DATABASE_URL") or None


def _db_path() -> Path:
    return Path(os.environ.get("DB_PATH") or _DEFAULT_PATH)


def describe() -> str:
    url = _database_url()
    if url:
        parts = urlsplit(url)
        return f"PostgreSQL ({parts.hostname}{parts.path})"
    return f"SQLite ({_db_path()})"


@contextmanager
def _connect():
    url = _database_url()
    if url:
        import psycopg
        from psycopg.rows import dict_row

        conn = psycopg.connect(url, row_factory=dict_row, connect_timeout=10)
        placeholder = "%s"
    else:
        path = _db_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row 
        placeholder = "?"
    try:
        yield conn, placeholder
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    seq_column = "seq BIGSERIAL," if _database_url() else ""
    with _connect() as (conn, _):
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS analyses (
                {seq_column}
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
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_analyses_client ON analyses (client_id, created_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_analyses_public ON analyses (is_public, created_at)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                analysis_id TEXT PRIMARY KEY,
                created_at  TEXT NOT NULL,
                report_json TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS owners (
                analysis_id TEXT PRIMARY KEY,
                masked_name TEXT,
                secret_hash TEXT
            )
            """
        )

        columns = (
            {r["name"] for r in conn.execute("PRAGMA table_info(owners)").fetchall()}
            if not _database_url()
            else {r["column_name"] for r in conn.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'owners'").fetchall()}
        )
        if "name_hash" not in columns:
            conn.execute("ALTER TABLE owners ADD COLUMN name_hash TEXT")

        # 본인 확인 실패 횟수. 예전에는 서버 메모리에만 있어 재시작하면 잠금이 풀렸다 (QA)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS owner_failures (
                analysis_id TEXT PRIMARY KEY,
                count       INTEGER NOT NULL,
                first_at    DOUBLE PRECISION NOT NULL
            )
            """
        )

        # 결과 화면의 '이 판정이 틀렸나요?' 신고. 자동으로 반영하지 않고 사람이 검토한다 (status)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id          TEXT PRIMARY KEY,
                analysis_id TEXT NOT NULL,
                client_id   TEXT NOT NULL,
                url         TEXT NOT NULL,
                verdict     TEXT,
                claim       TEXT NOT NULL,
                comment     TEXT,
                status      TEXT NOT NULL DEFAULT 'pending',
                created_at  TEXT NOT NULL,
                reviewed_at TEXT,
                review_note TEXT,
                UNIQUE (analysis_id, client_id)
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_status ON feedback (status, created_at)")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS shares (
                token       TEXT PRIMARY KEY,
                analysis_id TEXT NOT NULL UNIQUE,
                created_at  TEXT NOT NULL
            )
            """
        )


def save_analysis(result: AnalysisResponse, client_id: str | None, owner: tuple | None = None) -> None:
    """분석 결과와 본인 확인 정보를 한 트랜잭션으로 저장한다 (둘 중 하나만 저장되는 일이 없게)."""
    with _connect() as (conn, p):
        if owner is not None:
            masked_name, secret_hash, name_hash = owner
        conn.execute(
            f"""
            INSERT INTO analyses (id, url, verdict, created_at, client_id, is_public, result_json)
            VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p})
            """,
            (
                result.id,
                result.url,
                result.verdict,
                datetime.now(timezone.utc).isoformat(),
                client_id,
                int(result.is_public),
                result.model_dump_json(exclude=VIEW_ONLY_FIELDS),
            ),
        )
        if owner is not None:
            conn.execute(
                f"INSERT INTO owners (analysis_id, masked_name, secret_hash, name_hash) VALUES ({p}, {p}, {p}, {p})",
                (result.id, masked_name, secret_hash, name_hash),
            )


def get_analysis(analysis_id: str, client_id: str | None) -> AnalysisResponse | None:
    with _connect() as (conn, p):
        row = conn.execute(
            f"SELECT result_json FROM analyses WHERE id = {p} AND (is_public = 1 OR client_id = {p})",
            (analysis_id, client_id),
        ).fetchone()

    if row is None:
        return None
    return AnalysisResponse.model_validate_json(row["result_json"])

VIEW_ONLY_FIELDS = {"viewer", "share_token", "saved"}


def get_analysis_access(analysis_id: str, client_id: str | None):
    with _connect() as (conn, p):
        row = conn.execute(
            f"SELECT result_json, created_at, client_id FROM analyses "
            f"WHERE id = {p} AND (is_public = 1 OR client_id = {p})",
            (analysis_id, client_id),
        ).fetchone()
    if row is None:
        return None
    owner = client_id is not None and row["client_id"] == client_id
    return AnalysisResponse.model_validate_json(row["result_json"]), row["created_at"], owner


def set_visibility(analysis_id: str, client_id: str | None, is_public: bool) -> AnalysisResponse | None:
    if client_id is None:
        return None
    with _connect() as (conn, p):
        row = conn.execute(
            f"SELECT result_json FROM analyses WHERE id = {p} AND client_id = {p}", (analysis_id, client_id)
        ).fetchone()
        if row is None:
            return None
        result = AnalysisResponse.model_validate_json(row["result_json"])
        result.is_public = is_public
        conn.execute(
            f"UPDATE analyses SET is_public = {p}, result_json = {p} WHERE id = {p} AND client_id = {p}",
            (int(is_public), result.model_dump_json(exclude=VIEW_ONLY_FIELDS), analysis_id, client_id),
        )
    return result


def is_owner(analysis_id: str, client_id: str | None) -> bool:
    if client_id is None:
        return False
    with _connect() as (conn, p):
        row = conn.execute(
            f"SELECT 1 FROM analyses WHERE id = {p} AND client_id = {p}", (analysis_id, client_id)
        ).fetchone()
    return row is not None


def get_share_token(analysis_id: str) -> str | None:
    with _connect() as (conn, p):
        row = conn.execute(f"SELECT token FROM shares WHERE analysis_id = {p}", (analysis_id,)).fetchone()
    return row["token"] if row else None


def create_share(analysis_id: str) -> str:
    # 이미 있으면 그 토큰을 돌려준다. '조회 후 INSERT'로 나눠 하면 동시 요청이 함께 INSERT하다
    # PostgreSQL에서 UNIQUE 위반(500)이 났다 (QA: 5번 동시 요청 중 4번 실패) → ON CONFLICT로 한 번에 처리
    token = secrets.token_urlsafe(16)
    with _connect() as (conn, p):
        conn.execute(
            f"INSERT INTO shares (token, analysis_id, created_at) VALUES ({p}, {p}, {p}) "
            "ON CONFLICT (analysis_id) DO NOTHING",
            (token, analysis_id, datetime.now(timezone.utc).isoformat()),
        )
        row = conn.execute(f"SELECT token FROM shares WHERE analysis_id = {p}", (analysis_id,)).fetchone()
    return row["token"]


def delete_share(analysis_id: str) -> None:
    with _connect() as (conn, p):
        conn.execute(f"DELETE FROM shares WHERE analysis_id = {p}", (analysis_id,))


def get_shared(token: str):
    with _connect() as (conn, p):
        row = conn.execute(
            f"SELECT a.result_json, a.created_at, a.id FROM shares s JOIN analyses a ON a.id = s.analysis_id "
            f"WHERE s.token = {p}",
            (token,),
        ).fetchone()
    if row is None:
        return None
    return AnalysisResponse.model_validate_json(row["result_json"]), row["created_at"]


def get_analysis_record(analysis_id: str, client_id: str | None):
    with _connect() as (conn, p):
        row = conn.execute(
            f"SELECT result_json, created_at FROM analyses "
            f"WHERE id = {p} AND (is_public = 1 OR client_id = {p})",
            (analysis_id, client_id),
        ).fetchone()

    if row is None:
        return None
    return AnalysisResponse.model_validate_json(row["result_json"]), row["created_at"]


def save_report(report: ReportResponse) -> None:
    with _connect() as (conn, p):
        conn.execute(
            f"""
            INSERT INTO reports (analysis_id, created_at, report_json) VALUES ({p}, {p}, {p})
            ON CONFLICT (analysis_id) DO UPDATE
            SET created_at = excluded.created_at, report_json = excluded.report_json
            """,
            (report.analysis_id, report.created_at, report.model_dump_json()),
        )


def get_report(analysis_id: str) -> ReportResponse | None:
    with _connect() as (conn, p):
        row = conn.execute(
            f"SELECT report_json FROM reports WHERE analysis_id = {p}", (analysis_id,)
        ).fetchone()

    if row is None:
        return None
    return ReportResponse.model_validate_json(row["report_json"])


def list_analyses(limit: int, client_id: str | None = None) -> list[AnalysisSummary]:
    with _connect() as (conn, p):
        if client_id is None:
            where, params = "a.is_public = 1", ()
        else:
            where, params = f"a.client_id = {p}", (client_id,)
        tiebreak = "a.seq" if _database_url() else "a.rowid"
        rows = conn.execute(
            f"SELECT a.id, a.url, a.verdict, a.created_at, o.masked_name FROM analyses a "
            f"LEFT JOIN owners o ON o.analysis_id = a.id WHERE {where} "
            f"ORDER BY a.created_at DESC, {tiebreak} DESC LIMIT {p}",
            (*params, limit),
        ).fetchall()

    return [
        AnalysisSummary(
            id=row["id"], url=row["url"], verdict=row["verdict"], created_at=row["created_at"],
            owner_name=row["masked_name"],
        )
        for row in rows
    ]


def save_owner(analysis_id: str, masked_name: str | None, secret_hash: str | None, name_hash: str | None = None) -> None:
    with _connect() as (conn, p):
        conn.execute(
            f"INSERT INTO owners (analysis_id, masked_name, secret_hash, name_hash) VALUES ({p}, {p}, {p}, {p})",
            (analysis_id, masked_name, secret_hash, name_hash),
        )


def get_owner(analysis_id: str) -> dict | None:
    with _connect() as (conn, p):
        row = conn.execute(
            f"SELECT o.masked_name, o.name_hash, o.secret_hash FROM owners o JOIN analyses a ON a.id = o.analysis_id "
            f"WHERE o.analysis_id = {p} AND a.is_public = 1 AND o.secret_hash IS NOT NULL",
            (analysis_id,),
        ).fetchone()
    return dict(row) if row else None


def delete_analysis(analysis_id: str) -> None:
    with _connect() as (conn, p):
        for table, column in _ANALYSIS_TABLES:
            conn.execute(f"DELETE FROM {table} WHERE {column} = {p}", (analysis_id,))


# 분석 하나에 딸린 기록들. 삭제·보관 기간 정리 때 함께 지운다 (분석 기록은 마지막)
_ANALYSIS_TABLES = (
    ("reports", "analysis_id"), ("shares", "analysis_id"), ("owners", "analysis_id"),
    ("owner_failures", "analysis_id"), ("feedback", "analysis_id"), ("analyses", "id"),
)


def purge_older_than(days: int) -> int:
    """보관 기간이 지난 분석 기록과 딸린 기록(리포트·공유 링크·본인 확인·신고)을 지운다. 지운 분석 수를 돌려준다.

    created_at은 UTC ISO 문자열이라 문자열 비교로 시간 순서를 비교할 수 있다.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with _connect() as (conn, p):
        ids = [r["id"] for r in conn.execute(f"SELECT id FROM analyses WHERE created_at < {p}", (cutoff,)).fetchall()]
        for analysis_id in ids:
            for table, column in _ANALYSIS_TABLES:
                conn.execute(f"DELETE FROM {table} WHERE {column} = {p}", (analysis_id,))
    return len(ids)


# ---------- 판정 오류 신고 ----------

def save_feedback(item: dict) -> bool:
    """신고를 저장한다. 같은 사용자가 같은 분석에 이미 신고했으면 저장하지 않고 False."""
    with _connect() as (conn, p):
        exists = conn.execute(
            f"SELECT 1 FROM feedback WHERE analysis_id = {p} AND client_id = {p}",
            (item["analysis_id"], item["client_id"]),
        ).fetchone()
        if exists:
            return False
        conn.execute(
            f"INSERT INTO feedback (id, analysis_id, client_id, url, verdict, claim, comment, status, created_at) "
            f"VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, 'pending', {p})",
            (item["id"], item["analysis_id"], item["client_id"], item["url"], item["verdict"],
             item["claim"], item["comment"], datetime.now(timezone.utc).isoformat()),
        )
    return True


def has_feedback(analysis_id: str, client_id: str) -> bool:
    with _connect() as (conn, p):
        return conn.execute(
            f"SELECT 1 FROM feedback WHERE analysis_id = {p} AND client_id = {p}", (analysis_id, client_id)
        ).fetchone() is not None


def count_recent_feedback(client_id: str, since_iso: str) -> int:
    with _connect() as (conn, p):
        row = conn.execute(
            f"SELECT COUNT(*) AS n FROM feedback WHERE client_id = {p} AND created_at >= {p}", (client_id, since_iso)
        ).fetchone()
    return int(row["n"])


def list_feedback(status: str = "pending", limit: int = 50) -> list[dict]:
    with _connect() as (conn, p):
        rows = conn.execute(
            f"SELECT id, analysis_id, url, verdict, claim, comment, status, created_at, review_note FROM feedback "
            f"WHERE status = {p} ORDER BY created_at LIMIT {p}",
            (status, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def review_feedback(feedback_id: str, status: str, note: str | None) -> bool:
    with _connect() as (conn, p):
        cur = conn.execute(
            f"UPDATE feedback SET status = {p}, review_note = {p}, reviewed_at = {p} WHERE id = {p} AND status = 'pending'",
            (status, note, datetime.now(timezone.utc).isoformat(), feedback_id),
        )
        return cur.rowcount > 0


# ---------- 본인 확인 실패 기록 ----------

def get_failures(analysis_id: str) -> tuple[int, float] | None:
    with _connect() as (conn, p):
        row = conn.execute(
            f"SELECT count, first_at FROM owner_failures WHERE analysis_id = {p}", (analysis_id,)
        ).fetchone()
    return (int(row["count"]), float(row["first_at"])) if row else None


def record_failure(analysis_id: str, now: float, window: float) -> None:
    """실패를 1회 더한다. 첫 실패로부터 window초가 지났으면 1회부터 다시 센다."""
    with _connect() as (conn, p):
        conn.execute(
            f"INSERT INTO owner_failures (analysis_id, count, first_at) VALUES ({p}, 1, {p}) "
            f"ON CONFLICT (analysis_id) DO UPDATE SET "
            f"count = CASE WHEN {p} - owner_failures.first_at > {p} THEN 1 ELSE owner_failures.count + 1 END, "
            f"first_at = CASE WHEN {p} - owner_failures.first_at > {p} THEN {p} ELSE owner_failures.first_at END",
            (analysis_id, now, now, window, now, window, now),
        )


def clear_failures(analysis_id: str) -> None:
    with _connect() as (conn, p):
        conn.execute(f"DELETE FROM owner_failures WHERE analysis_id = {p}", (analysis_id,))
