"""
Configuration file for CONCIEL DATA_BOT agents
Contains API keys, model configurations, and memory settings
"""

import os
from pathlib import Path

# ============================================================================
# PROJECT PATHS
# ============================================================================

# Base directories
# Data source (TEXT folder - READ ONLY)
TEXT_DIR = Path(r"C:\\Users\\PC\\Desktop\\CONCIEL\\TEXT")
DATA_DIR = TEXT_DIR / "data_by_date"
MONTHLY_REF_DIR = DATA_DIR / "_monthly_reference"

# Output directories (Processors folder - WRITE)
PROCESSORS_DIR = Path(r"C:\\Users\\PC\\Desktop\\CONCIEL\\Processors")
AGENT_OUTPUT_DIR = PROCESSORS_DIR / "agent_outputs"
MACRO_STRUCTURED_DIR = PROCESSORS_DIR / "macro_structured"

# Create output directories if they don't exist
AGENT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MACRO_STRUCTURED_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# API KEYS (Set these as environment variables or edit directly)
# ============================================================================

API_KEYS = {
    "google": os.getenv("GOOGLE_API_KEY", "AIzaSyBfFPvJcEknAw2BPn-4KCbkkhWb08P5eBc"),
    "cerebras": os.getenv("CEREBRAS_API_KEY", "csk-k22wvdn4n2dx8rey53wvyhn8j4yrvwvppwc55hyykmeeefwx"),
    "sambanova": os.getenv("SAMBANOVA_API_KEY", "7950ff15-0c72-46ca-9322-052b2e4ac162"),
    "groq": os.getenv("GROQ_API_KEY", "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"),
}

# ============================================================================
# MODEL CONFIGURATIONS
# ============================================================================

AGENT_CONFIGS = {
    "macro": {
        "name": "macro",
        "description": "Economic events, rates, inflation, Fed policy analysis",
        "model": "Qwen-235B",
        "provider": "cerebras",  # Adjust based on your access
        "api_endpoint": "https://api.cerebras.ai/v1/chat/completions",  # Update if needed
        "files": ["calendar.txt", "fundamentals.txt"],
        "uses_monthly_data": True,
        "temperature": 0.2,
        "max_tokens": 2000,
        "priority": "HIGH"
    },
    
    "market": {
    "name": "market",
    "description": "Technical indicators and advanced volatility analysis",
    "model": "deepseek-r1-distill-llama-70b",  # Changed
    "provider": "cerebras",  # Changed to Cerebras
    "api_endpoint": "https://api.cerebras.ai/v1/chat/completions",
    "files": ["technicals.txt", "calculos.txt"],
    "uses_monthly_data": False,
    "temperature": 0.3,
    "max_tokens": 2000,
    "priority": "VERY_HIGH"},
    
    "narrative": {
        "name": "narrative",
        "description": "News headlines and social sentiment analysis",
        "model": "Meta-Llama-3.3-70B",
        "provider": "sambanova",  # Adjust based on your access
        "api_endpoint": "https://api.sambanova.ai/v1/chat/completions",  # Update if needed
        "files": ["news.txt", "forums.txt"],
        "uses_monthly_data": False,
        "temperature": 0.4,
        "max_tokens": 2000,
        "priority": "HIGH"
    }
}

# ============================================================================
# MEMORY CONFIGURATION
# ============================================================================

MEMORY_CONFIG = {
    "recent_days": 7,       # Last 7 days - full detail
    "medium_days": 14,      # Days 8-21 - weekly summaries (2 weeks)
    "long_days": 9,         # Days 22-30 - regime labels only
    "total_window": 30      # Total memory span (30 days)
}

# ============================================================================
# DATA FILE MAPPINGS
# ============================================================================

# Standard daily files (in each date folder)
DAILY_FILES = [
    "calendar.txt",
    "fundamentals.txt",
    "technicals.txt",
    "calculos.txt",
    "news.txt",
    "forums.txt"
]

# Monthly reference file
MONTHLY_DATA_FILE = "monthly_fundamentals.txt"

# ============================================================================
# PROCESSING SETTINGS
# ============================================================================

PROCESSING_CONFIG = {
    "skip_weekends": True,          # Skip Saturday/Sunday
    "skip_missing_data": True,      # Skip dates with no data folder
    "require_all_files": False,     # Allow partial data (some files missing)
    "parallel_agents": False,       # Run agents sequentially (set True for parallel)
    "retry_on_api_fail": True,      # Retry if API call fails
    "max_retries": 3,               # Max retry attempts
    "retry_delay": 5                # Seconds between retries
}

# ============================================================================
# OUTPUT SETTINGS
# ============================================================================

OUTPUT_CONFIG = {
    "save_individual_agents": True,     # Save each agent's output separately
    "save_combined_output": True,       # Save combined macro_structured.json
    "save_human_readable": True,       # Generate .md files for humans
    "pretty_print_json": True,          # Indent JSON outputs
    "log_processing_time": True         # Track how long each agent takes
}

# ============================================================================
# REGIME LABELS (Standardized across all agents)
# ============================================================================

REGIME_LABELS = {
    "RISK_ON": "Risk-on environment (supportive for gold)",
    "RISK_OFF": "Risk-off environment (headwinds for gold)",
    "NEUTRAL": "Neutral/consolidation environment"
}

# ============================================================================
# VALIDATION SETTINGS
# ============================================================================

VALIDATION_CONFIG = {
    "require_regime_label": True,       # Analysis must include regime
    "require_confidence_score": True,   # Analysis must include confidence
    "min_confidence": 0.0,              # Minimum confidence (0.0-1.0)
    "max_confidence": 1.0,              # Maximum confidence
    "require_key_drivers": True,        # Must specify key drivers
    "min_key_drivers": 1,               # Minimum number of drivers
    "max_key_drivers": 10               # Maximum number of drivers
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_agent_config(agent_name):
    """
    Get configuration for a specific agent
    
    Args:
        agent_name (str): Name of agent ('macro', 'market', 'narrative')
    
    Returns:
        dict: Agent configuration
    """
    if agent_name not in AGENT_CONFIGS:
        raise ValueError(f"Unknown agent: {agent_name}. Valid agents: {list(AGENT_CONFIGS.keys())}")
    return AGENT_CONFIGS[agent_name]


def get_api_key(provider):
    """
    Get API key for a provider
    
    Args:
        provider (str): Provider name ('openai', 'google', etc.)
    
    Returns:
        str: API key
    """
    key = API_KEYS.get(provider, "")
    if not key:
        print(f"⚠️  Warning: No API key found for {provider}")
    return key


def get_data_path(date):
    """
    Get path to data folder for a specific date
    
    Args:
        date (str): Date in YYYY-MM-DD format
    
    Returns:
        Path: Path to data folder
    """
    return DATA_DIR / date


def get_agent_output_path(agent_name, date):
    """
    Get path where agent output should be saved
    
    Args:
        agent_name (str): Name of agent
        date (str): Date in YYYY-MM-DD format
    
    Returns:
        Path: Path to output file
    """
    agent_dir = AGENT_OUTPUT_DIR / agent_name
    agent_dir.mkdir(exist_ok=True)
    return agent_dir / f"{date}.json"


def get_monthly_data_path():
    """
    Get path to monthly reference data
    
    Returns:
        Path: Path to monthly data file
    """
    return MONTHLY_REF_DIR / MONTHLY_DATA_FILE


def validate_paths():
    """
    Validate that required directories exist
    
    Returns:
        bool: True if all paths valid
    """
    issues = []
    
    if not DATA_DIR.exists():
        issues.append(f"Data directory not found: {DATA_DIR}")
    
    if not MONTHLY_REF_DIR.exists():
        issues.append(f"Monthly reference directory not found: {MONTHLY_REF_DIR}")
    
    if issues:
        print("❌ Path validation failed:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    
    print("✅ All paths validated")
    return True


# ============================================================================
# INITIALIZATION CHECK
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("CONCIEL CONFIG VALIDATION")
    print("=" * 60)
    print()
    
    # Validate paths
    validate_paths()
    print()
    
    # Check API keys
    print("API Keys Status:")
    for provider, key in API_KEYS.items():
        status = "✅ SET" if key else "❌ MISSING"
        print(f"  {provider}: {status}")
    print()
    
    # Show agent configs
    print("Agent Configurations:")
    for agent_name, config in AGENT_CONFIGS.items():
        print(f"  {agent_name.upper()}:")
        print(f"    Model: {config['model']}")
        print(f"    Provider: {config['provider']}")
        print(f"    Files: {', '.join(config['files'])}")
        print(f"    Temperature: {config['temperature']}")
    print()
    
    # Show memory config
    print("Memory Configuration:")
    print(f"  Recent (full detail): {MEMORY_CONFIG['recent_days']} days")
    print(f"  Medium (summaries): {MEMORY_CONFIG['medium_days']} days")
    print(f"  Long (labels only): {MEMORY_CONFIG['long_days']} days")
    print(f"  Total window: {MEMORY_CONFIG['total_window']} days")
    print()
    
    print("=" * 60)
    print("Config loaded successfully!")
    print("=" * 60)