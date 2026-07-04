import json
import asyncio
from ..services.llm_service import LLMService
from .safety_agent import SafetyAgent
from .product_agent import ProductAgent
from .sentiment_agent import SentimentAgent

class OrchestratorAgent:
    def __init__(self, llm_service: LLMService, db_service=None):
        self.llm_service = llm_service
        self.db_service = db_service
        self.safety_agent = SafetyAgent(llm_service)
        self.product_agent = ProductAgent(llm_service)
        self.sentiment_agent = SentimentAgent(llm_service)

    async def process_message(self, session_id: str, message: str):
        """
        Coordinates the entire multi-agent pipeline and streams the response.
        Yields JSON-formatted chunk strings.
        """
        # Step 8: Load existing history from DB
        history = []
        if self.db_service:
            history = await self.db_service.get_history(session_id)

        # Safety, Product, and Sentiment are independent of each other's output
        # (Product only needs `history`, already loaded above) - so kick all three
        # off concurrently right away instead of running them one after another.
        # The progress messages below are still yielded in sequence, with their
        # original pacing, purely for the UI's step-by-step display; the real
        # work is already running in the background by the time each message
        # appears, so total wall-clock time is roughly the slowest of the three
        # calls instead of the sum of all three run one after another.
        pipeline_task = asyncio.gather(
            self.safety_agent.analyze(message),
            self.product_agent.analyze_and_ground(message, history),
            self.sentiment_agent.analyze(message),
        )

        # Yield Progress Step 1: Safety Check
        yield json.dumps({
            "type": "progress",
            "agent": "Safety Agent",
            "status": "active",
            "message": "Safety Agent scanning message for health/exposure risks..."
        }) + "\n"
        await asyncio.sleep(0.4) # Small delay for visual progress simulation

        # Yield Progress Step 2 & 3: Product Search & Grounding
        yield json.dumps({
            "type": "progress",
            "agent": "Product Agent",
            "status": "active",
            "message": "Product Agent querying trustworthy database and checking grounding..."
        }) + "\n"
        await asyncio.sleep(0.4)

        # Yield Progress Step 4: Sentiment Assessment
        yield json.dumps({
            "type": "progress",
            "agent": "Sentiment Agent",
            "status": "active",
            "message": "Sentiment Agent analyzing customer tone..."
        }) + "\n"
        await asyncio.sleep(0.4)

        # All three results are awaited here. If the real calls took longer than
        # the ~1.2s of pacing above, this simply waits for whichever is slowest -
        # it never adds the three durations together the way sequential calls did.
        safety_res, product_res, sentiment_res = await pipeline_task

        safety_triggered = safety_res.get("safety_triggered", False)
        safety_reason = safety_res.get("reason", "")
        urgency = safety_res.get("urgency", "low")

        grounded_facts = product_res.get("grounded_summary", "")
        unverifiable = product_res.get("unverifiable_questions", [])

        tone = sentiment_res.get("tone", "calm")

        # Step 5: Decide whether a human needs to step in
        # Trigger handoff if safety is triggered OR if tone is negative (annoyed or furious)
        tone_is_negative = tone in ["annoyed", "furious"]
        handoff_required = safety_triggered or tone_is_negative

        # Step 6: Log hand-off if needed
        if handoff_required:
            reason = "Safety Concern" if safety_triggered else f"Negative Tone ({tone})"
            if safety_triggered and tone_is_negative:
                reason = f"Safety Concern & Negative Tone ({tone})"

            yield json.dumps({
                "type": "progress",
                "agent": "Orchestrator Agent",
                "status": "active",
                "message": f"Orchestrator Agent triggering human agent hand-off (Reason: {reason})..."
            }) + "\n"
            await asyncio.sleep(0.4)

            if self.db_service:
                await self.db_service.create_ticket(
                    session_id=session_id,
                    user_message=message,
                    reason=reason,
                    tone=tone,
                    urgency="high" if safety_triggered else "medium"
                )

        yield json.dumps({
            "type": "progress",
            "agent": "Orchestrator Agent",
            "status": "done",
            "message": "All agents reports gathered. Generating reply..."
        }) + "\n"
        await asyncio.sleep(0.2)

        # Step 7: Response generation prompt combining everything
        system_instruction = (
            "You are the final response compiler for P&G Customer Support.\n"
            "You must generate a response that is helpful, strictly grounded in the official facts provided, "
            "and adjusts its tone based on the sentiment classification.\n"
            "Rules:\n"
            "1. NEVER invent any facts, ingredients, or claims about products. If information is not provided in the facts, state clearly and honestly that we cannot verify it.\n"
            "2. NEVER diagnose, prescribe dosages, or give medical advice. If a safety concern is flagged, tell the customer to stop use, consult a doctor/Poison Control, and state that a human is following up.\n"
            "3. If a handoff is required, you MUST include a sentence explicitly telling the customer: 'I have flagged this conversation for a human support representative who will follow up with you.'\n"
            "4. If the sentiment tone is 'annoyed' or 'furious', write a more empathetic, apologetic, and solution-focused reply."
        )

        facts_section = f"Grounded Product Facts:\n{grounded_facts}\n" if grounded_facts else "No matching product facts found.\n"
        unverifiable_section = f"Unverifiable Questions:\n{', '.join(unverifiable)}\n" if unverifiable else ""
        safety_section = f"Safety Concerns Flagged: {safety_triggered} (Reason: {safety_reason})\n"
        handoff_section = f"Human Handoff Triggered: {handoff_required}\n"
        tone_section = f"Customer Emotional Tone: {tone}\n"

        generation_prompt = (
            f"=== PIPELINE DECISIONS ===\n"
            f"{facts_section}"
            f"{unverifiable_section}"
            f"{safety_section}"
            f"{handoff_section}"
            f"{tone_section}\n"
            f"=== CURRENT MESSAGE ===\n"
            f"Customer: {message}\n\n"
            f"Write the response to the customer now. Stream it back directly."
        )

        # Stream actual reply (Step 9)
        full_reply = []
        async for text_chunk in self.llm_service.generate_stream(generation_prompt, system_instruction):
            full_reply.append(text_chunk)
            yield json.dumps({
                "type": "chunk",
                "text": text_chunk
            }) + "\n"

        # Step 8: Save history to DB
        if self.db_service:
            # Save user message
            await self.db_service.save_message(session_id, "user", message)
            # Save assistant response
            full_reply_str = "".join(full_reply)
            await self.db_service.save_message(session_id, "assistant", full_reply_str)