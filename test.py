from openai import OpenAI

# Your Cerebras API key
CEREBRAS_API_KEY = "csk-k22wvdn4n2dx8rey53wvyhn8j4yrvwvppwc55hyykmeeefwx"  # Replace with your actual key

client = OpenAI(
    api_key=CEREBRAS_API_KEY,
    base_url="https://api.cerebras.ai/v1"
)

print("Testing Cerebras API...")
print("=" * 60)

# Try different model names (Cerebras naming can vary)
models_to_try = [
    "gpt-oss-120b",
    "llama-3.3-70b",
    "qwen-3-235b-a22b-instruct-2507",
    "zai-glm-4.6"
]

for model_name in models_to_try:
    try:
        print(f"\nTrying model: {model_name}")
        response = client.chat.completions.create(
            model=model_name,
            messages=[{
                "role": "user",
                "content": "Explain inflation in 100 words."
            }],
            temperature=0.3,
            max_tokens=300
        )
        
        print("✅ SUCCESS!")
        print("=" * 60)
        print(response.choices[0].message.content)
        print("=" * 60)
        print(f"Working model: {model_name}")
        print(f"Tokens used: {response.usage.total_tokens}")
        break
        
    except Exception as e:
        print(f"❌ Failed: {str(e)[:100]}")
        continue