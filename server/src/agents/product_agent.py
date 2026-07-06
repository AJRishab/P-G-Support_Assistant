import os
import json
import re
from pydantic import BaseModel, Field
from ..services.llm_service import LLMService


class ProductEvaluation(BaseModel):
    relevant_products_found: list[str] = Field(description="Names or IDs of matching products found.")
    grounded_summary: str = Field(description="Summary of facts specifically and only found in the provided product details, answering the customer's questions.")
    unverifiable_questions: list[str] = Field(description="Any customer questions that could not be verified or answered using the provided product details.")
    fit_caveat: str = Field(description=(
        "If the matched product's actual purpose is narrower or different than what the customer "
        "described needing, state that mismatch plainly here. Empty string if it's a clean fit."
    ))


class ProductMatch(BaseModel):
    matched_product_ids: list[str] = Field(description=(
        "IDs of catalog products that genuinely match the customer's underlying need, even if "
        "the message shares no exact keywords with the catalog entry. Empty list if nothing fits."
    ))


class ProductAgent:
    # Category-level signals only. Brand matching is dynamic (built from whatever's actually
    # loaded in products.json) so it scales past a fixed 4-brand list to a real data-driven catalog.
    CATEGORY_KEYWORDS = {
        "Detergent": ["laundry", "detergent", "wash", "stain", "grease", "clothes", "dirty"],
        "Baby Care": ["diaper", "swim", "baby", "toddler", "leak", "splashers"],
        "Skincare": ["skincare", "skin", "moisturizer", "wrinkle", "face", "cream", "hydrate",
                     "cleanser", "serum", "toner", "lotion"],
        "Shaving": ["shave", "razor", "blade", "shaving", "exfoliate", "hair"],
    }

    SKIN_TYPE_KEYWORDS = {
        "Sensitive": ["sensitive"],
        "Dry": ["dry skin", "dryness", "flaky"],
        "Oily": ["oily skin", "oily", "greasy"],
        "Combination": ["combination skin", "combination"],
        "Normal": ["normal skin"],
    }

    MAX_MATCHES = 5  # caps how many products get stuffed into one grounding prompt

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self.products = self._load_products()

    def _load_products(self) -> list:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.abspath(os.path.join(current_dir, "..", "config", "products.json"))
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f).get("products", [])
        except Exception as e:
            print(f"[ProductAgent Error] Failed to load products.json from {path}: {e}")
            return []

    def _keyword_search(self, query: str) -> list:
        query_lower = query.lower()

        matched_brands = {
            prod["brand"].lower() for prod in self.products
            if re.search(r'\b' + re.escape(prod["brand"].lower()) + r'\b', query_lower)
        }
        matched_categories = {
            category for category, keywords in self.CATEGORY_KEYWORDS.items()
            if any(re.search(r'\b' + re.escape(kw) + r'\b', query_lower) for kw in keywords)
        }
        matched_skin_types = {
            skin_type for skin_type, keywords in self.SKIN_TYPE_KEYWORDS.items()
            if any(kw in query_lower for kw in keywords)
        }

        matched = []
        for prod in self.products:
            is_match = (
                prod["brand"].lower() in matched_brands
                or prod["category"] in matched_categories
                or any(re.search(r'\b' + re.escape(w) + r'\b', query_lower) for w in prod["name"].lower().split())
                or any(ing.lower() in query_lower for ing in prod.get("ingredients", []))
            )
            if is_match:
                matched.append(prod)

        # The actual fix for the original bug, now backed by real per-product data: if the
        # query names a skin type, prefer Skincare products tagged for it over ones that aren't.
        if matched_skin_types:
            skin_filtered = [
                p for p in matched
                if p["category"] != "Skincare" or matched_skin_types & set(p.get("skin_types", []))
            ]
            if skin_filtered:
                matched = skin_filtered

        matched.sort(key=lambda p: p.get("rank", 0), reverse=True)
        return matched[: self.MAX_MATCHES]

    def _has_need_signal(self, query: str) -> bool:
        query_lower = query.lower()
        all_keywords = [kw for kws in self.CATEGORY_KEYWORDS.values() for kw in kws]
        return any(re.search(r'\b' + re.escape(kw) + r'\b', query_lower) for kw in all_keywords)

    async def _semantic_search(self, query: str) -> list:
        catalog_brief = "\n".join(
            f"- id: {p['id']} | brand: {p['brand']} | category: {p['category']} | purpose: {p['purpose']}"
            for p in self.products
        )
        prompt = (
            "You are the retrieval step of the Product Agent for P&G Customer Support.\n"
            "Below is the full product catalog. Decide which products, if any, genuinely match "
            "the customer's underlying need, not just literal keyword overlap.\n\n"
            f"=== CATALOG ===\n{catalog_brief}\n\n"
            f"Customer Message: \"{query}\"\n\n"
            "Return a JSON object with matched_product_ids. Empty list rather than guessing."
        )
        result = await self.llm_service.generate_json(prompt, schema_class=ProductMatch)
        matched_ids = set(result.get("matched_product_ids", []) or [])
        return [p for p in self.products if p["id"] in matched_ids][: self.MAX_MATCHES]

    async def search_catalog(self, query: str) -> list:
        matched = self._keyword_search(query)
        if matched or getattr(self.llm_service, "use_mock", True):
            return matched
        try:
            return await self._semantic_search(query)
        except Exception as e:
            print(f"[ProductAgent Error] Semantic search failed: {e}. Falling back to keyword results.")
            return matched

    async def analyze_and_ground(self, message: str, conversation_history: list = None) -> dict:
        matched_products = await self.search_catalog(message)

        if not matched_products and conversation_history and not self._has_need_signal(message):
            recent_user_messages = [h["content"] for h in conversation_history[-3:] if h["role"] == "user"]
            for prev_msg in recent_user_messages:
                matched_products = await self.search_catalog(prev_msg)
                if matched_products:
                    break

        if not matched_products:
            return {
                "relevant_products_found": [],
                "grounded_summary": "",
                "unverifiable_questions": ["No official product in our database matches your search. We cannot verify or answer your question."],
                "fit_caveat": "",
            }

        context_str = json.dumps(matched_products, indent=2)
        prompt = (
            "You are the Product Agent for P&G Customer Support.\n"
            "Answer using ONLY the official product information below. DO NOT assume, extrapolate, "
            "or invent facts. If a detail isn't explicitly stated (including safety warnings or "
            "where to buy, if blank), mark it as unverifiable rather than guessing.\n\n"
            "Some products include a skin_types field (Sensitive, Dry, Oily, Combination, Normal) - "
            "use it directly when the customer mentions their skin type.\n\n"
            "Separately, check fit: does this product's stated purpose actually match what the "
            "customer described needing? If not, say so plainly in fit_caveat.\n\n"
            f"=== OFFICIAL PRODUCT CONTEXT ===\n{context_str}\n\n"
            f"Customer Message: \"{message}\"\n\n"
            "Return a JSON object with relevant_products_found, grounded_summary, unverifiable_questions, and fit_caveat."
        )

        try:
            result = await self.llm_service.generate_json(prompt, schema_class=ProductEvaluation)
            return {
                "relevant_products_found": result.get("relevant_products_found", [p["name"] for p in matched_products]),
                "grounded_summary": result.get("grounded_summary", ""),
                "unverifiable_questions": result.get("unverifiable_questions", []),
                "fit_caveat": result.get("fit_caveat", ""),
            }
        except Exception as e:
            print(f"[ProductAgent Error] Grounding failed: {e}")
            return {
                "relevant_products_found": [p["name"] for p in matched_products],
                "grounded_summary": f"{matched_products[0]['name']}: {matched_products[0]['purpose']}",
                "unverifiable_questions": [],
                "fit_caveat": "",
            }