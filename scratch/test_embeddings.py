import os
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY")

models_to_try = [
    "models/gemini-embedding-001",
    "models/gemini-embedding-2",
]

for model in models_to_try:
    print(f"\nTrying model: {model}")
    try:
        embeddings = GoogleGenerativeAIEmbeddings(
            model=model,
            google_api_key=api_key
        )
        vector = embeddings.embed_query("Teste de conexão")
        print(f"Success! Vector length: {len(vector)}")
    except Exception as e:
        print(f"Error: {e}")
