import os
import json
import re
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL") or "openrouter/free"

REQUEST_HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "HTTP-Referer": "https://github.com/AJRishab/pg-support-assistant",
    "X-Title": "PG Support Assistant",
    "Content-Type": "application/json",
}


class LLMService:
    def __init__(self, model_name: str = None):
        self.use_mock = not bool(OPENROUTER_API_KEY)
        self.model_name = model_name or DEFAULT_MODEL
        if self.use_mock:
            print("[LLMService] Running in MOCK mode (no OPENROUTER_API_KEY found).")
        else:
            print(f"[LLMService] Running in LIVE mode - model '{self.model_name}'.")

    async def _call_openrouter(self, messages: list, schema_class=None) -> dict:
        payload = {"model": self.model_name, "messages": messages, "temperature": 0.0, "max_tokens": 4000}
        if schema_class and hasattr(schema_class, "model_json_schema"):
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": schema_class.__name__, "strict": True, "schema": schema_class.model_json_schema()},
            }
        async with httpx.AsyncClient(timeout=30.0, headers=REQUEST_HEADERS) as client:
            response = await client.post(f"{OPENROUTER_BASE_URL}/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
        return json.loads(data["choices"][0]["message"]["content"].strip())

    async def generate_json(self, prompt: str, schema_class=None) -> dict:
        if self.use_mock:
            return self._mock_json_response(prompt)
        try:
            return await self._call_openrouter([{"role": "user", "content": prompt}], schema_class)
        except Exception as e:
            print(f"[LLMService Error] Calling OpenRouter API failed: {e}. Falling back to mock.")
            return self._mock_json_response(prompt)

    async def generate_stream(self, prompt: str, system_instruction: str = None, mock_context: dict = None):
        """
        mock_context carries the pipeline's already-computed decisions so mock mode builds the
        reply from them directly, instead of re-scanning prompt text.
        """
        if self.use_mock:
            mock_text = self._mock_text_response(prompt, system_instruction, mock_context)
            words = mock_text.split(" ")
            for i, word in enumerate(words):
                yield (word + " " if i < len(words) - 1 else word)
                await asyncio.sleep(0.05)
            return

        try:
            messages = [{"role": "user", "content": prompt}]
            if system_instruction:
                messages.insert(0, {"role": "system", "content": system_instruction})
            async with httpx.AsyncClient(timeout=30.0, headers=REQUEST_HEADERS) as async_client:
                payload = {"model": self.model_name, "messages": messages, "temperature": 0.7, "max_tokens": 4000, "stream": True}
                async with async_client.stream(f"{OPENROUTER_BASE_URL}/chat/completions", json=payload) as response:
                    async for chunk in response.aiter_lines():
                        if chunk:
                            try:
                                data = json.loads(chunk)
                                if "choices" in data and data["choices"]:
                                    delta = data["choices"][0].get("delta", {})
                                    if "content" in delta:
                                        yield delta["content"]
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            print(f"[LLMService Error] Streaming failed: {e}. Falling back to mock stream.")
            mock_text = self._mock_text_response(prompt, system_instruction, mock_context)
            words = mock_text.split(" ")
            for i, word in enumerate(words):
                yield (word + " " if i < len(words) - 1 else word)
                await asyncio.sleep(0.05)

    def _mock_json_response(self, prompt: str) -> dict:
        prompt_lower = prompt.lower()
        # Non-greedy - the old greedy version could over-capture past the intended closing quote.
        msg_match = re.search(r'customer message:\s*"(.*?)"', prompt_lower, re.DOTALL)
        msg_content = msg_match.group(1) if msg_match else prompt_lower

        if "safety agent" in prompt_lower or "safety check" in prompt_lower:
            # \w* suffixes catch plurals/variants ("rashes", "burning") the old exact-word
            # patterns silently missed.
            danger_patterns = [
                r"\b(swallow\w*|ingest\w*|ate|drank|drink\w*|drunk)\b",
                r"\b(rash\w*|allerg\w*|hive\w*|burn\w*|irritat\w*|redness|swoll?en|swell\w*|hospital\w*|doctor\w*)\b",
                r"\b(poison\w*|toxic\w*|chok\w*|bleed\w*|bled|injur\w*|hurt\w*|pain\w*)\b",
                r"\b(eye\w*|blind\w*|exposure|exposed)\b",
            ]
            triggered, reason, urgency = False, "No safety concern detected.", "low"
            for pat in danger_patterns:
                match = re.search(pat, msg_content)
                if match:
                    triggered = True
                    matched_word = match.group(0)
                    urgency = "high" if re.match(r"swallow|poison|hospital", matched_word) else "medium"
                    reason = f"Potential risk identified regarding '{matched_word}' in user message."
                    break
            return {"safety_triggered": triggered, "reaction_reported": triggered, "reason": reason, "urgency": urgency}

        if "sentiment agent" in prompt_lower or "tone check" in prompt_lower:
            angry_patterns = [
                r"\b(sue|court|lawyer|horribl|worst|garbage|trash|useless|scam|fraud)\b",
                r"\b(hate|angry|pissed|furious|disgust|cancel|refund|complain)\b",
                r"!{2,}", r"\b(terrible|awful|crap|unacceptable)\b",
            ]
            annoyed_patterns = [r"\b(slow|disappoint|broke|faulty|frustrat|annoy|bad|regret|fix)\b"]
            tone = "calm"
            for pat in angry_patterns:
                if re.search(pat, msg_content):
                    tone = "furious"
                    break
            if tone == "calm":
                for pat in annoyed_patterns:
                    if re.search(pat, msg_content):
                        tone = "annoyed"
                        break
            return {"tone": tone}

        if "product agent" in prompt_lower:
            matched_prods, summary, unverifiable = [], "", []
            if "tide" in msg_content:
                matched_prods.append("Tide Hygienic Clean Heavy Duty 10X")
                summary = "Tide Hygienic Clean Heavy Duty 10X contains Sodium Alcoholethoxy Sulfate, Linear Alkylbenzene Sulfonate, Propylene Glycol, Sodium Borate, and Water. It is designed for heavy-duty cleaning and removing grease."
            elif "pampers" in msg_content:
                matched_prods.append("Pampers Splashers Disposable Swim Diapers")
                summary = "Pampers Splashers are waterproof swim diapers made of Polypropylene, Polyethylene, Elastomer, and Adhesives. Diapers are flammable; keep away from open flame."
            elif "olay" in msg_content or "sensitive skin" in msg_content:
                matched_prods.append("Olay Regenerist Whip Active Moisturizer")
                summary = "Olay Regenerist Whip hydrates skin and contains Niacinamide (Vitamin B3), Glycerin, Peptides, and Hyaluronic Acid. Avoid eye contact."
            elif "gillette" in msg_content:
                matched_prods.append("Gillette Labs with Exfoliating Bar Shaving Razor")
                summary = "Gillette Labs Exfoliating Razor uses stainless steel blades and a lubricating strip."
            else:
                unverifiable.append("No official product matches found in our database.")
                summary = "We could not find verified details for the requested product."
            return {"relevant_products_found": matched_prods, "grounded_summary": summary, "unverifiable_questions": unverifiable}

        return {"error": "Mock fallback reached without matching classification context."}

    def _mock_text_response(self, prompt: str, system_instruction: str = None, mock_context: dict = None) -> str:
        if mock_context is not None:
            safety_triggered = bool(mock_context.get("safety_triggered", False))
            tone_angry = mock_context.get("tone") in ("annoyed", "furious")
            escalated = bool(mock_context.get("handoff_required", False))
            grounded_summary = mock_context.get("grounded_summary") or ""

            parts = []
            if tone_angry:
                parts.append("I am very sorry to hear about your experience and understand your frustration.")
            if safety_triggered:
                parts.append("Your safety is our top priority. Please stop using the product immediately. "
                              "If someone ingested the product or is experiencing a severe reaction, contact a "
                              "healthcare professional or Poison Control right away.")
            if grounded_summary:
                parts.append(f"Regarding your query: {grounded_summary}")
            else:
                parts.append("I'm happy to help you find the right P&G product. Could you tell me a bit more "
                              "about what you're looking for (e.g. skin care, laundry care, baby diapers, or shaving)?")
            if escalated:
                parts.append("I have flagged this conversation for a human support representative who will "
                              "follow up with you as soon as possible.")
            return " ".join(parts)

        # legacy fallback for any caller that doesn't pass mock_context
        prompt_lower = prompt.lower()
        safety_triggered = bool(re.search(r"\b(swallow\w*|rash\w*|allerg\w*)\b", prompt_lower))
        tone_angry = "furious" in prompt_lower or "annoyed" in prompt_lower or "sue" in prompt_lower or "horrible" in prompt_lower
        escalated = safety_triggered or tone_angry

        grounded_info = ""
        if "tide" in prompt_lower:
            grounded_info = "Tide Hygienic Clean Heavy Duty 10X is designed for heavy-duty cleaning and removing grease. It contains Sodium Alcoholethoxy Sulfate and Sodium Borate. Keep out of reach of children. It is available at Walmart and Target."
        elif "pampers" in prompt_lower:
            grounded_info = "Pampers Splashers Disposable Swim Diapers are waterproof swim diapers that do not swell in water. They are made of Polypropylene and Polyethylene. Diapers are flammable, so keep them away from open flame. You can buy them at Target, Walgreens, and Amazon."
        elif "olay" in prompt_lower:
            grounded_info = "Olay Regenerist Whip Active Moisturizer hydrates skin and reduces wrinkles with a matte finish. It includes Glycerin, Niacinamide (Vitamin B3), and Peptides. Avoid contact with eyes. It is available at CVS, Walgreens, and olay.com."
        elif "gillette" in prompt_lower:
            grounded_info = "Gillette Labs Exfoliating Razor features an exfoliating bar to remove dirt before blades pass. It uses stainless steel blades and a lubricating strip. Handle sharp blades with care. It is available at Walmart, CVS, and gillette.com."

        parts = []
        if tone_angry:
            parts.append("I am very sorry to hear about your experience and understand your frustration.")
        if safety_triggered:
            parts.append("Your safety is our top priority. Please stop using the product immediately. If someone ingested the product or is experiencing a severe reaction, contact a healthcare professional or Poison Control right away.")
        if grounded_info:
            parts.append(f"Regarding your query: {grounded_info}")
        else:
            parts.append("I'm happy to help you find the right P&G product. Could you tell me a bit more about what you're looking for (e.g. skin care, laundry care, baby diapers, or shaving)?")
        if escalated:
            parts.append("I have flagged this conversation for a human support representative who will follow up with you as soon as possible.")
        return " ".join(parts)