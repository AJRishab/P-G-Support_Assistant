import os
import sys
import pytest

# Add src to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services.db_service import DBService

TEST_DB_PATH = "test_pg_support.db"

@pytest.fixture
def clean_db():
    # Remove test db file if exists
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    
    db = DBService(db_path=TEST_DB_PATH)
    yield db
    
    # Cleanup after test
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

def test_session_persistence_across_restart(clean_db):
    session_id = "test_session_123"
    
    # Write messages to database
    clean_db.save_message(session_id, "user", "Hello support!")
    clean_db.save_message(session_id, "assistant", "Hello! How can I help you?")
    
    # Retrieve and verify
    history1 = clean_db.get_history(session_id)
    assert len(history1) == 2
    assert history1[0]["role"] == "user"
    assert history1[1]["role"] == "assistant"
    
    # Simulate Server Restart by reinstantiating the DBService
    new_db_instance = DBService(db_path=TEST_DB_PATH)
    
    # Retrieve again and verify it is identical
    history2 = new_db_instance.get_history(session_id)
    assert len(history2) == 2
    assert history2[0]["content"] == "Hello support!"
    assert history2[1]["content"] == "Hello! How can I help you?"

def test_ticket_creation_and_retrieval(clean_db):
    session_id = "test_safety_session"
    
    clean_db.create_ticket(
        session_id=session_id,
        user_message="Help, my kid ate Tide pods!",
        reason="Safety Concern",
        tone="calm",
        urgency="high"
    )
    
    # Verify ticket is logged
    tickets = clean_db.get_tickets()
    assert len(tickets) == 1
    assert tickets[0]["session_id"] == session_id
    assert tickets[0]["urgency"] == "high"
    assert tickets[0]["reason"] == "Safety Concern"
