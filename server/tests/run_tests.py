import sys
import os
import asyncio

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.test_engine import (
    test_safety_agent_triggered,
    test_safety_agent_not_triggered,
    test_sentiment_agent_furious,
    test_sentiment_agent_calm,
    test_product_agent_search,
    test_product_agent_grounding,
    test_product_agent_semantic_search_used_when_llm_available,
    test_product_agent_semantic_search_skipped_in_mock_mode
)
from tests.test_storage import (
    test_session_persistence_across_restart,
    test_ticket_creation_and_retrieval
)
from tests.test_integration import (
    test_integration_safety_escalation,
    test_integration_angry_escalation
)
from src.services.llm_service import LLMService
from src.services.db_service import DBService

class SimpleFixture:
    def __init__(self, obj, teardown_fn=None):
        self.obj = obj
        self.teardown_fn = teardown_fn

    def close(self):
        if self.teardown_fn:
            self.teardown_fn()

def run_sync_test(name, test_fn, *args):
    print(f"Running {name}... ", end="", flush=True)
    try:
        test_fn(*args)
        print("PASSED")
        return True
    except Exception as e:
        print("FAILED")
        import traceback
        traceback.print_exc()
        return False

async def run_async_test(name, test_fn, *args):
    print(f"Running {name}... ", end="", flush=True)
    try:
        await test_fn(*args)
        print("PASSED")
        return True
    except Exception as e:
        print("FAILED")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("=== STARTING P&G CUSTOMER SUPPORT CHAT ASSISTANT TESTS ===")
    
    llm = LLMService()
    success = True

    # 1. Engine tests
    success &= run_sync_test("test_safety_agent_triggered", test_safety_agent_triggered, llm)
    success &= run_sync_test("test_safety_agent_not_triggered", test_safety_agent_not_triggered, llm)
    success &= run_sync_test("test_sentiment_agent_furious", test_sentiment_agent_furious, llm)
    success &= run_sync_test("test_sentiment_agent_calm", test_sentiment_agent_calm, llm)
    success &= run_sync_test("test_product_agent_search", test_product_agent_search, llm)
    success &= run_sync_test("test_product_agent_grounding", test_product_agent_grounding, llm)
    success &= run_sync_test("test_product_agent_semantic_search_used_when_llm_available", test_product_agent_semantic_search_used_when_llm_available, llm)
    success &= run_sync_test("test_product_agent_semantic_search_skipped_in_mock_mode", test_product_agent_semantic_search_skipped_in_mock_mode, llm)

    # 2. Storage tests
    db_path = "test_pg_support.db"
    def cleanup_db():
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass
    
    cleanup_db()
    db = DBService(db_path=db_path)
    success &= run_sync_test("test_session_persistence_across_restart", test_session_persistence_across_restart, db)
    cleanup_db()

    cleanup_db()
    db = DBService(db_path=db_path)
    success &= run_sync_test("test_ticket_creation_and_retrieval", test_ticket_creation_and_retrieval, db)
    cleanup_db()

    # 3. Integration tests
    integ_db_path = "test_integration.db"
    def cleanup_integ():
        if os.path.exists(integ_db_path):
            try:
                os.remove(integ_db_path)
            except Exception:
                pass

    cleanup_integ()
    integ_db = DBService(db_path=integ_db_path)
    success &= await run_async_test("test_integration_safety_escalation", test_integration_safety_escalation, integ_db)
    cleanup_integ()

    cleanup_integ()
    integ_db = DBService(db_path=integ_db_path)
    success &= await run_async_test("test_integration_angry_escalation", test_integration_angry_escalation, integ_db)
    cleanup_integ()

    print("=========================================================")
    if success:
        print("ALL TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print("SOME TESTS FAILED!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())