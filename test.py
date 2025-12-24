import os
from openai import OpenAI

# IMPORTANT: Move this to your api.env file and revoke the old key!
DEEPSEEK_API_KEY = "sk-9088ca44395849018d3850ac75aaf2cb"

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{
        "role": "user", 
        "content": "Explain what inflation is in the context of macroeconomics and gold markets. Be concise and quantitative."
    }],
    temperature=0.3
)

print(response.choices[0].message.content)