import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

from pathlib import Path

# Load dotenv using absolute path
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / '.env')

api_key = os.environ.get("GROQ_API_KEY")
model_name = os.environ.get("GROQ_MODEL", "llama-3.3-70b-specdec")
print("Groq API Key loaded (first 5 chars):", api_key[:5] if api_key else "None")
print("Groq Model:", model_name)

try:
    llm = ChatGroq(model_name=model_name, groq_api_key=api_key, temperature=0)
    res = llm.invoke([HumanMessage(content="Hello! Respond with 'OK' if you can read this.")])
    print("Success!")
    print("Response:", res.content)
except Exception as e:
    print("Error details:")
    print(e)
