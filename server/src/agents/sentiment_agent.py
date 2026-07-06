from pydantic import BaseModel, Field
from ..services.llm_service import LLMService


class SentimentEvaluation(BaseModel):
    tone: str = Field(description="Customer's emotional tone: calm, annoyed, or furious.")


class SentimentAgent:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    async def analyze(self, message: str) -> dict:
        prompt = (
            "You are a Sentiment Agent for P&G Customer Support.\n"
            "Assess the emotional tone of the following customer message.\n"
            "Classify strictly as one of: 'calm', 'annoyed', or 'furious'.\n\n"
            "Default to 'calm'. Only move off it when the message contains actual signals of "
            "frustration or anger - complaints, criticism, exclamation marks, all-caps emphasis, "
            "or explicit dissatisfaction ('this is broken', 'I want a refund').\n\n"
            "A plainly-worded question is still 'calm' even with typos, no punctuation, run-on "
            "phrasing, or all-lowercase text - none of those are emotional signals on their own.\n"
            "Example: 'what diper should i buy my baby is 11 month old' -> calm (an ordinary "
            "question, just typed informally, not a complaint).\n\n"
            "Do not let the topic (safety, complaints about products in the abstract) influence "
            "this - judge only the customer's own tone.\n"
            f"Customer Message: \"{message}\"\n\n"
            "Return a JSON object conforming to the schema."
        )
        try:
            result = await self.llm_service.generate_json(prompt, schema_class=SentimentEvaluation)
            tone = str(result.get("tone", "calm")).lower()
            return {"tone": tone if tone in ["calm", "annoyed", "furious"] else "calm"}
        except Exception as e:
            print(f"[SentimentAgent Error] Analysis failed: {e}")
            return {"tone": "calm"}