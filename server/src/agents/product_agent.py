import os
import json
import re
from pydantic import BaseModel, Field
from ..services.llm_service import LLMService

class ProductEvaluation(BaseModel):
    relevant_products_found: list[str] = Field(description="Names or IDs of matching products found.")
    grounded_summary: str = Field(description="Summary of facts specifically and only found in the provided product details, answering the customer's questions.")
    unverifiable_questions: list[str] = Field(description="Any customer questions that could not be verified or answered using the provided product details.")

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

    def search_catalog(self, query: str) -> list:
        """
        Performs a keyword-based search on the product catalog.
        Matches brand, name, category, purpose, and ingredients.
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
            prod_str = json.dumps(prod).lower()
            
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
