import os
from pathlib import Path

PROCESSORS_DIR = Path(r"C:\Users\PC\Desktop\CONCIEL\Processors")
MACRO_STRUCTURED_DIR = PROCESSORS_DIR / "macro_structured"
REPORTS_DIR = PROCESSORS_DIR / "reports"
REPORTS_WORKING_DIR = REPORTS_DIR / "working"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_WORKING_DIR.mkdir(parents=True, exist_ok=True)

API_KEYS = {
    "sambanova": os.getenv("SAMBANOVA_API_KEY", "7950ff15-0c72-46ca-9322-052b2e4ac162"),
    "cerebras": os.getenv("CEREBRAS_API_KEY", "csk-k22wvdn4n2dx8rey53wvyhn8j4yrvwvppwc55hyykmeeefwx"),
    "groq": os.getenv("GROQ_API_KEY", "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"),
}

REPORT_LLM_FALLBACKS = [
    {
        "name": "Meta-Llama-3.3-70B-Instruct",
        "provider": "sambanova",
        "api_endpoint": "https://api.sambanova.ai/v1/chat/completions",
        "max_tokens": 16000,
        "priority": 1
    },
    {
        "name": "llama3.3-70b",
        "provider": "cerebras",
        "api_endpoint": "https://api.cerebras.ai/v1/chat/completions",
        "max_tokens": 8000,
        "priority": 2
    },
    {
        "name": "DeepSeek-V3-0324",
        "provider": "sambanova",
        "api_endpoint": "https://api.sambanova.ai/v1/chat/completions",
        "max_tokens": 16000,
        "priority": 3
    },
    {
        "name": "llama-3.3-70b-versatile",
        "provider": "groq",
        "api_endpoint": "https://api.groq.com/openai/v1/chat/completions",
        "max_tokens": 8000,
        "priority": 4
    },
    {
        "name": "Qwen2.5-72B-Instruct",
        "provider": "sambanova",
        "api_endpoint": "https://api.sambanova.ai/v1/chat/completions",
        "max_tokens": 8000,
        "priority": 5
    }
]

STICKY_MODEL_CONFIG = {
    "enabled": True,
    "persist_across_agents": True,
}

REPORT_CONFIG = {
    "agent1_char_budget": 15000,
    "agent2_char_budget": 15000,
    "agent3_char_budget": 18000,
    "temperature": 0.3,
    "timeout": 180,
}

CHARS_PER_PAGE = 3000

def get_report_path(start_date: str, end_date: str) -> Path:
    return REPORTS_DIR / f"report_{start_date}_{end_date}.txt"

def get_working_file(agent_name: str, start_date: str, end_date: str) -> Path:
    return REPORTS_WORKING_DIR / f"{agent_name}_{start_date}_{end_date}.txt"