import os
import sys

key = os.environ.get("GEMINI_API_KEY", "")

from google import genai

client = genai.Client(api_key=key)

for model_name in ["gemini-2.5-flash", "gemini-2.0-flash"]:
    try:
        print(f"Trying model: {model_name}...")
        response = client.models.generate_content(
            model=model_name,
            contents="Explain how AI works in a few words",
        )
        print("Success!")
        print(f"Response:\n{response.text}\n")
        break
    except Exception as e:
        print(f"Model {model_name} error: {e}")
