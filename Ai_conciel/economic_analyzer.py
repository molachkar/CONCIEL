#!/usr/bin/env python3

import os
import sys
import time
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from google import genai
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv('Ai_conciel/api.env')

DATA_FOLDER = Path("TEXT/daily_summaries")
OUTPUT_FOLDER = Path("Ai_conciel/reports")
GEMINI_MODEL = "gemini-2.5-flash"
QWEN_MODEL = "qwen-3-235b-a22b-instruct-2507"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
CEREBRAS_API_KEY = os.environ.get("CEREBRAS_API_KEY")

gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
cerebras_client = OpenAI(
    api_key=CEREBRAS_API_KEY,
    base_url="https://api.cerebras.ai/v1"
) if CEREBRAS_API_KEY else None


def check_api_keys():
    if not GEMINI_API_KEY or not CEREBRAS_API_KEY:
        print("Error: Missing API keys in api.env")
        return False
    return True


def load_txt_file_raw(file_path: Path) -> str:
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read().strip() or None
    except:
        return None


def load_economic_data(folder_path: Path) -> dict:
    if not folder_path.exists():
        print(f"Error: Folder not found: {folder_path}")
        return None
    
    txt_files = sorted(list(folder_path.glob("*.txt")))
    if not txt_files:
        print(f"Error: No TXT files in {folder_path}")
        return None
    
    print(f"Loading {len(txt_files)} files...")
    
    daily_data = {}
    monthly_indicators = None
    
    for txt_file in txt_files:
        content = load_txt_file_raw(txt_file)
        if content:
            if "monthly_indicators" in txt_file.name.lower():
                monthly_indicators = content
            else:
                daily_data[txt_file.stem.replace("summary_", "")] = content
    
    if not daily_data:
        print("Error: No daily data loaded")
        return None
    
    return {"daily_data": daily_data, "monthly_indicators": monthly_indicators}


def prepare_data_for_qwen(data_dict: dict) -> str:
    data_text = []
    daily_data = data_dict["daily_data"]
    monthly_indicators = data_dict["monthly_indicators"]
    
    if monthly_indicators:
        data_text.append("MONTHLY INDICATORS:\n" + monthly_indicators + "\n")
    
    for date in sorted(daily_data.keys()):
        data_text.append(f"\nDATE: {date}\n{daily_data[date]}")
    
    return "\n".join(data_text)


def call_cerebras_qwen(prompt: str) -> str:
    try:
        response = cerebras_client.chat.completions.create(
            model=QWEN_MODEL,
            messages=[
                {"role": "system", "content": "You are a senior macro analyst extracting intelligence from economic data."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"[ERROR: {str(e)}]"


def extract_inflation_monetary_intelligence(full_data: str) -> str:
    prompt = f"""Extract INFLATION and MONETARY POLICY intelligence for gold macro regime.

Focus on:
1. Inflation: Michigan 1Y/5Y expectations, CPI/PCE, PPI
2. Fed Policy: Rate decisions, Fed speakers, forward guidance
3. Real Rates: 10Y yields, real rate shifts

OUTPUT (300-400 words): Chronological bullets with numbers. End with net assessment.

DATA: {full_data}"""
    return call_cerebras_qwen(prompt)


def extract_market_news_reaction(full_data: str) -> str:
    prompt = f"""Extract MARKET REACTION and NEWS SENTIMENT for gold regime.

Focus on:
1. Gold: Daily moves >1%, key levels
2. USD: DXY trend, levels
3. Risk: VIX regime, S&P moves
4. News: Gold ETF flows, geopolitical events, Fed headlines
5. ETF: GLD/IAU volume anomalies

OUTPUT (350-450 words): Group by gold→USD→risk→news. Quantify with prices/dates. Net assessment.

DATA: {full_data}"""
    return call_cerebras_qwen(prompt)


def extract_calendar_reddit_signals(full_data: str) -> str:
    prompt = f"""Extract ECONOMIC CALENDAR and SOCIAL SENTIMENT.

Focus on:
1. Calendar: NFP, PMI, GDP, consumer sentiment (actual vs forecast)
2. Impact: Which releases moved markets
3. Reddit: Only meaningful sentiment shifts

OUTPUT (250-350 words): Chronological calendar releases, brief reddit section if relevant, forward outlook.

DATA: {full_data}"""
    return call_cerebras_qwen(prompt)


def stage1_qwen_extraction(full_data: str) -> dict:
    print("Stage 1: Qwen extraction (3 parallel tasks)...")
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(extract_inflation_monetary_intelligence, full_data): "inflation",
            executor.submit(extract_market_news_reaction, full_data): "market",
            executor.submit(extract_calendar_reddit_signals, full_data): "calendar"
        }
        
        extracts = {}
        for future in as_completed(futures):
            extract_type = futures[future]
            extracts[extract_type] = future.result()
    
    print("Stage 1 complete")
    return extracts


def stage2_gemini_synthesis(extracts: dict) -> str:
    print("Stage 2: Gemini synthesis...")
    
    combined = f"{extracts['inflation']}\n\n{extracts['market']}\n\n{extracts['calendar']}"
    
    prompt = f"""Synthesize gold (XAU/USD) macro regime brief from these pre-analyzed summaries.

MUST start with:
---
## KEY METRICS SNAPSHOT
- **Regime**: "[classification]"
- **XAU/USD**: $[price]
- **DXY**: [value]
- **VIX**: [value]
- **Fed Stance**: [Dovish/Hawkish/Neutral]
- **10Y Treasury**: [yield]%
- **Real Rate Estimate**: [calculation]%
---

Then:
### 1. Regime Call (100 words)
### 2. Five Dominant Forces (400 words) - ranked by gold impact, cite numbers
### 3. Gold Transmission Summary (150 words)
### 4. What Matters Next (200 words) - 4 triggers with levels
### 5. Mispriced Risk (150 words) - 1-2 risks with probability
### 6. Final Bias & Invalidation (100 words)

Total: 900-1200 words. Pure synthesis.

SUMMARIES:
{combined}"""

    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        print("Stage 2 complete")
        return response.text or "[No response]"
    except Exception as e:
        return f"[ERROR: {str(e)}]"


def save_report(final_report: str, extracts: dict, data_dict: dict):
    OUTPUT_FOLDER.mkdir(exist_ok=True)
    
    sorted_dates = sorted(data_dict["daily_data"].keys())
    start_date = sorted_dates[0]
    end_date = sorted_dates[-1]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    report_file = OUTPUT_FOLDER / f"gold_regime_brief_{timestamp}.md"
    with open(report_file, "w", encoding='utf-8') as f:
        f.write(f"# GOLD MACRO REGIME BRIEF v2.0\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}\n")
        f.write(f"Period: {start_date} to {end_date}\n")
        f.write(f"Pipeline: Qwen 2.5 → Gemini 2.5\n\n")
        f.write(final_report)
    
    extracts_file = OUTPUT_FOLDER / f"extracts_{timestamp}.md"
    with open(extracts_file, "w", encoding='utf-8') as f:
        f.write(f"# QWEN EXTRACTS\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}\n\n")
        f.write("## INFLATION & MONETARY\n\n" + extracts['inflation'])
        f.write("\n\n## MARKET & NEWS\n\n" + extracts['market'])
        f.write("\n\n## CALENDAR & REDDIT\n\n" + extracts['calendar'])
    
    return report_file, extracts_file


def main():
    print("\nGold Macro Regime Analyzer v2.0")
    print(f"Data: {DATA_FOLDER}")
    print(f"Output: {OUTPUT_FOLDER}\n")
    
    if not check_api_keys():
        sys.exit(1)
    
    data_dict = load_economic_data(DATA_FOLDER)
    if data_dict is None:
        sys.exit(1)
    
    print("Preparing data...")
    full_data = prepare_data_for_qwen(data_dict)
    
    start_time = time.time()
    extracts = stage1_qwen_extraction(full_data)
    final_report = stage2_gemini_synthesis(extracts)
    total_time = time.time() - start_time
    
    report_file, extracts_file = save_report(final_report, extracts, data_dict)
    
    print(f"\nComplete in {total_time:.1f}s")
    print(f"Report: {report_file}")
    print(f"Extracts: {extracts_file}")


if __name__ == "__main__":
    main()