"""
sql_engine.py
SQLite-backed SQL engine.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "business.db"


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_schema() -> str:
    """Return compact schema description for the system prompt."""
    conn = _get_conn()
    cur  = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cur.fetchall()]

    lines = []
    for table in tables:
        cur.execute(f"PRAGMA table_info({table})")
        cols     = cur.fetchall()
        col_defs = ", ".join(f"{c[1]} ({c[2]})" for c in cols)
        lines.append(f"  {table}: {col_defs}")

    conn.close()
    return "DATABASE SCHEMA (SQLite):\n" + "\n".join(lines)


def run_query(sql: str) -> dict:
    """Execute a SELECT query and return results as a dict."""
    normalized = sql.strip().upper()
    for dangerous in ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE"):
        if normalized.startswith(dangerous):
            return {"columns": [], "rows": [], "row_count": 0,
                    "error": f"Write operation '{dangerous}' is not allowed."}
    try:
        conn = _get_conn()
        cur  = conn.cursor()
        cur.execute(sql)
        rows    = cur.fetchall()
        columns = [desc[0] for desc in cur.description] if cur.description else []
        data    = [list(row) for row in rows]
        conn.close()
        return {"columns": columns, "rows": data, "row_count": len(data), "error": None}
    except Exception as e:
        return {"columns": [], "rows": [], "row_count": 0, "error": str(e)}


def format_sql_result(result: dict) -> str:
    if result["error"]:
        return f"SQL ERROR: {result['error']}"
    if result["row_count"] == 0:
        return "Query returned no results."
    columns = result["columns"]
    rows    = result["rows"]
    lines   = [" | ".join(columns), "-" * max(len(" | ".join(columns)), 10)]
    for row in rows[:50]:
        lines.append(" | ".join(str(v) for v in row))
    if result["row_count"] > 50:
        lines.append(f"... ({result['row_count'] - 50} more rows)")
    return "\n".join(lines)