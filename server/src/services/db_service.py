import os
import sqlite3

class DBService:
    def __init__(self, db_path="pg_support.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        """
        Returns a standard connection. In SQLite, it's best to open a connection
        per thread/request to avoid threading conflicts.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """
        Initializes the schema for conversations history and handoff tickets.
        """
        conn = self._get_connection()
        try:
            with conn:
                # Create messages table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                # Create tickets table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS tickets (
                        ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        user_message TEXT NOT NULL,
                        reason TEXT NOT NULL,
                        tone TEXT NOT NULL,
                        urgency TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
        finally:
            conn.close()

    def save_message(self, session_id: str, role: str, content: str):
        """
        Saves a message to the conversation history.
        """
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
                    (session_id, role, content)
                )
        finally:
            conn.close()

    def get_history(self, session_id: str) -> list:
        """
        Retrieves the conversation history for a given session ID.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, content FROM messages WHERE session_id = ? ORDER BY timestamp ASC",
                (session_id,)
            )
            rows = cursor.fetchall()
            return [{"role": r["role"], "content": r["content"]} for r in rows]
        finally:
            conn.close()

    def create_ticket(self, session_id: str, user_message: str, reason: str, tone: str, urgency: str):
        """
        Logs a human support follow-up ticket.
        """
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO tickets (session_id, user_message, reason, tone, urgency)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (session_id, user_message, reason, tone, urgency)
                )
        finally:
            conn.close()

    def get_tickets(self) -> list:
        """
        Retrieves all support tickets logged (for the admin view).
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tickets ORDER BY timestamp DESC")
            rows = cursor.fetchall()
            return [
                {
                    "ticket_id": r["ticket_id"],
                    "session_id": r["session_id"],
                    "user_message": r["user_message"],
                    "reason": r["reason"],
                    "tone": r["tone"],
                    "urgency": r["urgency"],
                    "timestamp": r["timestamp"]
                }
                for r in rows
            ]
        finally:
            conn.close()

    def clear_database(self):
        """
        Helper method to reset database for testing.
        """
        conn = self._get_connection()
        try:
            with conn:
                conn.execute("DELETE FROM messages")
                conn.execute("DELETE FROM tickets")
        finally:
            conn.close()
