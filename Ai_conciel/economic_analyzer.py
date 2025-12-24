#!/usr/bin/env python3

import os
import sys
import time
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.progress import Progress

from google import genai
from dotenv import load_dotenv

load_dotenv('Ai_conciel/api.env')

console = Console()

DATA_FOLDER = Path("TEXT/daily_summaries")
OUTPUT_FOLDER = Path("Ai_conciel/reports")
GEMINI_MODEL = "gemini-2.5-flash"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None


def check_api_key():
    if not GEMINI_API_KEY:
        console.print(Panel(
            "[red]Missing GEMINI_API_KEY in api.env[/red]",
            title="Configuration Error",
            border_style="red"
        ))
        return False
    return True


def load_txt_file_raw(file_path: Path) -> str:
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read().strip()
        return content if content else None
    except Exception as e:
        console.print(f"  [red]✗ Error: {e}[/red]")
        return None


def load_economic_data(folder_path: Path) -> dict:
    if not folder_path.exists():
        console.print(f"[red]Folder not found: {folder_path}[/red]")
        return None
    
    txt_files = sorted(list(folder_path.glob("*.txt")))
    
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
            if "monthly_indicators" in txt_file.name.lower():
                monthly_indicators = content
                console.print(f"[blue]✓ (Monthly Context)[/blue]")
            else:
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
    daily_data = data_dict["daily_data"]
    monthly_indicators = data_dict["monthly_indicators"]
    
    data_text = []
    
    if monthly_indicators:
        data_text.append("=" * 80)
        data_text.append("MONTHLY INDICATORS (BASELINE CONTEXT)")
        data_text.append("=" * 80)
        data_text.append(monthly_indicators)
        data_text.append("\n" + "=" * 80)
        data_text.append("DAILY ECONOMIC DATA (30-DAY PERIOD)")
        data_text.append("=" * 80 + "\n")
    
    sorted_dates = sorted(daily_data.keys())
    
    for date in sorted_dates:
        data_text.append(f"\n--- DATE: {date} ---")
        data_text.append(daily_data[date])
        data_text.append("-" * 80)
    
    data_text.append(f"\n\nTOTAL DAYS ANALYZED: {len(sorted_dates)}")
    data_text.append(f"DATE RANGE: {sorted_dates[0]} to {sorted_dates[-1]}")
    
    return "\n".join(data_text)


def analyze_data_overview(data_dict: dict) -> str:
    daily_data = data_dict["daily_data"]
    monthly_indicators = data_dict["monthly_indicators"]
    
    sorted_dates = sorted(daily_data.keys())
    
    summary = []
    summary.append(f"Data Period: {len(sorted_dates)} days")
    summary.append(f"Date Range: {sorted_dates[0]} to {sorted_dates[-1]}")
    summary.append(f"Monthly Indicators: {'Present' if monthly_indicators else 'Not found'}")
    
    return "\n".join(summary)


def generate_macro_snapshot(formatted_data: str, data_summary: str) -> str:
    prompt = f"""You are a senior institutional macro strategist focused on gold (XAUUSD) regime analysis. Using only the last ~30 days of data provided, produce a concise, high-signal macro regime brief in Markdown, 400–600 words maximum, with no charts, appendix, or narrative filler.

The output must include:

1. **Regime Call**: One-line classification plus brief justification and net gold bias

2. **Three Dominant Forces** (ranked): For each force describe:
   - What changed numerically
   - The transmission via real rates, USD, inflation expectations, or risk stress
   - The quantified impact on gold

3. **Gold Transmission Summary**: How the macro forces flow through to XAUUSD

4. **What Matters Next**: Exactly three macro triggers with:
   - Metric
   - Level
   - Implication
   - Gold response range

5. **Mispriced Risk**: One or two only, with probability bands

6. **Final Bias**: Regime suitability for gold and clear invalidation conditions

RULES:
- Use ONLY supplied data
- Quantify every claim (no vague statements)
- Avoid buy/sell language
- State uncertainty where data is weak
- Focus strictly on: real rates, USD, inflation expectations, and risk stress
- 400-600 words MAX
- No filler, no narratives, pure signal

Data Overview:
{data_summary}

Economic Data:
{formatted_data}

OUTPUT: High-signal gold regime brief in Markdown format."""

    console.print(f"\n[yellow]Generating gold regime brief with {GEMINI_MODEL}...[/yellow]")
    
    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        return response.text or "[No response generated]"
    except Exception as e:
        return f"[Error: {str(e)}]"


def save_snapshot(snapshot_content: str, data_summary: str):
    """Save the gold macro regime brief in markdown format."""
    OUTPUT_FOLDER.mkdir(exist_ok=True)
    
    date_range_parts = data_summary.split('Date Range: ')[1].split('\n')[0].strip()
    dates = date_range_parts.split(' to ')
    start_date = dates[0].strip()
    end_date = dates[1].strip() if len(dates) > 1 else start_date
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = OUTPUT_FOLDER / f"gold_regime_brief_{timestamp}.md"
    
    with open(filename, "w", encoding='utf-8') as f:
        f.write(f"GOLD MACRO REGIME BRIEF\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}\n")
        f.write(f"Period: {start_date} to {end_date}\n\n")
        f.write(snapshot_content)
    
    return filename


def main():
    console.print(Panel(
        "[bold]Gold Macro Regime Analyzer[/bold]\n\n"
        f"Data: [cyan]{DATA_FOLDER}[/cyan]\n"
        f"Output: [cyan]{OUTPUT_FOLDER}[/cyan]\n"
        f"Model: [cyan]{GEMINI_MODEL}[/cyan]",
        title="Gold Regime Analysis",
        border_style="blue"
    ))
    
    if not check_api_key():
        sys.exit(1)
    
    console.print("\n[yellow]Loading economic data...[/yellow]")
    data_dict = load_economic_data(DATA_FOLDER)
    
    if data_dict is None:
        sys.exit(1)
    
    console.print("\n[yellow]Preparing data...[/yellow]")
    data_summary = analyze_data_overview(data_dict)
    formatted_data = prepare_data_for_analysis(data_dict)
    
    console.print(Panel(
        data_summary,
        title="Data Overview",
        border_style="cyan"
    ))
    
    with Progress() as progress:
        task = progress.add_task("[cyan]Generating regime brief...", total=1)
        snapshot_content = generate_macro_snapshot(formatted_data, data_summary)
        progress.update(task, advance=1)
    
    console.print()
    console.print(Panel(
        snapshot_content[:1500] + "\n\n...(truncated)",
        title="[bold green]Gold Regime Brief[/bold green]",
        border_style="green",
        padding=(1, 2)
    ))
    
    filename = save_snapshot(snapshot_content, data_summary)
    
    console.print()
    console.print(Panel(
        f"[bold green]Complete[/bold green]\n\n"
        f"Saved: [bold]{filename}[/bold]\n"
        f"Format: Markdown 400-600 words",
        title="Done",
        border_style="green"
    ))


if __name__ == "__main__":
    main()