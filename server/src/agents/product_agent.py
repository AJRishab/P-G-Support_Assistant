import os
import json
import re
from pydantic import BaseModel, Field
from ..services.llm_service import LLMService

class ProductEvaluation(BaseModel):
    relevant_products_found: list[str] = Field(description="Names or IDs of matching products found.")
    grounded_summary: str = Field(description="Summary of facts specifically and only found in the provided product details, answering the customer's questions.")
    unverifiable_questions: list[str] = Field(description="Any customer questions that could not be verified or answered using the provided product details.")

class ProductMatch(BaseModel):
    matched_product_ids: list[str] = Field(
        description=(
            "IDs of catalog products that genuinely match the customer's underlying need, "
            "even if the message shares no exact keywords with the catalog entry. "
            "Return an empty list if nothing in the catalog is relevant."
        )
    )

class ProductAgent:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self.products = self._load_products()

    def _load_products(self) -> list:
        """
        Loads the trustworthy official products knowledge base.
        """
        current_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.abspath(os.path.join(current_dir, "..", "config", "products.json"))
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("products", [])
        except Exception as e:
            print(f"[ProductAgent Error] Failed to load products.json from {path}: {e}")
            return []

    def _keyword_search(self, query: str) -> list:
        """
        Fast, dependency-free lexical pass over the catalog: matches brand, name,
        category, and ingredients that are directly mentioned in the query.
        This is the only pass available in mock mode (no LLM to reason with), and
        it's always tried first even when a real LLM is configured, since it's free
        and instantly resolves the common case of the customer naming the brand/product.
        """
        query_lower = query.lower()
        matched = []
        
        # Define some mappings for common needs
        need_keywords = {
            "tide": ["tide", "laundry", "detergent", "wash", "stain", "grease", "clothes", "dirty"],
            "pampers": ["pampers", "diaper", "swim", "baby", "toddler", "leak", "splashers"],
            "olay": ["olay", "skincare", "skin", "moisturizer", "wrinkle", "face", "cream", "hydrate", "sensitive"],
            "gillette": ["gillette", "shave", "razor", "blade", "shaving", "exfoliate", "hair"]
        }

        # Check keyword associations
        matched_brands = set()
        for brand, keywords in need_keywords.items():
            for kw in keywords:
                if re.search(r'\b' + re.escape(kw) + r'\b', query_lower):
                    matched_brands.add(brand)
                    break

        for prod in self.products:
            # Direct text match or brand association
            is_match = False
            if prod["brand"].lower() in matched_brands:
                is_match = True
            elif any(re.search(r'\b' + re.escape(word) + r'\b', query_lower) for word in prod["name"].lower().split()):
                is_match = True
            elif prod["category"].lower() in query_lower:
                is_match = True
            elif any(ing.lower() in query_lower for ing in prod["ingredients"]):
                is_match = True

            if is_match:
                matched.append(prod)

        return matched

    def _semantic_search(self, query: str) -> list:
        """
        LLM-based retrieval pass: matches the query against the catalog by underlying
        need rather than exact words, catching paraphrases the keyword pass misses
        (e.g. "my face looks tired around the eyes" -> Olay, with no mention of
        "skin", "moisturizer", or the brand name).

        Only meaningful when a real LLM is configured. Callers should check
        `llm_service.use_mock` before calling this, and treat the result as
        best-effort, falling back to `_keyword_search` results on any failure.
        """
        catalog_brief = "\n".join(
            f"- id: {p['id']} | brand: {p['brand']} | category: {p['category']} | purpose: {p['purpose']}"
            for p in self.products
        )
        prompt = (
            "You are the retrieval step of the Product Agent for P&G Customer Support.\n"
            "Below is the full product catalog (id, brand, category, purpose). Decide which products, "
            "if any, genuinely match what the customer is describing - based on their underlying need, "
            "not just literal keyword overlap. Customers often describe a problem or symptom without "
            "naming the brand, category, or product type.\n\n"
            f"=== CATALOG ===\n{catalog_brief}\n\n"
            f"=== CUSTOMER MESSAGE ===\n\"{query}\"\n\n"
            "Return a JSON object with matched_product_ids. Only include a product if it truly answers "
            "the need described - return an empty list rather than guessing the closest available option."
        )
        result = self.llm_service.generate_json(prompt, schema_class=ProductMatch)
        matched_ids = set(result.get("matched_product_ids", []) or [])
        return [p for p in self.products if p["id"] in matched_ids]

    def search_catalog(self, query: str) -> list:
        """
        Step 2: Retrieves matching products for a customer query.

        Two-tier search:
        1. Keyword/brand match (fast, free, works with or without an LLM configured).
        2. If that finds nothing and a real LLM is available, an LLM-based semantic
           pass catches paraphrased or needs-based questions that share no keywords
           with the catalog. In mock mode this second tier is skipped entirely, since
           there is no real model available to reason with - the heuristic mock engine
           only knows how to fake the grounding step, not open-ended retrieval.
        """
        matched = self._keyword_search(query)
        if matched or getattr(self.llm_service, "use_mock", True):
            return matched

        try:
            return self._semantic_search(query)
        except Exception as e:
            print(f"[ProductAgent Error] Semantic search failed: {e}. Falling back to keyword results.")
            return matched

    def analyze_and_ground(self, message: str, conversation_history: list = None) -> dict:
        """
        Handles Step 2 (gather what it needs) and Step 3 (factual grounding).
        Queries the catalog and synthesizes the grounded answer, indicating what couldn't be answered.
        """
        # Step 2: Query catalog
        matched_products = self.search_catalog(message)
        
        # If history is present and no products were found, search on history too
        if not matched_products and conversation_history:
            recent_user_messages = [h["content"] for h in conversation_history[-3:] if h["role"] == "user"]
            for prev_msg in recent_user_messages:
                matched_products = self.search_catalog(prev_msg)
                if matched_products:
                    break

        if not matched_products:
            return {
                "relevant_products_found": [],
                "grounded_summary": "",
                "unverifiable_questions": ["No official product in our database matches your search. We cannot verify or answer your question."]
            }

        # Prepare context for Step 3 Grounding Check
        context_str = json.dumps(matched_products, indent=2)
        
        prompt = (
            "You are the Product Agent for P&G Customer Support.\n"
            "Your job is to answer customer questions using ONLY the official product information provided below.\n"
            "DO NOT assume, extrapolate, or invent any facts. If a detail is not explicitly stated in the context, "
            "mark it as an unverifiable question.\n\n"
            f"=== OFFICIAL PRODUCT CONTEXT ===\n{context_str}\n\n"
            f"=== CUSTOMER MESSAGE ===\n{message}\n\n"
            "Return a JSON object with:\n"
            "1. relevant_products_found: list of product names matched.\n"
            "2. grounded_summary: answer explaining ingredients, purpose, safety, or where to buy, drawing strictly from the context.\n"
            "3. unverifiable_questions: list of queries or details requested by the user that were NOT verifiable in the context."
        )

        try:
            result = self.llm_service.generate_json(prompt, schema_class=ProductEvaluation)
            return {
                "relevant_products_found": result.get("relevant_products_found", [p["name"] for p in matched_products]),
                "grounded_summary": result.get("grounded_summary", ""),
                "unverifiable_questions": result.get("unverifiable_questions", [])
            }
        except Exception as e:
            print(f"[ProductAgent Error] Grounding failed: {e}")
            # Mock fallback summary
            summary = self.llm_service._mock_text_response(message)
            return {
                "relevant_products_found": [p["name"] for p in matched_products],
                "grounded_summary": summary,
                "unverifiable_questions": []
            }