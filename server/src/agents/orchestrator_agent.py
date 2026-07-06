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
        history = []
        if self.db_service:
            history = await self.db_service.get_history(session_id)

        pipeline_task = asyncio.gather(
            self.safety_agent.analyze(message),
            self.product_agent.analyze_and_ground(message, history),
            self.sentiment_agent.analyze(message),
        )

        yield json.dumps({
            "type": "progress", "agent": "Safety Agent", "status": "active",
            "message": "Safety Agent scanning message for health/exposure risks..."
        }) + "\n"
        await asyncio.sleep(0.4)

        yield json.dumps({
            "type": "progress", "agent": "Product Agent", "status": "active",
            "message": "Product Agent querying trustworthy database and checking grounding..."
        }) + "\n"
        await asyncio.sleep(0.4)

        yield json.dumps({
            "type": "progress", "agent": "Sentiment Agent", "status": "active",
            "message": "Sentiment Agent analyzing customer tone..."
        }) + "\n"
        await asyncio.sleep(0.4)

        safety_res, product_res, sentiment_res = await pipeline_task

        safety_triggered = safety_res.get("safety_triggered", False)
        safety_reason = safety_res.get("reason", "")
        urgency = safety_res.get("urgency", "low")

        grounded_facts = product_res.get("grounded_summary", "")
        unverifiable = product_res.get("unverifiable_questions", [])
        matched_names = product_res.get("relevant_products_found", [])
        fit_caveat = product_res.get("fit_caveat", "")

        tone = sentiment_res.get("tone", "calm")
        tone_is_negative = tone in ["annoyed", "furious"]
        handoff_required = safety_triggered or tone_is_negative

        if handoff_required:
            reason = "Safety Concern" if safety_triggered else f"Negative Tone ({tone})"
            if safety_triggered and tone_is_negative:
                reason = f"Safety Concern & Negative Tone ({tone})"

            ticket_urgency = urgency if safety_triggered else ("high" if tone == "furious" else "medium")

            yield json.dumps({
                "type": "progress", "agent": "Orchestrator Agent", "status": "active",
                "message": f"Orchestrator Agent triggering human agent hand-off (Reason: {reason})..."
            }) + "\n"
            await asyncio.sleep(0.4)

            if self.db_service:
                await self.db_service.create_ticket(
                    session_id=session_id, user_message=message, reason=reason,
                    tone=tone, urgency=ticket_urgency
                )

        yield json.dumps({
            "type": "progress", "agent": "Orchestrator Agent", "status": "done",
            "message": "All agents reports gathered. Generating reply..."
        }) + "\n"
        await asyncio.sleep(0.2)

        system_instruction = (
            "You are the final response compiler for P&G Customer Support.\n"
            "You must generate a response that is helpful, strictly grounded in the official facts provided, "
            "and adjusts its tone based on the sentiment classification.\n"
            "Rules:\n"
            "1. NEVER invent any facts, ingredients, or claims about products. If information is not provided in the facts, state clearly and honestly that we cannot verify it.\n"
            "2. NEVER diagnose, prescribe dosages, or give medical advice. If a safety concern is flagged, tell the customer to stop use, consult a doctor/Poison Control, and state that a human is following up.\n"
            "3. If a handoff is required, you MUST include a sentence explicitly telling the customer: 'I have flagged this conversation for a human support representative who will follow up with you.'\n"
            "4. If the sentiment tone is 'annoyed' or 'furious', write a more empathetic, apologetic, and solution-focused reply.\n"
            "5. If a Product Fit Caveat is present, say so plainly before giving the product's facts - don't present a mismatched product's specs as if they fully answer the customer's question."
        )

        facts_section = f"Grounded Product Facts:\n{grounded_facts}\n" if grounded_facts else "No matching product facts found.\n"
        caveat_section = f"Product Fit Caveat: {fit_caveat}\n" if fit_caveat else ""
        unverifiable_section = f"Unverifiable Questions:\n{', '.join(unverifiable)}\n" if unverifiable else ""
        safety_section = f"Safety Concerns Flagged: {safety_triggered} (Reason: {safety_reason})\n"
        handoff_section = f"Human Handoff Triggered: {handoff_required}\n"
        tone_section = f"Customer Emotional Tone: {tone}\n"

        generation_prompt = (
            f"=== PIPELINE DECISIONS ===\n"
            f"{facts_section}"
            f"{caveat_section}"
            f"{unverifiable_section}"
            f"{safety_section}"
            f"{handoff_section}"
            f"{tone_section}\n"
            f"=== CURRENT MESSAGE ===\n"
            f"Customer: {message}\n\n"
            f"Write the response to the customer now. Stream it back directly."
        )

        mock_context = {
            "safety_triggered": safety_triggered,
            "tone": tone,
            "handoff_required": handoff_required,
            "product_name": matched_names[0] if matched_names else None,
            "grounded_summary": grounded_facts,
            "fit_caveat": fit_caveat,
        }

        full_reply = []
        async for text_chunk in self.llm_service.generate_stream(generation_prompt, system_instruction, mock_context):
            full_reply.append(text_chunk)
            yield json.dumps({"type": "chunk", "text": text_chunk}) + "\n"

        if self.db_service:
            await self.db_service.save_message(session_id, "user", message)
            full_reply_str = "".join(full_reply)
            await self.db_service.save_message(session_id, "assistant", full_reply_str)