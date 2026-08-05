from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import psycopg
import sqlparse
from databricks.sdk import WorkspaceClient
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


SCHEMA = "support_app"
ALLOWED_STATUSES = ("open", "in_progress", "resolved")
_workspace_client = WorkspaceClient()


class OAuthConnection(psycopg.Connection):
    """Create each PostgreSQL connection with a fresh Lakebase OAuth token."""

    @classmethod
    def connect(cls, conninfo: str = "", **kwargs: Any) -> "OAuthConnection":
        endpoint_name = os.environ["ENDPOINT_NAME"]
        credential = _workspace_client.postgres.generate_database_credential(
            endpoint=endpoint_name
        )
        kwargs["password"] = credential.token
        return super().connect(conninfo, **kwargs)


def _required_environment() -> dict[str, str]:
    names = ("ENDPOINT_NAME", "PGDATABASE", "PGHOST", "PGPORT", "PGUSER")
    values = {name: os.environ.get(name, "").strip() for name in names}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise RuntimeError(
            "Missing Databricks App database configuration: " + ", ".join(missing)
        )
    return values


@lru_cache(maxsize=1)
def get_pool() -> ConnectionPool:
    """Return one process-level pool; new connections receive fresh tokens."""

    env = _required_environment()
    sslmode = os.environ.get("PGSSLMODE", "require")
    conninfo = (
        f"dbname={env['PGDATABASE']} user={env['PGUSER']} "
        f"host={env['PGHOST']} port={env['PGPORT']} sslmode={sslmode}"
    )
    pool = ConnectionPool(
        conninfo=conninfo,
        connection_class=OAuthConnection,
        kwargs={"row_factory": dict_row},
        min_size=1,
        max_size=5,
        open=True,
    )
    pool.wait()
    return pool


@lru_cache(maxsize=1)
def initialize_database() -> None:
    """Create the schema, tables, indexes, and idempotent sample rows."""

    schema_path = Path(__file__).with_name("schema.sql")
    statements = sqlparse.split(schema_path.read_text(encoding="utf-8"))
    with get_pool().connection() as conn:
        with conn.cursor() as cur:
            for statement in statements:
                if statement.strip():
                    cur.execute(statement)


def list_tickets() -> list[dict[str, Any]]:
    query = f"""
        SELECT
            t.ticket_id,
            t.title,
            t.status,
            t.created_by,
            t.created_at,
            COUNT(m.message_id) AS message_count
        FROM {SCHEMA}.tickets AS t
        LEFT JOIN {SCHEMA}.ticket_messages AS m
            ON m.ticket_id = t.ticket_id
        GROUP BY
            t.ticket_id,
            t.title,
            t.status,
            t.created_by,
            t.created_at
        ORDER BY t.created_at DESC, t.ticket_id DESC
    """
    with get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            return list(cur.fetchall())


def get_ticket(ticket_id: int) -> dict[str, Any] | None:
    query = f"""
        SELECT ticket_id, title, status, created_by, created_at
        FROM {SCHEMA}.tickets
        WHERE ticket_id = %s
    """
    with get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (ticket_id,))
            return cur.fetchone()


def get_ticket_messages(ticket_id: int) -> list[dict[str, Any]]:
    query = f"""
        SELECT message_id, ticket_id, message_text, author, created_at
        FROM {SCHEMA}.ticket_messages
        WHERE ticket_id = %s
        ORDER BY created_at, message_id
    """
    with get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (ticket_id,))
            return list(cur.fetchall())


def create_ticket(title: str, status: str, created_by: str) -> int:
    title = title.strip()
    created_by = created_by.strip()
    if not title or not created_by:
        raise ValueError("Title and creator are required.")
    if status not in ALLOWED_STATUSES:
        raise ValueError("Unsupported ticket status.")

    query = f"""
        INSERT INTO {SCHEMA}.tickets (title, status, created_by)
        VALUES (%s, %s, %s)
        RETURNING ticket_id
    """
    with get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (title, status, created_by))
            row = cur.fetchone()
            return int(row["ticket_id"])


def add_message(ticket_id: int, message_text: str, author: str) -> int:
    message_text = message_text.strip()
    author = author.strip()
    if not message_text or not author:
        raise ValueError("Message and author are required.")

    query = f"""
        INSERT INTO {SCHEMA}.ticket_messages (ticket_id, message_text, author)
        VALUES (%s, %s, %s)
        RETURNING message_id
    """
    with get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (ticket_id, message_text, author))
            row = cur.fetchone()
            return int(row["message_id"])


def update_ticket_status(ticket_id: int, status: str) -> None:
    if status not in ALLOWED_STATUSES:
        raise ValueError("Unsupported ticket status.")

    query = f"""
        UPDATE {SCHEMA}.tickets
        SET status = %s
        WHERE ticket_id = %s
        RETURNING ticket_id
    """
    with get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (status, ticket_id))
            if cur.fetchone() is None:
                raise ValueError("Ticket not found.")

            
