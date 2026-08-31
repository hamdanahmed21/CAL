"""
CB-12 · Feedback Endpoint Test Suite
─────────────────────────────────────────────────────────────────────────────
Tests POST /api/chat/feedback against all acceptance criteria.

HOW IT WORKS — nothing in the existing project is touched:
  - A minimal Starlette app is built here just for testing.
  - An isolated in-memory SQLite DB is created fresh for each test.
  - require_user is monkeypatched to simulate auth / guest states.
  - The real submit_feedback, upsert_feedback, and get_feedback_for_message
    functions from your actual files are imported and exercised.

PLACE THIS FILE AT:
  tests/test_cb12_feedback.py   (alongside chatbot_tests.py)

RUN WITH:
  pytest tests/test_cb12_feedback.py -v
─────────────────────────────────────────────────────────────────────────────
"""

import json
import sqlite3
import sys
import os
import pytest

# ── Path setup ────────────────────────────────────────────────────────────────
# Allows imports to resolve the same way the rest of the project does.
# Adjust if your project root is structured differently.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient
from starlette.requests import Request

# ── Imports from your actual code ─────────────────────────────────────────────
import db as db_module
import chat as chat_module
from chat import submit_feedback, json_response


# ═════════════════════════════════════════════════════════════════════════════
# TEST DATABASE SETUP
# Each test gets a completely fresh in-memory SQLite database so tests
# never interfere with each other or with the real calcvoyager.db.
# ═════════════════════════════════════════════════════════════════════════════

IN_MEMORY_DB = ":memory:"

# We keep one shared connection open for the duration of the test session
# because :memory: databases are destroyed when the last connection closes.
_test_conn: sqlite3.Connection = None


def _get_test_connection():
    """Return the shared test connection (mimics db_module.get_connection)."""
    global _test_conn
    if _test_conn is None:
        _test_conn = sqlite3.connect(IN_MEMORY_DB, check_same_thread=False)
        _test_conn.row_factory = sqlite3.Row
        _test_conn.execute("PRAGMA foreign_keys = ON")
    return _test_conn


def _reset_db():
    """Drop and recreate all tables — called before each test."""
    conn = _get_test_connection()
    conn.executescript("""
        DROP TABLE IF EXISTS message_feedback;
        DROP TABLE IF EXISTS chat_messages;
        DROP TABLE IF EXISTS chat_sessions;
        DROP TABLE IF EXISTS users;
    """)
    # Minimal users table so FK references resolve
    conn.executescript("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL
        );
    """ + db_module.CHAT_SCHEMA_SQL)
    conn.commit()


def _seed_db(user_id: int = 1, session_id: str = "test-session-uuid"):
    """
    Insert the minimum rows needed for feedback tests:
      - one user
      - one active session
      - one assistant message (this is what gets liked/disliked)
    Returns the message_id of the seeded assistant message.
    """
    conn = _get_test_connection()
    conn.execute("INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)", (user_id, "testuser"))
    conn.execute(
        "INSERT INTO chat_sessions (user_id, session_id, title) VALUES (?, ?, ?)",
        (user_id, session_id, "Test Session")
    )
    cursor = conn.execute(
        "INSERT INTO chat_messages (user_id, session_id, message_type, content) "
        "VALUES (?, ?, 'assistant', 'Here is your calculus answer.')",
        (user_id, session_id)
    )
    conn.commit()
    return cursor.lastrowid


# ── Patch db_module helpers to use the test connection ────────────────────────
# We replace get_connection in db_module so every helper (execute, fetchone,
# upsert_feedback, etc.) transparently uses the in-memory DB.

async def _patched_execute(query: str, params: tuple = ()):
    conn = _get_test_connection()
    cursor = conn.execute(query, params)
    conn.commit()
    return cursor.lastrowid

async def _patched_fetchone(query: str, params: tuple = ()):
    conn = _get_test_connection()
    cursor = conn.execute(query, params)
    row = cursor.fetchone()
    return dict(row) if row else None

async def _patched_fetchall(query: str, params: tuple = ()):
    conn = _get_test_connection()
    cursor = conn.execute(query, params)
    return [dict(r) for r in cursor.fetchall()]

async def _patched_scalar(query: str, params: tuple = ()):
    conn = _get_test_connection()
    cursor = conn.execute(query, params)
    row = cursor.fetchone()
    return row[0] if row else None

# Apply patches
db_module.execute  = _patched_execute
db_module.fetchone = _patched_fetchone
db_module.fetchall = _patched_fetchall
db_module.scalar   = _patched_scalar

# Patch the same names inside chat_module (it imported them at load time)
chat_module.execute  = _patched_execute
chat_module.fetchone = _patched_fetchone


# ═════════════════════════════════════════════════════════════════════════════
# AUTH HELPERS
# require_user normally reads a JWT from the request. We replace it per-test
# to simulate authenticated users and guests without any real tokens.
# ═════════════════════════════════════════════════════════════════════════════

def _make_auth(user_id):
    """Return a require_user that always authenticates as user_id."""
    def _auth(request: Request):
        return user_id
    return _auth

def _guest_auth(request: Request):
    """Simulates a guest — require_user returns None."""
    return None


# ═════════════════════════════════════════════════════════════════════════════
# MINIMAL TEST APP
# Only the feedback route is mounted — no other endpoints needed.
# ═════════════════════════════════════════════════════════════════════════════

def _make_app(user_id=None):
    """
    Build a fresh TestClient app.
    Pass user_id=None to simulate a guest.
    """
    if user_id is not None:
        chat_module.require_user = _make_auth(user_id)
    else:
        chat_module.require_user = _guest_auth

    app = Starlette(routes=[
        Route("/api/chat/feedback", submit_feedback, methods=["POST"]),
    ])
    return TestClient(app, raise_server_exceptions=True)


# ═════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═════════════════════════════════════════════════════════════════════════════

USER_ID    = 1
SESSION_ID = "test-session-uuid"

@pytest.fixture(autouse=True)
def fresh_db():
    """Reset and seed the database before every test."""
    _reset_db()
    yield


# ═════════════════════════════════════════════════════════════════════════════
# TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestFeedbackSuccess:
    """Happy-path cases — valid votes from authenticated users."""

    def test_like_returns_200(self):
        message_id = _seed_db(USER_ID, SESSION_ID)
        client = _make_app(user_id=USER_ID)

        resp = client.post("/api/chat/feedback", json={
            "message_id": message_id,
            "session_id": SESSION_ID,
            "feedback":   "like"
        })

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["feedback"] == "like"
        assert data["data"]["message_id"] == message_id

    def test_dislike_returns_200(self):
        message_id = _seed_db(USER_ID, SESSION_ID)
        client = _make_app(user_id=USER_ID)

        resp = client.post("/api/chat/feedback", json={
            "message_id": message_id,
            "session_id": SESSION_ID,
            "feedback":   "dislike"
        })

        assert resp.status_code == 200
        assert resp.json()["data"]["feedback"] == "dislike"

    def test_feedback_row_persisted_in_db(self):
        """After a like, a real row must exist in message_feedback."""
        message_id = _seed_db(USER_ID, SESSION_ID)
        client = _make_app(user_id=USER_ID)

        client.post("/api/chat/feedback", json={
            "message_id": message_id,
            "session_id": SESSION_ID,
            "feedback":   "like"
        })

        conn = _get_test_connection()
        row = conn.execute(
            "SELECT feedback FROM message_feedback WHERE message_id = ? AND user_id = ?",
            (message_id, USER_ID)
        ).fetchone()

        assert row is not None, "No row found in message_feedback"
        assert row["feedback"] == "like"


class TestUpsertBehaviour:
    """Re-voting must UPDATE the existing row, not INSERT a duplicate."""

    def test_revote_changes_value(self):
        message_id = _seed_db(USER_ID, SESSION_ID)
        client = _make_app(user_id=USER_ID)

        # First vote: like
        client.post("/api/chat/feedback", json={
            "message_id": message_id,
            "session_id": SESSION_ID,
            "feedback":   "like"
        })

        # Second vote: dislike (change of mind)
        resp = client.post("/api/chat/feedback", json={
            "message_id": message_id,
            "session_id": SESSION_ID,
            "feedback":   "dislike"
        })

        assert resp.status_code == 200
        assert resp.json()["data"]["feedback"] == "dislike"

    def test_revote_does_not_duplicate_row(self):
        """Only one row per (message_id, user_id) should ever exist."""
        message_id = _seed_db(USER_ID, SESSION_ID)
        client = _make_app(user_id=USER_ID)

        client.post("/api/chat/feedback", json={
            "message_id": message_id, "session_id": SESSION_ID, "feedback": "like"
        })
        client.post("/api/chat/feedback", json={
            "message_id": message_id, "session_id": SESSION_ID, "feedback": "dislike"
        })

        conn = _get_test_connection()
        count = conn.execute(
            "SELECT COUNT(*) FROM message_feedback WHERE message_id = ? AND user_id = ?",
            (message_id, USER_ID)
        ).fetchone()[0]

        assert count == 1, f"Expected 1 row, found {count} (upsert created duplicates)"


class TestValidation:
    """Bad input must be rejected with 400 before touching the DB."""

    def test_missing_message_id(self):
        _seed_db(USER_ID, SESSION_ID)
        client = _make_app(user_id=USER_ID)

        resp = client.post("/api/chat/feedback", json={
            "session_id": SESSION_ID,
            "feedback":   "like"
        })
        assert resp.status_code == 400

    def test_missing_session_id(self):
        message_id = _seed_db(USER_ID, SESSION_ID)
        client = _make_app(user_id=USER_ID)

        resp = client.post("/api/chat/feedback", json={
            "message_id": message_id,
            "feedback":   "like"
        })
        assert resp.status_code == 400

    def test_missing_feedback(self):
        message_id = _seed_db(USER_ID, SESSION_ID)
        client = _make_app(user_id=USER_ID)

        resp = client.post("/api/chat/feedback", json={
            "message_id": message_id,
            "session_id": SESSION_ID,
        })
        assert resp.status_code == 400

    def test_invalid_feedback_value(self):
        """Only 'like' and 'dislike' are valid — anything else is 400."""
        message_id = _seed_db(USER_ID, SESSION_ID)
        client = _make_app(user_id=USER_ID)

        resp = client.post("/api/chat/feedback", json={
            "message_id": message_id,
            "session_id": SESSION_ID,
            "feedback":   "meh"
        })
        assert resp.status_code == 400
        assert "like" in resp.json()["detail"] or "dislike" in resp.json()["detail"]

    def test_non_integer_message_id(self):
        _seed_db(USER_ID, SESSION_ID)
        client = _make_app(user_id=USER_ID)

        resp = client.post("/api/chat/feedback", json={
            "message_id": "abc",
            "session_id": SESSION_ID,
            "feedback":   "like"
        })
        assert resp.status_code == 400

    def test_empty_body(self):
        _seed_db(USER_ID, SESSION_ID)
        client = _make_app(user_id=USER_ID)

        resp = client.post("/api/chat/feedback", json={})
        assert resp.status_code == 400


class TestAuth:
    """Unauthenticated (guest) requests must be rejected with 401."""

    def test_guest_gets_401(self):
        message_id = _seed_db(USER_ID, SESSION_ID)
        client = _make_app(user_id=None)  # guest

        resp = client.post("/api/chat/feedback", json={
            "message_id": message_id,
            "session_id": SESSION_ID,
            "feedback":   "like"
        })
        assert resp.status_code == 401

    def test_guest_leaves_no_db_row(self):
        """A rejected guest request must not write anything to the DB."""
        message_id = _seed_db(USER_ID, SESSION_ID)
        client = _make_app(user_id=None)

        client.post("/api/chat/feedback", json={
            "message_id": message_id,
            "session_id": SESSION_ID,
            "feedback":   "like"
        })

        conn = _get_test_connection()
        count = conn.execute(
            "SELECT COUNT(*) FROM message_feedback"
        ).fetchone()[0]

        assert count == 0, "Guest request wrote a row — auth guard failed"


class TestOwnership:
    """A user must not be able to vote on another user's messages."""

    def test_wrong_user_gets_404(self):
        """
        Message belongs to USER_ID=1.
        Request authenticated as USER_ID=2.
        Should return 404 — message not found in their session.
        """
        message_id = _seed_db(user_id=1, session_id=SESSION_ID)

        # Seed a second user so FK is valid
        conn = _get_test_connection()
        conn.execute("INSERT OR IGNORE INTO users (id, username) VALUES (2, 'otheruser')")
        conn.commit()

        client = _make_app(user_id=2)  # different user

        resp = client.post("/api/chat/feedback", json={
            "message_id": message_id,
            "session_id": SESSION_ID,
            "feedback":   "like"
        })
        assert resp.status_code == 404

    def test_wrong_session_gets_404(self):
        """
        Valid user, valid message_id, but wrong session_id in the body.
        Should return 404.
        """
        message_id = _seed_db(USER_ID, SESSION_ID)
        client = _make_app(user_id=USER_ID)

        resp = client.post("/api/chat/feedback", json={
            "message_id": message_id,
            "session_id": "completely-wrong-session-id",
            "feedback":   "like"
        })
        assert resp.status_code == 404

    def test_nonexistent_message_gets_404(self):
        _seed_db(USER_ID, SESSION_ID)
        client = _make_app(user_id=USER_ID)

        resp = client.post("/api/chat/feedback", json={
            "message_id": 99999,   # doesn't exist
            "session_id": SESSION_ID,
            "feedback":   "like"
        })
        assert resp.status_code == 404
