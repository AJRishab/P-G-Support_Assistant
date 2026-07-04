import os
import sys
import pytest
import json

# Add src to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services.llm_service import LLMService
from src.services.db_service import DBService
from src.agents.orchestrator_agent import OrchestratorAgent

TEST_DB_PATH = "test_integration.db"

@pytest.fixture
def db_service():
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    db = DBService(db_path=TEST_DB_PATH)
    yield db
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

@pytest.mark.asyncio
async def test_integration_safety_escalation(db_service):
    llm = LLMService()
    orchestrator = OrchestratorAgent(llm, db_service)
    
    session_id = "integ_test_session_1"
    message = "My baby swallowed Tide pods. Help!"
    
    # Process message and consume the stream
    responses = []
    async for event_line in orchestrator.process_message(session_id, message):
        event = json.loads(event_line.strip())
        responses.append(event)
        
    # Check that it streamed progress and chunks
    progress_events = [r for r in responses if r["type"] == "progress"]
    chunk_events = [r for r in responses if r["type"] == "chunk"]
    
    assert len(progress_events) > 0
    assert len(chunk_events) > 0
    
    # Check that a ticket was logged in the DB
    tickets = await db_service.get_tickets()
    assert len(tickets) == 1
    assert tickets[0]["session_id"] == session_id
    assert "Safety Concern" in tickets[0]["reason"]
    assert tickets[0]["urgency"] == "high"
    
    # Check that history was saved in DB
    history = await db_service.get_history(session_id)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == message
    assert history[1]["role"] == "assistant"
    assert len(history[1]["content"]) > 0

@pytest.mark.asyncio
async def test_integration_angry_escalation(db_service):
    llm = LLMService()
    orchestrator = OrchestratorAgent(llm, db_service)
    
    session_id = "integ_test_session_2"
    message = "Your razor cut me, I will sue you! Horrible product."
    
    # Process message and consume stream
    responses = []
    async for event_line in orchestrator.process_message(session_id, message):
        event = json.loads(event_line.strip())
        responses.append(event)
        
    # Check that a ticket was logged for negative tone
    tickets = await db_service.get_tickets()
    assert len(tickets) == 1
    assert tickets[0]["session_id"] == session_id
    assert "Negative Tone" in tickets[0]["reason"]
    assert tickets[0]["urgency"] == "medium"