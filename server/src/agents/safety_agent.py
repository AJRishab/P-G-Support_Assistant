from pydantic import BaseModel, Field
from ..services.llm_service import LLMService

class SafetyEvaluation(BaseModel):
    safety_triggered: bool = Field(description="True if the message contains physical safety concerns, injuries, rash, allergic reactions, ingestion, or chemical exposure.")
    reason: str = Field(description="Reason for triggering safety or a brief description of findings.")
    urgency: str = Field(description="Urgency level: high, medium, or low.")

class SafetyAgent:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    async def analyze(self, message: str) -> dict:
        """
        Scans the user message for safety/risk language.
        Step 1: Check for safety concerns first, before anything else.
        """
        # Define instruction for safety agent
        prompt = (
            "You are a Safety Agent for P&G Customer Support.\n"
            "Analyze the following customer message for physical safety risks, injuries, "
            "allergic reactions, skin rashes, chemical exposure, or a child swallowing a product.\n"
            "This check must be objective and independent of the user's tone (even if they sound calm, "
            "a report of physical harm must be treated as safety_triggered=true).\n"
            f"Customer Message: \"{message}\"\n\n"
            "Return a JSON object conforming to the schema."
        )

        try:
            # Query LLM with schema guidance
            result = await self.llm_service.generate_json(prompt, schema_class=SafetyEvaluation)
            
            # Ensure return dict has all keys
            return {
                "safety_triggered": bool(result.get("safety_triggered", False)),
                "reason": str(result.get("reason", "No safety concern detected.")),
                "urgency": str(result.get("urgency", "low")).lower()
            }
        except Exception as e:
            print(f"[SafetyAgent Error] Analysis failed: {e}")
            return {
                "safety_triggered": False,
                "reason": f"Fallback error: {e}",
                "urgency": "low"
            }