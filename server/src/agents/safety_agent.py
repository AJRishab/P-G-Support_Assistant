from pydantic import BaseModel, Field
from ..services.llm_service import LLMService


class SafetyEvaluation(BaseModel):
    reaction_reported: bool = Field(description=(
        "True ONLY if the customer reports a physical reaction, injury, or exposure that has "
        "already happened or is happening now - a rash appeared, skin is burning, a child "
        "swallowed the product, breathing difficulty, eye contact with chemicals. False if the "
        "customer only mentions a pre-existing trait or condition (e.g. 'I have sensitive skin', "
        "'I'm allergic to fragrance') while asking a normal product question, with no reaction reported."
    ))
    reason: str = Field(description="Reason for the classification, or a short note on what was found.")
    urgency: str = Field(description="Urgency: high, medium, or low. Must be 'low' if reaction_reported is False.")


class SafetyAgent:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    async def analyze(self, message: str) -> dict:
        prompt = (
            "You are a Safety Agent for P&G Customer Support.\n"
            "Determine whether the customer is reporting an ACTIVE physical safety incident: an "
            "injury, allergic reaction, skin rash, chemical exposure, or a child swallowing a "
            "product that has already happened or is happening now.\n\n"
            "Do NOT confuse these two cases:\n"
            "(a) REACTION ALREADY HAPPENED - e.g. 'this gave me a rash', 'my skin is burning', "
            "'my kid swallowed some' -> reaction_reported=true.\n"
            "(b) TRAIT MENTIONED, NOTHING HAPPENED - e.g. 'I have sensitive skin, which "
            "moisturizer should I use?' -> reaction_reported=false. This is an ordinary product "
            "question and must NOT be treated as a safety incident just because it names a "
            "health-related word.\n\n"
            "Independent of tone: a calm report of an actual reaction is still reaction_reported=true. "
            "A calm question that only references a trait, with nothing having happened, is false.\n"
            f"Customer Message: \"{message}\"\n\n"
            "Return a JSON object conforming to the schema."
        )
        try:
            result = await self.llm_service.generate_json(prompt, schema_class=SafetyEvaluation)
            reaction_reported = bool(result.get("reaction_reported", False))
            urgency = str(result.get("urgency", "low")).lower()
            if not reaction_reported:
                urgency = "low"
            return {
                "safety_triggered": reaction_reported,
                "reason": str(result.get("reason", "No active safety incident detected.")),
                "urgency": urgency,
            }
        except Exception as e:
            print(f"[SafetyAgent Error] Analysis failed: {e}")
            return {"safety_triggered": False, "reason": f"Fallback error: {e}", "urgency": "low"}