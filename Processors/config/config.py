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
    "sambanova": os.getenv("SAMBANOVA_API_KEY", "7950ff15-0c72-46ca-9322-052b2e4ac162"),
    "cerebras": os.getenv("CEREBRAS_API_KEY", "csk-k22wvdn4n2dx8rey53wvyhn8j4yrvwvppwc55hyykmeeefwx"),
    "groq": os.getenv("GROQ_API_KEY", "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"),
}

# Fallback model configurations for market agent (when primary model hits token limit)
MARKET_FALLBACK_MODELS = [
    {
        "name": "DeepSeek-V3.1",
        "provider": "sambanova",
        "api_endpoint": "https://api.sambanova.ai/v1/chat/completions",
        "max_tokens": 2000,
        "priority": 1
    },
    {
        "name": "Meta-Llama-3.3-70B",
        "provider": "sambanova", 
        "api_endpoint": "https://api.sambanova.ai/v1/chat/completions",
        "max_tokens": 2000,
        "priority": 2
    },
    {
        "name": "DeepSeek-V3-0324",
        "provider": "sambanova",
        "api_endpoint": "https://api.sambanova.ai/v1/chat/completions",
        "max_tokens": 2000,
        "priority": 3
    },
    {
        "name": "gpt-oss-120b",
        "provider": "sambanova",
        "api_endpoint": "https://api.sambanova.ai/v1/chat/completions",
        "max_tokens": 2000,
        "priority": 4
    },
    {
        "name": "Llama-Swallow",
        "provider": "sambanova",
        "api_endpoint": "https://api.sambanova.ai/v1/chat/completions",
        "max_tokens": 2000,
        "priority": 5
    }
]

# Fallback model configurations for macro agent
MACRO_FALLBACK_MODELS = [
    {
        "name": "llama3.3-70b",
        "provider": "cerebras",
        "api_endpoint": "https://api.cerebras.ai/v1/chat/completions",
        "max_tokens": 2000,
        "priority": 1
    },
    {
        "name": "Meta-Llama-3.3-70B",
        "provider": "sambanova",
        "api_endpoint": "https://api.sambanova.ai/v1/chat/completions",
        "max_tokens": 2000,
        "priority": 2
    },
    {
        "name": "DeepSeek-V3-0324",
        "provider": "sambanova",
        "api_endpoint": "https://api.sambanova.ai/v1/chat/completions",
        "max_tokens": 2000,
        "priority": 3
    }
]

# Fallback model configurations for narrative agent
NARRATIVE_FALLBACK_MODELS = [
    {
        "name": "Meta-Llama-3.3-70B-Instruct",
        "provider": "sambanova",
        "api_endpoint": "https://api.sambanova.ai/v1/chat/completions",
        "max_tokens": 2000,
        "priority": 1
    },
    {
        "name": "llama3.3-70b",
        "provider": "cerebras",
        "api_endpoint": "https://api.cerebras.ai/v1/chat/completions",
        "max_tokens": 2000,
        "priority": 2
    },
    {
        "name": "DeepSeek-V3-0324",
        "provider": "sambanova",
        "api_endpoint": "https://api.sambanova.ai/v1/chat/completions",
        "max_tokens": 2000,
        "priority": 3
    }
]

# Sticky model configuration (persist working model for N days before retrying primary)
STICKY_MODEL_CONFIG = {
    "enabled": True,
    "retry_primary_after_days": 10,  # After 10 successful days, retry primary model
    "reset_on_failure": True  # Reset to full fallback chain when sticky model fails
}

AGENT_CONFIGS = {
    "market": {
        "name": "market",
        "description": "Technical indicators and volatility analysis",
        "model": "DeepSeek-V3.1",
        "provider": "sambanova",
        "api_endpoint": "https://api.sambanova.ai/v1/chat/completions",
        "files": ["technicals.txt", "calculos.txt"],
        "uses_monthly_data": False,
        "temperature": 0.3,
        "max_tokens": 2000,
        "priority": "VERY_HIGH"
    },
    "macro": {
        "name": "macro",
        "description": "Economic events, rates, inflation, Fed policy",
        "model": "Qwen-235B",
        "provider": "cerebras",
        "api_endpoint": "https://api.cerebras.ai/v1/chat/completions",
        "files": ["calendar.txt", "fundamentals.txt"],
        "uses_monthly_data": True,
        "temperature": 0.2,
        "max_tokens": 2000,
        "priority": "HIGH"
    },
    "narrative": {
        "name": "narrative",
        "description": "News headlines and social sentiment",
        "model": "Meta-Llama-3.3-70B",
        "provider": "sambanova",
        "api_endpoint": "https://api.sambanova.ai/v1/chat/completions",
        "files": ["news.txt", "forums.txt"],
        "uses_monthly_data": False,
        "temperature": 0.4,
        "max_tokens": 2000,
        "priority": "HIGH"
    }
}

MEMORY_CONFIG = {
    "recent_days": 7,
    "medium_days": 14,
    "long_days": 9,
    "total_window": 30
}

DAILY_FILES = [
    "calendar.txt",
    "fundamentals.txt",
    "technicals.txt",
    "calculos.txt",
    "news.txt",
    "forums.txt"
]

MONTHLY_DATA_FILE = "monthly_fundamentals.txt"

PROCESSING_CONFIG = {
    "skip_weekends": False,  # CHANGED: Process weekends if data exists
    "skip_missing_data": True,
    "require_all_files": False,
    "parallel_agents": False,
    "retry_on_api_fail": True,
    "max_retries": 3,
    "retry_delay": 5
}

OUTPUT_CONFIG = {
    "save_individual_agents": True,
    "save_combined_output": True,
    "save_human_readable": True,
    "pretty_print_json": True,
    "log_processing_time": True
}

REGIME_LABELS = {
    "RISK_ON": "Risk-on environment (supportive for gold)",
    "RISK_OFF": "Risk-off environment (headwinds for gold)",
    "NEUTRAL": "Neutral/consolidation environment"
}

VALIDATION_CONFIG = {
    "require_regime_label": True,
    "require_confidence_score": False,  # CHANGED: Removed confidence requirement
    "min_confidence": 0.0,
    "max_confidence": 1.0,
    "require_key_drivers": True,
    "min_key_drivers": 1,
    "max_key_drivers": 10
}

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
        status = "SET" if key else "MISSING"
        print(f"{provider}: {status}")
    print("\ndone")