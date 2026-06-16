import os
import sys
import logging
from pathlib import Path

# Adjust PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

from app.database import SessionLocal
from app.services.agent_service import AgentService
from app.seeder import seed_database

db = SessionLocal()
try:
    seed_database(db)
    
    agent = AgentService()
    print("Running agent test query...")
    result = agent.run_agent(
        db=db,
        conversation_id="conversa_demonstracao",
        tenant_id="quantum_corp",
        current_query="Como cadastrar um cliente no sistema ERP?"
    )
    print("\nRetrieved Context Chunks:")
    for i, ctx in enumerate(result.get("retrieved_context", []), 1):
        print(f"[{i}]: {ctx[:150]}...")
        
    print("\nAgent Response:")
    print(result.get("response"))
    print("\nToken Usage:")
    print(result.get("token_usage"))
except Exception as e:
    print("Error during agent test run:", e)
finally:
    db.close()
