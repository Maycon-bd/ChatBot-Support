import os
import sys
import traceback
from dotenv import load_dotenv

load_dotenv()

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal
from app.services.agent_service import AgentService

print("Initializing database session...")
db = SessionLocal()

try:
    print("Running AgentService.run_agent...")
    agent_service = AgentService()
    result = agent_service.run_agent(
        db=db,
        conversation_id="conversa_demonstracao",
        tenant_id="quantum_corp",
        current_query="Como resolver o erro Schrödinger State Ambiguity?"
    )
    print("Success! Result:")
    print(result)
except Exception as e:
    print("Error occurred:")
    traceback.print_exc()
finally:
    db.close()
