#!/usr/bin/env python3
import os
from openai import OpenAI
from dotenv import load_dotenv

# Load API key from api.env
load_dotenv('Ai_conciel/api.env')

# Change this to test different models
MODEL_NAME = "Llama-3.3-Swallow-70B-Instruct-v0.4"

SAMBANOVA_API_KEY = os.environ.get("SAMBANOVA_API_KEY")

if not SAMBANOVA_API_KEY:
    print("Error: SAMBANOVA_API_KEY not found in api.env")
    exit(1)

client = OpenAI(
    api_key=SAMBANOVA_API_KEY,
    base_url="https://api.sambanova.ai/v1"
)

print(f"Testing model: {MODEL_NAME}")
print("-" * 60)

try:
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "user", "content": "Define inflation in one line"}
        ],
        max_tokens=100,
        temperature=0.3
    )
    
    result = response.choices[0].message.content
    print(f"SUCCESS: {result}")
    
except Exception as e:
    print(f"FAILED: {e}")

print("-" * 60)