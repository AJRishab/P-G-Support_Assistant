import os
import sys
import pytest

# Add src to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services.llm_service import LLMService
from src.agents.safety_agent import SafetyAgent
from src.agents.sentiment_agent import SentimentAgent
from src.agents.product_agent import ProductAgent

@pytest.fixture
def llm_service():
    # Uses mock mode if GEMINI_API_KEY is not set
    return LLMService()

def test_safety_agent_triggered(llm_service):
    safety_agent = SafetyAgent(llm_service)
    
    # Urgent safety ingestion query
    res = safety_agent.analyze("My toddler swallowed a Tide pod. What should I do?")
    assert res["safety_triggered"] is True
    assert res["urgency"] == "high"

    # Calm safety query
    res2 = safety_agent.analyze("I developed a severe allergic skin rash after using Gillette blades.")
    assert res2["safety_triggered"] is True
    assert res2["urgency"] in ["medium", "high"]

def test_safety_agent_not_triggered(llm_service):
    safety_agent = SafetyAgent(llm_service)
    
    res = safety_agent.analyze("Where can I buy Tide detergent online?")
    assert res["safety_triggered"] is False

def test_sentiment_agent_furious(llm_service):
    sentiment_agent = SentimentAgent(llm_service)
    
    res = sentiment_agent.analyze("This olay product is garbage and absolute trash! I am going to sue you!")
    assert res["tone"] == "furious"

def test_sentiment_agent_calm(llm_service):
    sentiment_agent = SentimentAgent(llm_service)
    
    res = sentiment_agent.analyze("Can you recommend a skincare product for sensitive skin?")
    assert res["tone"] == "calm"

def test_product_agent_search(llm_service):
    product_agent = ProductAgent(llm_service)
    
    # Keyword search Tide
    tide_prods = product_agent.search_catalog("Tide detergent details")
    assert len(tide_prods) > 0
    assert tide_prods[0]["brand"] == "Tide"

    # Keyword search sensitive skin (should find Olay)
    olay_prods = product_agent.search_catalog("sensitive skin moisturizer")
    assert len(olay_prods) > 0
    assert any(p["brand"] == "Olay" for p in olay_prods)

def test_product_agent_grounding(llm_service):
    product_agent = ProductAgent(llm_service)
    res = product_agent.analyze_and_ground("What are the ingredients in Tide Hygienic Clean?")
    
    # Grounded response should contain the ingredients or summary
    assert len(res["relevant_products_found"]) > 0
    assert "Sodium Borate" in res["grounded_summary"] or "Sodium Alcoholethoxy Sulfate" in res["grounded_summary"]
