#!/usr/bin/env python3
"""
Economic Data Analyzer
Analyzes 30 days of economic data using three AI experts to create a collaborative market research report.
"""

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path
import pandas as pd
import numpy as np
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.progress import Progress

from groq import Groq
from google import genai
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv('api.env')

console = Console()

# Configuration paths
DATA_FOLDER = "TEXT/daily_summaries"
OUTPUT_FOLDER = "./reports"

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SAMBANOVA_API_KEY = os.environ.get("SAMBANOVA_API_KEY")

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
sambanova_client = OpenAI(
    api_key=SAMBANOVA_API_KEY,
    base_url="https://api.sambanova.ai/v1"
) if SAMBANOVA_API_KEY else None

ANALYSTS = {
    "groq": {
        "name": "Economic Data Analyst (Groq)",
        "color": "cyan",
        "role": "Data analysis and trend identification",
        "model": "llama-3.1-8b-instant"
    },
    "gemini": {
        "name": "Market Strategist (Gemini)",
        "color": "green",
        "role": "Strategic insights and implications",
        "model": "gemini-2.5-flash"
    },
    "sambanova": {
        "name": "Risk Assessment Expert (SambaNova)",
        "color": "magenta",
        "role": "Risk factors and practical considerations",
        "model": "Meta-Llama-3.1-8B-Instruct"
    }
}


def check_api_keys():
    """Check if all required API keys are set."""
    missing_keys = []
    if not GROQ_API_KEY:
        missing_keys.append("GROQ_API_KEY")
    if not GEMINI_API_KEY:
        missing_keys.append("GEMINI_API_KEY")
    if not SAMBANOVA_API_KEY:
        missing_keys.append("SAMBANOVA_API_KEY")
    
    if missing_keys:
        console.print(Panel(
            f"[red]Missing API keys in api.env: {', '.join(missing_keys)}[/red]",
            title="Configuration Error",
            border_style="red"
        ))
        return False
    return True


def load_txt_file_raw(file_path: Path) -> str:
    """Load TXT file as raw text without DataFrame conversion."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read().strip()
        return content if content else None
    except Exception as e:
        console.print(f"  [red]✗ Error: {e}[/red]")
        return None


def load_economic_data(folder_path: str) -> dict:
    """Load economic data files as raw text organized by date."""
    folder = Path(folder_path)
    
    if not folder.exists():
        console.print(f"[red]Folder not found: {folder_path}[/red]")
        return None
    
    txt_files = sorted(list(folder.glob("*.txt")))
    
    if not txt_files:
        console.print(f"[red]No TXT files found in: {folder_path}[/red]")
        return None
    
    console.print(f"[yellow]Found {len(txt_files)} TXT files[/yellow]\n")
    
    daily_data = {}
    monthly_indicators = None
    
    for txt_file in txt_files:
        time.sleep(0.05)
        
        console.print(f"  Loading: {txt_file.name}...", end=" ")
        
        content = load_txt_file_raw(txt_file)
        
        if content:
            # Check if it's the monthly indicators file
            if "monthly_indicators" in txt_file.name.lower():
                monthly_indicators = content
                console.print(f"[blue]✓ (Monthly Context)[/blue]")
            else:
                # Extract date from filename
                date_str = txt_file.stem.replace("summary_", "")
                daily_data[date_str] = content
                console.print(f"[green]✓[/green]")
        else:
            console.print(f"[yellow]⊘[/yellow]")
    
    if not daily_data:
        console.print("[red]No daily data files loaded[/red]")
        return None
    
    console.print(f"\n[green]Successfully loaded {len(daily_data)} daily files[/green]")
    if monthly_indicators:
        console.print(f"[blue]Monthly indicators loaded as context baseline[/blue]")
    
    return {
        "daily_data": daily_data,
        "monthly_indicators": monthly_indicators
    }


def prepare_data_for_analysis(data_dict: dict) -> str:
    """Format all data chronologically for AI analysis."""
    daily_data = data_dict["daily_data"]
    monthly_indicators = data_dict["monthly_indicators"]
    
    data_text = []
    
    # Add monthly context first
    if monthly_indicators:
        data_text.append("=" * 80)
        data_text.append("MONTHLY INDICATORS (BASELINE CONTEXT)")
        data_text.append("=" * 80)
        data_text.append(monthly_indicators)
        data_text.append("\n" + "=" * 80)
        data_text.append("DAILY ECONOMIC DATA (30-DAY PERIOD)")
        data_text.append("=" * 80 + "\n")
    
    # Add daily data chronologically
    sorted_dates = sorted(daily_data.keys())
    
    for date in sorted_dates:
        data_text.append(f"\n--- DATE: {date} ---")
        data_text.append(daily_data[date])
        data_text.append("-" * 80)
    
    data_text.append(f"\n\nTOTAL DAYS ANALYZED: {len(sorted_dates)}")
    data_text.append(f"DATE RANGE: {sorted_dates[0]} to {sorted_dates[-1]}")
    
    return "\n".join(data_text)


def analyze_data_overview(data_dict: dict) -> str:
    """Generate overview summary of loaded data."""
    daily_data = data_dict["daily_data"]
    monthly_indicators = data_dict["monthly_indicators"]
    
    sorted_dates = sorted(daily_data.keys())
    
    summary = []
    summary.append(f"Data Period: {len(sorted_dates)} days")
    summary.append(f"Date Range: {sorted_dates[0]} to {sorted_dates[-1]}")
    summary.append(f"Monthly Indicators: {'Present' if monthly_indicators else 'Not found'}")
    summary.append(f"\nDaily Files Loaded:")
    
    for date in sorted_dates[:10]:
        preview = daily_data[date][:100].replace("\n", " ")
        summary.append(f"  {date}: {preview}...")
    
    if len(sorted_dates) > 10:
        summary.append(f"  ... and {len(sorted_dates) - 10} more days")
    
    return "\n".join(summary)


def get_ai_analysis(analyst_key: str, data_summary: str, formatted_data: str) -> str:
    """Get analysis from an AI analyst with rate limiting."""
    analyst = ANALYSTS[analyst_key]
    
    base_prompt = """You are a senior macro strategist operating at institutional hedge-fund standards.

Your task: Analyze 30 days of daily economic data files to create a decision-grade research report for professional traders and portfolio managers.

CRITICAL INSTRUCTIONS:
1. The data contains DAILY summaries from a 30-day period
2. There is a MONTHLY INDICATORS file providing baseline context - this is your foundation
3. You MUST analyze day-by-day changes, trends, and inflections across the 30-day period
4. Extract specific dates, values, events, and data points from each day
5. Identify dominant trends, inflection points, and anomalies that materially matter
6. Map causal transmission paths from economic variables to market outcomes

Focus EXCLUSIVELY on what is happening in markets and the economy - describe the current state, trends, inflections, and likely scenarios. Do NOT include trading recommendations.

The tone must be institutional, analytical, and objective, using concrete figures, rates of change, and comparative deltas.

CITE SPECIFIC DATES AND DATA POINTS from the daily files."""
    
    prompt = f"""{base_prompt}

Role for this section: {analyst['role']}

Economic Data (30-Day Period + Monthly Context):
{formatted_data}

Data Overview:
{data_summary}

Provide a dense, institutional-grade analysis (2000-2500 words) that:
1. Uses the monthly indicators as baseline context
2. Analyzes the 30-day period day-by-day, citing specific dates and data points
3. Identifies dominant trends and inflection points across the period
4. Maps causal transmission paths from economic variables to market outcomes
5. Assesses macro and risk regime implications over the 2-4 week horizon
6. Defines clear invalidation conditions

Use only evidence from the provided data. Be specific with dates and numbers."""

    time.sleep(2)
    
    try:
        if analyst_key == "groq":
            if not groq_client:
                return "[Error: Groq client not initialized]"
            messages = [
                {"role": "system", "content": "You are a senior institutional macro strategist. Provide dense, data-driven analysis with specific date citations."},
                {"role": "user", "content": prompt}
            ]
            response = groq_client.chat.completions.create(
                model=analyst["model"],
                messages=messages,
                max_tokens=3000,
                temperature=0.5
            )
            return response.choices[0].message.content or "[No response]"
            
        elif analyst_key == "gemini":
            if not gemini_client:
                return "[Error: Gemini client not initialized]"
            response = gemini_client.models.generate_content(
                model=analyst["model"],
                contents=prompt
            )
            return response.text or "[No response]"
            
        else:
            if not sambanova_client:
                return "[Error: SambaNova client not initialized]"
            messages = [
                {"role": "system", "content": "You are a senior institutional macro strategist. Provide dense, data-driven analysis with specific date citations."},
                {"role": "user", "content": prompt}
            ]
            response = sambanova_client.chat.completions.create(
                model=analyst["model"],
                messages=messages,
                max_tokens=3000,
                temperature=0.5
            )
            return response.choices[0].message.content or "[No response]"
            
    except Exception as e:
        return f"[Error: {str(e)}]"


def generate_synthesis(analyses: dict, data_summary: str) -> str:
    """Generate a synthesis of all analyses into a cohesive market report."""
    analyses_text = "\n\n".join([
        f"[{ANALYSTS[key]['name']}]:\n{analysis}"
        for key, analysis in analyses.items()
    ])
    
    prompt = f"""You are a senior macro strategist synthesizing institutional-grade research based on 30 days of daily economic data.

Data Overview:
{data_summary}

Individual Expert Analyses:
{analyses_text}

Create a comprehensive INTEGRATED MACRO ASSESSMENT (3-4 paragraphs) that:
1. Synthesizes all expert perspectives into one cohesive macro view with specific date and data citations
2. Identifies consensus inflection points across the 30-day period and material disagreements
3. Maps the transmission paths from economic variables to market outcomes
4. Frames the 2-4 week outlook with scenario ranges and invalidation conditions
5. Assesses the current macro and risk regime

Use the monthly indicators as baseline context. Be dense, analytical, and institutional. Cite specific dates and concrete figures. Do NOT include trading recommendations."""

    time.sleep(2)
    
    try:
        if groq_client:
            messages = [
                {"role": "system", "content": "You are a senior institutional macro strategist. Synthesize research with specific date citations and institutional rigor."},
                {"role": "user", "content": prompt}
            ]
            response = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                max_tokens=2000,
                temperature=0.5
            )
            return response.choices[0].message.content or ""
        else:
            return "[Synthesis generation failed]"
    except Exception as e:
        return f"[Error: {str(e)}]"


def save_report(data_summary: str, analyses: dict, synthesis: str):
    """Save the complete market research report."""
    output_path = Path(OUTPUT_FOLDER)
    output_path.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = output_path / f"market_research_report_{timestamp}.txt"
    
    with open(filename, "w") as f:
        f.write("=" * 80 + "\n")
        f.write("ECONOMIC MARKET RESEARCH REPORT\n")
        f.write("30-DAY PERIOD ANALYSIS\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("-" * 80 + "\n")
        f.write("EXECUTIVE SUMMARY\n")
        f.write("-" * 80 + "\n")
        f.write(synthesis + "\n\n")
        
        f.write("-" * 80 + "\n")
        f.write("DATA OVERVIEW\n")
        f.write("-" * 80 + "\n")
        f.write(data_summary + "\n\n")
        
        f.write("-" * 80 + "\n")
        f.write("DETAILED EXPERT ANALYSES\n")
        f.write("-" * 80 + "\n\n")
        
        for key in ["groq", "gemini", "sambanova"]:
            analyst = ANALYSTS[key]
            f.write(f"[{analyst['name']}]\n")
            f.write(f"Role: {analyst['role']}\n")
            f.write("-" * 40 + "\n")
            f.write(analyses[key] + "\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("END OF REPORT\n")
        f.write("=" * 80 + "\n")
    
    return filename


def main():
    """Main function to run the economic data analyzer."""
    console.print(Panel(
        "[bold]Economic Market Research Generator[/bold]\n\n"
        "Analyzes 30 days of daily economic data files\n"
        "using three AI experts to create a comprehensive\n"
        "institutional-grade market research report.\n\n"
        f"Data Folder: [cyan]{DATA_FOLDER}[/cyan]\n"
        f"Output Folder: [cyan]{OUTPUT_FOLDER}[/cyan]\n\n"
        "Features:\n"
        "  • Day-by-day analysis of 30-day period\n"
        "  • Monthly indicators as baseline context\n"
        "  • Three independent expert perspectives\n"
        "  • Synthesized macro assessment\n"
        "  • Professional research report output",
        title="Market Research Tool",
        border_style="blue"
    ))
    
    if not check_api_keys():
        sys.exit(1)
    
    console.print("\n[yellow]Loading economic data files...[/yellow]")
    data_dict = load_economic_data(DATA_FOLDER)
    
    if data_dict is None:
        sys.exit(1)
    
    console.print("\n[yellow]Preparing data for analysis...[/yellow]")
    data_summary = analyze_data_overview(data_dict)
    formatted_data = prepare_data_for_analysis(data_dict)
    
    console.print(Panel(
        data_summary,
        title="Data Overview",
        border_style="cyan"
    ))
    
    analyses = {}
    
    console.print("\n[yellow]Generating institutional-grade expert analyses (this may take 2-3 minutes)...[/yellow]")
    
    with Progress() as progress:
        task = progress.add_task("[cyan]Analysts working...", total=3)
        
        for key in ["groq", "gemini", "sambanova"]:
            analyst = ANALYSTS[key]
            with console.status(f"[{analyst['color']}]{analyst['name']} analyzing...[/{analyst['color']}]"):
                analysis = get_ai_analysis(key, data_summary, formatted_data)
                analyses[key] = analysis
            progress.update(task, advance=1)
    
    console.print()
    for key in ["groq", "gemini", "sambanova"]:
        analyst = ANALYSTS[key]
        console.print(Panel(
            Markdown(analyses[key]),
            title=f"[bold {analyst['color']}]{analyst['name']}[/bold {analyst['color']}]",
            border_style=analyst["color"],
            padding=(1, 2)
        ))
    
    console.print("\n[yellow]Synthesizing market insights...[/yellow]")
    synthesis = generate_synthesis(analyses, data_summary)
    
    console.print(Panel(
        Markdown(synthesis),
        title="[bold gold1]Integrated Macro Assessment[/bold gold1]",
        border_style="gold1",
        padding=(1, 2)
    ))
    
    filename = save_report(data_summary, analyses, synthesis)
    
    console.print()
    console.print(Panel(
        f"[bold green]Institutional research report generated![/bold green]\n\n"
        f"Report saved to: [bold]{filename}[/bold]\n\n"
        f"The report contains:\n"
        f"  • Integrated Macro Assessment (synthesized insights)\n"
        f"  • 30-Day Period Overview\n"
        f"  • Three Expert Institutional Analyses\n"
        f"    - Day-by-day trend analysis\n"
        f"    - Strategic implications\n"
        f"    - Risk regime assessment\n"
        f"  • Evidence-based 2-4 week outlook\n"
        f"  • Monthly indicators as baseline context",
        title="Report Complete",
        border_style="green"
    ))


if __name__ == "__main__":
    main()