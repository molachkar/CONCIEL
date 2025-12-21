#!/usr/bin/env python3
"""
Macroeconomic Research Pipeline
Analyzes daily economic data files and generates a professional research report using DeepSeek.
"""

import os
import glob
from pathlib import Path
from openai import OpenAI
from datetime import datetime


# ============================================================================
# CONFIGURATION - Edit these values
# ============================================================================
USE_OLLAMA = False  # Using Hugging Face API

# For Hugging Face - trying different free models
HF_API_KEY = "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"
HF_MODEL = "mistralai/Mistral-7B-Instruct-v0.2"  # More reliable free model

INPUT_FOLDER = "TEXT/daily_summaries"
OUTPUT_FOLDER = "TEXT/Reports"
# ============================================================================


def read_data_files(folder_path: str) -> str:
    """Read all text files from the given folder and combine them in sorted order."""
    data_context = ""
    files = glob.glob(os.path.join(folder_path, "*.txt"))
    
    if not files:
        print(f"❌ Error: No .txt files found in {folder_path}")
        return None
    
    # Sort files alphabetically to maintain consistent order
    files_sorted = sorted(files)
    
    print(f"📖 Reading {len(files_sorted)} files in order:")
    for idx, file_path in enumerate(files_sorted, 1):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                filename = Path(file_path).name
                print(f"   [{idx:2d}] {filename}")
                data_context += f"\n--- FILE {idx}: {filename} ---\n{content}\n"
        except Exception as e:
            print(f"⚠️  Warning: Could not read {file_path}: {e}")
    
    return data_context


def generate_report(data_context: str) -> str:
    """Generate economic research report using AI."""
    
    if USE_OLLAMA:
        # Local Ollama - completely free
        client = OpenAI(
            api_key="not-needed",
            base_url="http://localhost:11434/v1"
        )
        model = OLLAMA_MODEL
    else:
        # Hugging Face API - free tier
        client = OpenAI(
            api_key=HF_API_KEY,
            base_url="https://router.huggingface.co/v1"
        )
        model = HF_MODEL
    
    system_prompt = """You are a senior macro strategist operating at institutional hedge-fund standards, tasked with converting the last 30 days of economic and market data into a decision-grade research report for professional traders and portfolio managers. 

The output must be a dense, 3–4 page markdown report that prioritizes signal over narrative, explicitly separating observed facts, analytical interpretation, and forward assumptions. 

The report should synthesize the data into a clear macro and risk regime assessment, isolate the few dominant trends, inflections, and anomalies that materially matter, and map causal transmission paths from economic variables to assets, sectors, volatility, liquidity, and correlations. 

Forward-looking analysis must be evidence-based rather than predictive, framed over a 2–4 week horizon with scenario ranges, probability weighting, and clearly defined invalidation conditions. 

Focus EXCLUSIVELY on what is happening in markets and the economy - describe the current state, trends, inflections, and likely scenarios. Do NOT include trading recommendations, positioning advice, risk management strategies, or actionable implications.

The tone must be institutional, analytical, and objective, using concrete figures, rates of change, and comparative deltas, with no filler, storytelling, or unsupported speculation.

CRITICAL: You must cite specific data points, dates, and figures from the provided files. Reference exact numbers, percentages, and timestamps."""

    user_prompt = f"""Analyze the following 30-day economic and market dataset (files are numbered sequentially for temporal ordering) and produce a decision-grade institutional research report.

Extract and reference SPECIFIC data points including:
- Exact dates and values
- Percentage changes and rates
- Specific economic indicators with their readings
- Concrete market levels and movements

DATA CONTEXT (Chronologically Ordered):
{data_context}"""

    print("⏳ Sending data to AI for analysis... (this may take 1-2 minutes)")
    if USE_OLLAMA:
        print("   Using local Ollama - running on your computer...")
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=8192
        )
        
        report_content = response.choices[0].message.content
        return report_content
        
    except Exception as e:
        print(f"❌ Error calling AI API: {e}")
        if USE_OLLAMA:
            print("   Make sure Ollama is running: https://ollama.com/download")
        return None


def save_report(report_content: str, output_folder: str) -> str:
    """Save the generated report to a markdown file."""
    
    os.makedirs(output_folder, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_folder, f"economic_research_{timestamp}.md")
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        return output_path
    except Exception as e:
        print(f"❌ Error saving report: {e}")
        return None


def main():
    print("\n" + "="*60)
    print("  📊 ECONOMIC RESEARCH PIPELINE")
    print("="*60 + "\n")
    
    if USE_OLLAMA:
        if not os.system("ollama --version > nul 2>&1") == 0:
            print("❌ Error: Ollama not installed")
            print("   Download from: https://ollama.com/download")
            return
    else:
        if HF_API_KEY == "your_huggingface_token_here":
            print("❌ Error: Please set your HF_API_KEY")
            print("   Get free token at: https://huggingface.co/settings/tokens")
            return
    
    if not os.path.isdir(INPUT_FOLDER):
        print(f"❌ Error: Input folder not found: {INPUT_FOLDER}")
        return
    
    print(f"Configuration:")
    print(f"  Provider:      {'Ollama (Local/Free)' if USE_OLLAMA else 'Hugging Face (Free)'}")
    print(f"  Model:         {OLLAMA_MODEL if USE_OLLAMA else HF_MODEL}")
    print(f"  Input folder:  {INPUT_FOLDER}")
    print(f"  Output folder: {OUTPUT_FOLDER}")
    print(f"{'='*60}\n")
    
    # Read data files
    data_context = read_data_files(INPUT_FOLDER)
    
    if not data_context:
        return
    
    num_files = data_context.count("--- FILE")
    print(f"\n✅ Loaded {num_files} files in chronological order")
    print(f"   Total data size: {len(data_context):,} characters\n")
    
    # Generate report
    print("🤖 Generating institutional research report...")
    report_content = generate_report(data_context)
    
    if not report_content:
        return
    
    # Save report
    print("💾 Saving report...")
    output_file = save_report(report_content, OUTPUT_FOLDER)
    
    if not output_file:
        return
    
    print(f"✅ Report saved to: {output_file}")
    print(f"   Pages (estimated): {len(report_content) // 3000 + 1}")
    print(f"   Total words: {len(report_content.split()):,}")
    print(f"\n{'='*60}")
    print("✨ Analysis complete! Your report is ready.\n")
    

if __name__ == "__main__":
    main()