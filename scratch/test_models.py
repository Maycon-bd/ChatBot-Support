import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY")
print("API Key loaded (first 5 chars):", api_key[:5] if api_key else "None")

models_to_test = [
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash",
    "gemini-3.5-flash",
    "gemini-flash-latest",
]

for model_name in models_to_test:
    print(f"\n--- Testing model: {model_name} ---")
    try:
        llm = ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key, temperature=0)
        res = llm.invoke([HumanMessage(content="Hello! Respond with 'OK' if you can read this.")])
        print("Success!")
        print("Response:", res.content)
    except Exception as e:
        print("Error details:")
        print(e)
