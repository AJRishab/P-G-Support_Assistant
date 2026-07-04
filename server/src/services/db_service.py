import sqlite3
import aiosqlite

class DBService:
    def __init__(self, db_path="pg_support.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """
        Initializes the schema for conversation history and handoff tickets.

        This stays synchronous and runs once at construction time - a brief
        blocking call here is fine since it happens before the server starts
        accepting requests, not on the request path (unlike the per-request
        methods below, which use aiosqlite so they never block the event loop).
        """
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                # WAL mode lets readers and a writer proceed concurrently instead
                # of blocking each other - this is a database-level setting
                # persisted in the file itself, so it only needs to be set once.
                conn.execute("PRAGMA journal_mode=WAL")

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
                # Every lookup filters by session_id - without an index this was
                # a full table scan on every single chat message and page load.
                conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_tickets_session_id ON tickets(session_id)")
        finally:
            conn.close()

    async def save_message(self, session_id: str, role: str, content: str):
        """
        Saves a message to the conversation history.
        """
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
                (session_id, role, content)
            )
            await conn.commit()

    async def get_history(self, session_id: str) -> list:
        """
        Retrieves the conversation history for a given session ID.
        """
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT role, content FROM messages WHERE session_id = ? ORDER BY timestamp ASC",
                (session_id,)
            ) as cursor:
                rows = await cursor.fetchall()
            return [{"role": r["role"], "content": r["content"]} for r in rows]

    async def create_ticket(self, session_id: str, user_message: str, reason: str, tone: str, urgency: str):
        """
        Logs a human support follow-up ticket.
        """
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                """
                INSERT INTO tickets (session_id, user_message, reason, tone, urgency)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, user_message, reason, tone, urgency)
            )
            await conn.commit()

    async def get_tickets(self) -> list:
        """
        Retrieves all support tickets logged (for the admin view).
        """
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("SELECT * FROM tickets ORDER BY timestamp DESC") as cursor:
                rows = await cursor.fetchall()
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

    async def clear_database(self):
        """
        Helper method to reset database for testing.
        """
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("DELETE FROM messages")
            await conn.execute("DELETE FROM tickets")
            await conn.commit()