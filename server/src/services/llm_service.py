import os
import json
import re
from google import genai
from google.genai import types

# Load GEMINI_API_KEY from env
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

class LLMService:
    def __init__(self):
        self.use_mock = not bool(GEMINI_API_KEY)
        if not self.use_mock:
            # Initialize the official Google Gen AI Client
            self.client = genai.Client(api_key=GEMINI_API_KEY)
            self.model_name = "gemini-2.5-flash"
        else:
            self.client = None
            self.model_name = "mock-engine"

    def generate_json(self, prompt: str, schema_class=None) -> dict:
        """
        Generates a JSON response from the LLM, with a fallback to mock evaluation
        if no API key is available.
        """
        if self.use_mock:
            return self._mock_json_response(prompt)

        try:
            # Set structured output config if schema_class is provided
            config = None
            if schema_class:
                config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema_class,
                    temperature=0.0
                )
            else:
                config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0
                )

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )
            return json.loads(response.text.strip())
        except Exception as e:
            # Fallback to mock on remote API errors
            print(f"[LLMService Error] Calling Gemini API failed: {e}. Falling back to mock.")
            return self._mock_json_response(prompt)

    async def generate_stream(self, prompt: str, system_instruction: str = None):
        """
        Asynchronously streams the response text from Gemini or mock.
        Yields chunk strings.
        """
        if self.use_mock:
            # Simulate a streaming response for mock mode
            import asyncio
            mock_text = self._mock_text_response(prompt, system_instruction)
            words = mock_text.split(" ")
            for i, word in enumerate(words):
                yield (word + " " if i < len(words) - 1 else word)
                await asyncio.sleep(0.05)
            return

        try:
            config = types.GenerateContentConfig(temperature=0.7)
            if system_instruction:
                config.system_instruction = system_instruction

            response_stream = self.client.models.generate_content_stream(
                model=self.model_name,
                contents=prompt,
                config=config
            )
            for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            print(f"[LLMService Error] Streaming failed: {e}. Falling back to mock stream.")
            # Fallback to mock stream
            import asyncio
            mock_text = self._mock_text_response(prompt, system_instruction)
            words = mock_text.split(" ")
            for i, word in enumerate(words):
                yield (word + " " if i < len(words) - 1 else word)
                await asyncio.sleep(0.05)

    def _mock_json_response(self, prompt: str) -> dict:
        """
        Heuristic rule-based mock engine to handle classification tasks offline.
        """
        prompt_lower = prompt.lower()

        # Extract the user's raw message if possible to avoid matching instruction text
        msg_match = re.search(r'customer message:\s*"(.*)"', prompt_lower, re.DOTALL)
        msg_content = msg_match.group(1) if msg_match else prompt_lower

        # 1. Safety Agent Classification
        if "safety agent" in prompt_lower or "safety check" in prompt_lower:
            danger_patterns = [
                r"\b(swallow|ingest|ate|drink|drunk|swallowed)\b",
                r"\b(rash|allerg|hives|burn|irritat|redness|swol|swell|hospit|doctor)\b",
                r"\b(poison|toxic|chok|bleed|injur|hurt|pain)\b",
                r"\b(eye|blind|exposure|exposed)\b"
            ]
            triggered = False
            reason = "No safety concern detected."
            urgency = "low"

            for pat in danger_patterns:
                match = re.search(pat, msg_content)
                if match:
                    triggered = True
                    matched_word = match.group(0)
                    urgency = "high" if "swallow" in matched_word or "poison" in matched_word or "hospital" in matched_word else "medium"
                    reason = f"Potential risk identified regarding '{matched_word}' in user message."
                    break

            return {
                "safety_triggered": triggered,
                "reason": reason,
                "urgency": urgency
            }

        # 2. Sentiment/Tone Agent Classification
        if "sentiment agent" in prompt_lower or "tone check" in prompt_lower:
            angry_patterns = [
                r"\b(sue|court|lawyer|horribl|worst|garbage|trash|useless|scam|fraud)\b",
                r"\b(hate|angry|pissed|furious|disgust|cancel|refund|complain)\b",
                r"!{2,}",
                r"\b(terrible|awful|crap|unacceptable)\b"
            ]
            annoyed_patterns = [
                r"\b(slow|disappoint|broke|faulty|frustrat|annoy|bad|regret|fix)\b"
            ]

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

        # 3. Product Agent Grounding
        if "product agent" in prompt_lower:
            matched_prods = []
            summary = ""
            unverifiable = []
            
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

            return {
                "relevant_products_found": matched_prods,
                "grounded_summary": summary,
                "unverifiable_questions": unverifiable
            }

        # Default fallback JSON
        return {"error": "Mock fallback reached without matching classification context."}

    def _mock_text_response(self, prompt: str, system_instruction: str = None) -> str:
        """
        Heuristic generator for the final response when in mock mode.
        """
        prompt_lower = prompt.lower()
        
        # Extract safety and escalation flags if they were embedded in the generation prompt
        safety_triggered = "safety_triggered: true" in prompt_lower or "safety_triggered=true" in prompt_lower or "swallow" in prompt_lower or "rash" in prompt_lower or "allergic" in prompt_lower
        tone_angry = "furious" in prompt_lower or "annoyed" in prompt_lower or "sue" in prompt_lower or "horrible" in prompt_lower
        
        escalated = safety_triggered or tone_angry
        
        # Basic grounding responses based on brand keywords
        grounded_info = ""
        if "tide" in prompt_lower:
            grounded_info = "Tide Hygienic Clean Heavy Duty 10X is designed for heavy-duty cleaning and removing grease. It contains Sodium Alcoholethoxy Sulfate and Sodium Borate. Keep out of reach of children. It is available at Walmart and Target."
        elif "pampers" in prompt_lower:
            grounded_info = "Pampers Splashers Disposable Swim Diapers are waterproof swim diapers that do not swell in water. They are made of Polypropylene and Polyethylene. Diapers are flammable, so keep them away from open flame. You can buy them at Target, Walgreens, and Amazon."
        elif "olay" in prompt_lower:
            grounded_info = "Olay Regenerist Whip Active Moisturizer hydrates skin and reduces wrinkles with a matte finish. It includes Glycerin, Niacinamide (Vitamin B3), and Peptides. Avoid contact with eyes. It is available at CVS, Walgreens, and olay.com."
        elif "gillette" in prompt_lower:
            grounded_info = "Gillette Labs Exfoliating Razor features an exfoliating bar to remove dirt before blades pass. It uses stainless steel blades and a lubricating strip. Handle sharp blades with care. It is available at Walmart, CVS, and gillette.com."

        response_parts = []
        
        # 1. Apology if angry
        if tone_angry:
            response_parts.append("I am very sorry to hear about your experience and understand your frustration.")
            
        # 2. General Safety guidance if triggered
        if safety_triggered:
            response_parts.append("Your safety is our top priority. Please stop using the product immediately. If someone ingested the product or is experiencing a severe reaction, contact a healthcare professional or Poison Control right away.")
            
        # 3. Grounded answer/recommendation
        if grounded_info:
            response_parts.append(f"Regarding your query: {grounded_info}")
        else:
            # General answer matching need
            if "sensitive skin" in prompt_lower:
                response_parts.append("For sensitive skin, Olay Regenerist Whip is dermatologically designed with Niacinamide to hydrate without irritation. You can buy it at Walgreens or olay.com.")
            elif "grease" in prompt_lower:
                response_parts.append("For grease stains, we recommend Tide Hygienic Clean Heavy Duty 10X, which is specifically formulated to remove heavy grease and dirt. It is available at major retailers like Target and Walmart.")
            else:
                response_parts.append("I'm happy to help you find the right P&G product. Could you tell me a bit more about what you're looking for (e.g. skin care, laundry care, baby diapers, or shaving)?")

        # 4. Escalation warning
        if escalated:
            response_parts.append("I have flagged this conversation for a human support representative who will follow up with you as soon as possible.")

        return " ".join(response_parts)
