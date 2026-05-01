"""
Netlify function: /api/history
GET / POST / DELETE — command history via Neon Postgres.
"""

import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor


def get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"], cursor_factory=RealDictCursor)


def ensure_table(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS shellsage_history (
                id           SERIAL PRIMARY KEY,
                session_id   TEXT      NOT NULL,
                query        TEXT,
                command      TEXT      NOT NULL,
                mode         TEXT      NOT NULL DEFAULT 'generate',
                shell        TEXT      DEFAULT 'bash',
                os           TEXT      DEFAULT 'Linux',
                danger_level TEXT      DEFAULT 'safe',
                was_run      BOOLEAN   DEFAULT FALSE,
                created_at   TIMESTAMP DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_session ON shellsage_history(session_id);
            CREATE INDEX IF NOT EXISTS idx_created ON shellsage_history(created_at DESC);
        """)
        conn.commit()


def handler(event, context):
    if event.get("httpMethod") == "OPTIONS":
        return _cors(200, "")
    method = event.get("httpMethod", "GET")
    params = event.get("queryStringParameters") or {}
    try:
        conn = get_conn()
        ensure_table(conn)
        if method == "POST":
            return handle_save(conn, event)
        elif method == "GET":
            return handle_fetch(conn, params)
        elif method == "DELETE":
            return handle_delete(conn, params)
        else:
            return _cors(405, json.dumps({"error": "Method not allowed"}))
    except Exception as e:
        return _cors(500, json.dumps({"error": str(e)}))


def handle_save(conn, event):
    body = json.loads(event.get("body") or "{}")
    if not body.get("session_id") or not body.get("command"):
        return _cors(400, json.dumps({"error": "session_id and command are required"}))
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO shellsage_history
                (session_id, query, command, mode, shell, os, danger_level, was_run)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, created_at
        """, (
            body["session_id"],
            body.get("query", ""),
            body["command"],
            body.get("mode", "generate"),
            body.get("shell", "bash"),
            body.get("os", "Linux"),
            body.get("danger_level", "safe"),
            body.get("was_run", False),
        ))
        row = cur.fetchone()
        conn.commit()
    return _cors(201, json.dumps({
        "id": row["id"],
        "created_at": row["created_at"].isoformat(),
    }))


def handle_fetch(conn, params):
    session_id = params.get("session_id")
    search     = params.get("search", "").strip()
    limit      = min(int(params.get("limit", 50)), 200)
    offset     = int(params.get("offset", 0))
    with conn.cursor() as cur:
        if search:
            cur.execute("""
                SELECT id, session_id, query, command, mode, shell, os,
                       danger_level, was_run, created_at
                FROM shellsage_history
                WHERE (session_id = %s OR %s IS NULL)
                  AND (query ILIKE %s OR command ILIKE %s)
                ORDER BY created_at DESC LIMIT %s OFFSET %s
            """, (session_id, session_id, f"%{search}%", f"%{search}%", limit, offset))
        else:
            cur.execute("""
                SELECT id, session_id, query, command, mode, shell, os,
                       danger_level, was_run, created_at
                FROM shellsage_history
                WHERE (session_id = %s OR %s IS NULL)
                ORDER BY created_at DESC LIMIT %s OFFSET %s
            """, (session_id, session_id, limit, offset))
        rows = cur.fetchall()
    results = []
    for row in rows:
        r = dict(row)
        r["created_at"] = r["created_at"].isoformat()
        results.append(r)
    return _cors(200, json.dumps({"history": results, "count": len(results)}))


def handle_delete(conn, params):
    session_id = params.get("session_id")
    if not session_id:
        return _cors(400, json.dumps({"error": "session_id is required"}))
    with conn.cursor() as cur:
        cur.execute("DELETE FROM shellsage_history WHERE session_id = %s", (session_id,))
        deleted = cur.rowcount
        conn.commit()
    return _cors(200, json.dumps({"deleted": deleted}))


def _cors(status: int, body: str):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin":  "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
        },
        "body": body,
    }
