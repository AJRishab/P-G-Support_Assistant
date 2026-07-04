import os
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .services.db_service import DBService
from .services.llm_service import LLMService
from .agents.orchestrator_agent import OrchestratorAgent

app = FastAPI(title="P&G Customer Support Chat Assistant")

# Enable CORS for frontend development (running on Vite, usually port 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the exact domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
db_path = os.getenv("DB_PATH", "pg_support.db")
db_service = DBService(db_path=db_path)
llm_service = LLMService()
orchestrator = OrchestratorAgent(llm_service, db_service)

class ChatRequest(BaseModel):
    message: str

@app.get("/api/history")
async def get_chat_history(x_session_id: str = Header(None)):
    """
    Step 8: Retrieves conversation history for the customer's session.
    """
    if not x_session_id:
        raise HTTPException(status_code=400, detail="X-Session-ID header is missing.")
    history = await db_service.get_history(x_session_id)
    return {"history": history}

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest, x_session_id: str = Header(None)):
    """
    Step 9: Streams progress states and final response chunks via SSE.
    """
    if not x_session_id:
        raise HTTPException(status_code=400, detail="X-Session-ID header is missing.")
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # Return a StreamingResponse utilizing the Orchestrator's generator
    generator = orchestrator.process_message(x_session_id, request.message)
    return StreamingResponse(generator, media_type="text/event-stream")

@app.get("/api/tickets")
async def get_all_tickets():
    """
    Endpoint for the support team dashboard to view human hand-off escalations.
    """
    tickets = await db_service.get_tickets()
    return {"tickets": tickets}

@app.post("/api/tickets/clear")
async def clear_all_data():
    """
    Utility endpoint to reset conversation logs and tickets during demos/testing.
    """
    await db_service.clear_database()
    return {"status": "success", "message": "All data cleared successfully."}