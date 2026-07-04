from pydantic import BaseModel, Field
from ..services.llm_service import LLMService

class SentimentEvaluation(BaseModel):
    tone: str = Field(description="Customer's emotional tone: calm, annoyed, or furious.")

class SentimentAgent:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    async def analyze(self, message: str) -> dict:
        """
        Independently assesses the emotional tone of what the customer said.
        Step 4: Separately judge how the customer is feeling.
        """
        prompt = (
            "You are a Sentiment Agent for P&G Customer Support.\n"
            "Assess the emotional tone of the following customer message.\n"
            "Classify it strictly as one of the following: 'calm', 'annoyed', or 'furious'.\n"
            "Do not let the factual content influence this classification. Focus purely on tone and emotion "
            "(e.g., uppercase words, exclamation marks, or threats to sue indicate a furious/annoyed tone).\n"
            f"Customer Message: \"{message}\"\n\n"
            "Return a JSON object conforming to the schema."
        )

        try:
            result = await self.llm_service.generate_json(prompt, schema_class=SentimentEvaluation)
            tone = str(result.get("tone", "calm")).lower()
            if tone not in ["calm", "annoyed", "furious"]:
                tone = "calm"
            return {"tone": tone}
        except Exception as e:
            print(f"[SentimentAgent Error] Analysis failed: {e}")
            return {"tone": "calm"}