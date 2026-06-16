import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=api_key)

print("Listing models:")
try:
    for model in genai.list_models():
        if "embedContent" in model.supported_generation_methods:
            print(f"- {model.name} (methods: {model.supported_generation_methods})")
except Exception as e:
    print(f"Error: {e}")
