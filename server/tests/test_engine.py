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
    # Uses mock mode if OPENROUTER_API_KEY is not set
    return LLMService()

@pytest.mark.asyncio
async def test_safety_agent_triggered(llm_service):
    safety_agent = SafetyAgent(llm_service)
    
    # Urgent safety ingestion query
    res = await safety_agent.analyze("My toddler swallowed a Tide pod. What should I do?")
    assert res["safety_triggered"] is True
    assert res["urgency"] == "high"

    # Calm safety query
    res2 = await safety_agent.analyze("I developed a severe allergic skin rash after using Gillette blades.")
    assert res2["safety_triggered"] is True
    assert res2["urgency"] in ["medium", "high"]

@pytest.mark.asyncio
async def test_safety_agent_not_triggered(llm_service):
    safety_agent = SafetyAgent(llm_service)
    
    res = await safety_agent.analyze("Where can I buy Tide detergent online?")
    assert res["safety_triggered"] is False

@pytest.mark.asyncio
async def test_sentiment_agent_furious(llm_service):
    sentiment_agent = SentimentAgent(llm_service)
    
    res = await sentiment_agent.analyze("This olay product is garbage and absolute trash! I am going to sue you!")
    assert res["tone"] == "furious"

@pytest.mark.asyncio
async def test_sentiment_agent_calm(llm_service):
    sentiment_agent = SentimentAgent(llm_service)
    
    res = await sentiment_agent.analyze("Can you recommend a skincare product for sensitive skin?")
    assert res["tone"] == "calm"

@pytest.mark.asyncio
async def test_product_agent_search(llm_service):
    product_agent = ProductAgent(llm_service)
    
    # Keyword search Tide
    tide_prods = await product_agent.search_catalog("Tide detergent details")
    assert len(tide_prods) > 0
    assert tide_prods[0]["brand"] == "Tide"

    # Keyword search sensitive skin (should find Olay)
    olay_prods = await product_agent.search_catalog("sensitive skin moisturizer")
    assert len(olay_prods) > 0
    assert any(p["brand"] == "Olay" for p in olay_prods)

@pytest.mark.asyncio
async def test_product_agent_grounding(llm_service):
    product_agent = ProductAgent(llm_service)
    res = await product_agent.analyze_and_ground("What are the ingredients in Tide Hygienic Clean?")
    
    # Grounded response should contain the ingredients or summary
    assert len(res["relevant_products_found"]) > 0
    assert "Sodium Borate" in res["grounded_summary"] or "Sodium Alcoholethoxy Sulfate" in res["grounded_summary"]

@pytest.mark.asyncio
async def test_product_agent_semantic_search_used_when_llm_available(llm_service):
    """
    "I look tired around the eyes lately, is there anything for that?" shares no
    keywords with any catalog entry (no "skin", "moisturizer", "face", "olay",
    etc.), so the keyword pass genuinely comes back empty. Once a real LLM is
    configured, search_catalog should escalate to the semantic pass and trust
    its judgement.

    The LLM call itself is stubbed (not the network) so this test has no
    external dependency. It also asserts the stub was actually invoked, so a
    coincidental keyword match can't make this pass for the wrong reason.
    """
    product_agent = ProductAgent(llm_service)
    query = "I look tired around the eyes lately, is there anything for that?"

    # Sanity check the test's own premise: keyword pass alone finds nothing here.
    assert product_agent._keyword_search(query) == []

    original_use_mock = llm_service.use_mock
    original_generate_json = llm_service.generate_json
    call_count = {"n": 0}
    async def fake_generate_json(prompt, schema_class=None):
        call_count["n"] += 1
        return {"matched_product_ids": ["olay-regenerist-whip"]}
    try:
        llm_service.use_mock = False  # simulate a configured real API key
        llm_service.generate_json = fake_generate_json

        results = await product_agent.search_catalog(query)
        assert call_count["n"] == 1  # proves the semantic pass actually ran
        assert len(results) == 1
        assert results[0]["brand"] == "Olay"
    finally:
        llm_service.use_mock = original_use_mock
        llm_service.generate_json = original_generate_json

@pytest.mark.asyncio
async def test_product_agent_semantic_search_skipped_in_mock_mode(llm_service):
    """
    In mock mode there is no real model to reason with, so search_catalog must
    never attempt the semantic pass - even for phrasing the keyword list misses.
    A keyword miss in mock mode should just return no results, not call the LLM.
    """
    product_agent = ProductAgent(llm_service)
    assert llm_service.use_mock is True  # no OPENROUTER_API_KEY in this test env
    query = "I look tired around the eyes lately, is there anything for that?"
    assert product_agent._keyword_search(query) == []

    original_generate_json = llm_service.generate_json
    async def fail_if_called(prompt, schema_class=None):
        raise AssertionError("generate_json must not be called for semantic search in mock mode")
    try:
        llm_service.generate_json = fail_if_called
        results = await product_agent.search_catalog(query)
        assert results == []
    finally:
        llm_service.generate_json = original_generate_json