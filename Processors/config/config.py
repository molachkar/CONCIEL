import os
from pathlib import Path

TEXT_DIR = Path(r"C:\\Users\\PC\\Desktop\\CONCIEL\\TEXT")
DATA_DIR = TEXT_DIR / "data_by_date"
MONTHLY_REF_DIR = DATA_DIR / "_monthly_reference"

PROCESSORS_DIR = Path(r"C:\\Users\\PC\\Desktop\\CONCIEL\\Processors")
AGENT_OUTPUT_DIR = PROCESSORS_DIR / "agent_outputs"
MACRO_STRUCTURED_DIR = PROCESSORS_DIR / "macro_structured"

AGENT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MACRO_STRUCTURED_DIR.mkdir(parents=True, exist_ok=True)

API_KEYS = {
    "google": os.getenv("GOOGLE_API_KEY", "AIzaSyBfFPvJcEknAw2BPn-4KCbkkhWb08P5eBc"),
    "cerebras": os.getenv("CEREBRAS_API_KEY", "csk-k22wvdn4n2dx8rey53wvyhn8j4yrvwvppwc55hyykmeeefwx"),
    "sambanova": os.getenv("SAMBANOVA_API_KEY", "7950ff15-0c72-46ca-9322-052b2e4ac162"),
    "groq": os.getenv("GROQ_API_KEY", "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"),
}

AGENT_CONFIGS = {
    "macro": {"name": "macro", "description": "Economic events, rates, inflation, Fed policy", "model": "Qwen-235B", "provider": "cerebras", "api_endpoint": "https://api.cerebras.ai/v1/chat/completions", "files": ["calendar.txt", "fundamentals.txt"], "uses_monthly_data": True, "temperature": 0.2, "max_tokens": 2000, "priority": "HIGH"},
    "market": {"name": "market", "description": "Technical indicators and volatility analysis", "model": "deepseek-r1-distill-llama-70b", "provider": "cerebras", "api_endpoint": "https://api.cerebras.ai/v1/chat/completions", "files": ["technicals.txt", "calculos.txt"], "uses_monthly_data": False, "temperature": 0.3, "max_tokens": 2000, "priority": "VERY_HIGH"},
    "narrative": {"name": "narrative", "description": "News headlines and social sentiment", "model": "Meta-Llama-3.3-70B", "provider": "sambanova", "api_endpoint": "https://api.sambanova.ai/v1/chat/completions", "files": ["news.txt", "forums.txt"], "uses_monthly_data": False, "temperature": 0.4, "max_tokens": 2000, "priority": "HIGH"}
}

MEMORY_CONFIG = {"recent_days": 7, "medium_days": 14, "long_days": 9, "total_window": 30}

DAILY_FILES = ["calendar.txt", "fundamentals.txt", "technicals.txt", "calculos.txt", "news.txt", "forums.txt"]
MONTHLY_DATA_FILE = "monthly_fundamentals.txt"

PROCESSING_CONFIG = {"skip_weekends": True, "skip_missing_data": True, "require_all_files": False, "parallel_agents": False, "retry_on_api_fail": True, "max_retries": 3, "retry_delay": 5}

OUTPUT_CONFIG = {"save_individual_agents": True, "save_combined_output": True, "save_human_readable": True, "pretty_print_json": True, "log_processing_time": True}

REGIME_LABELS = {"RISK_ON": "Risk-on environment (supportive for gold)", "RISK_OFF": "Risk-off environment (headwinds for gold)", "NEUTRAL": "Neutral/consolidation environment"}

VALIDATION_CONFIG = {"require_regime_label": True, "require_confidence_score": True, "min_confidence": 0.0, "max_confidence": 1.0, "require_key_drivers": True, "min_key_drivers": 1, "max_key_drivers": 10}

def get_agent_config(agent_name):
    if agent_name not in AGENT_CONFIGS:
        raise ValueError(f"Unknown agent: {agent_name}")
    return AGENT_CONFIGS[agent_name]

def get_api_key(provider):
    return API_KEYS.get(provider, "")

def get_data_path(date):
    return DATA_DIR / date

def get_agent_output_path(agent_name, date):
    agent_dir = AGENT_OUTPUT_DIR / agent_name
    agent_dir.mkdir(exist_ok=True)
    return agent_dir / f"{date}.json"

def get_monthly_data_path():
    return MONTHLY_REF_DIR / MONTHLY_DATA_FILE

def validate_paths():
    issues = []
    if not DATA_DIR.exists():
        issues.append(f"Data directory not found: {DATA_DIR}")
    if not MONTHLY_REF_DIR.exists():
        issues.append(f"Monthly reference directory not found: {MONTHLY_REF_DIR}")
    if issues:
        for issue in issues:
            print(issue)
        return False
    return True

if __name__ == "__main__":
    validate_paths()
    for provider, key in API_KEYS.items():
        print(f"{provider}: {'SET' if key else 'MISSING'}")
    print("\ndone")