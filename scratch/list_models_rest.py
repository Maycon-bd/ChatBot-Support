import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY not found in environment.")
    exit(1)

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

try:
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        print("Models with embedContent support:")
        for model in data.get("models", []):
            methods = model.get("supportedGenerationMethods", [])
            if "embedContent" in methods:
                print(f"- {model.get('name')} (DisplayName: {model.get('displayName')})")
    else:
        print(f"Error listing models (HTTP {response.status_code}): {response.text}")
except Exception as e:
    print(f"Request error: {e}")
