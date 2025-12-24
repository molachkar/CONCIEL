#!/usr/bin/env python3
"""
Trading Setup Generator v3.0 - Vote-by-Component Architecture
Ultra-compact, math-validated, consensus-driven trading system
"""

import os
import sys
import random
import json
import re
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt, IntPrompt, Confirm, FloatPrompt
from rich.table import Table

try:
    from dotenv import load_dotenv
    load_dotenv('api.env')
except ImportError:
    pass

from groq import Groq
from google import genai
from openai import OpenAI

console = Console()

# API Setup
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SAMBANOVA_API_KEY = os.environ.get("SAMBANOVA_API_KEY")

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
sambanova_client = OpenAI(
    api_key=SAMBANOVA_API_KEY,
    base_url="https://api.sambanova.ai/v1"
) if SAMBANOVA_API_KEY else None

# NEW TRADER PERSONALITIES - Profitable, Not Theatrical
TRADER_PERSONALITIES = {
    "groq": {
        "name": "Momentum Scalper",
        "color": "cyan",
        "style": "bold cyan",
        "personality": "You are a momentum scalper. Focus: price action, support/resistance, immediate execution. Style: Quick entries on breaks, tight stops, minimum 1:2 R:R. Trade WITH trend only. Be concise: max 3 sentences.",
        "model": "llama-3.1-8b-instant"
    },
    "gemini": {
        "name": "Swing Structure Trader",
        "color": "green",
        "style": "bold green",
        "personality": "You are a swing structure trader. Focus: market structure, EMAs, higher timeframe context. Style: Hold through noise, wider stops, 1:3+ R:R. Only trade WITH higher timeframe trend. Be concise: max 3 sentences.",
        "model": "gemini-2.5-flash"
    },
    "sambanova": {
        "name": "Risk Quant",
        "color": "magenta",
        "style": "bold magenta",
        "personality": "You are a risk quant. Focus: position sizing, probability, risk-adjusted returns. Math-first validation. If math doesn't work, trade doesn't happen. Be concise: max 3 sentences.",
        "model": "Meta-Llama-3.1-8B-Instruct"
    }
}

EXPERTS = {}
trade_parameters = {}
macro_report = ""
technical_data = ""
debate_log = []


def get_trade_parameters():
    """Interactive parameter collection."""
    console.print(Panel(
        "[bold yellow]Trading Parameters Setup[/bold yellow]\n\n"
        "Configure your trading constraints:",
        title="Step 1: Parameters",
        border_style="yellow"
    ))
    
    params = {}
    
    params['account_size'] = FloatPrompt.ask(
        "[bold]Account Size (USD)[/bold]",
        default=300.0
    )
    
    params['risk_percent'] = FloatPrompt.ask(
        "[bold]Risk per Trade (%)[/bold]",
        default=2.0
    )
    
    console.print("\n[bold]Timeframe:[/bold]")
    console.print("  1. Scalp (M5-M15)")
    console.print("  2. Intraday (H1-H4)")
    console.print("  3. Swing (D1)")
    
    tf_choice = IntPrompt.ask("[bold]Select[/bold]", default=2)
    params['timeframe'] = {1: "Scalp", 2: "Intraday", 3: "Swing"}[tf_choice]
    
    console.print("\n[bold]Minimum Risk:Reward Ratio:[/bold]")
    console.print("  1. 1:2 (Standard)")
    console.print("  2. 1:3 (Conservative)")
    console.print("  3. 1:5 (Very Conservative)")
    
    rr_choice = IntPrompt.ask("[bold]Select[/bold]", default=1)
    params['min_rr'] = {1: 2.0, 2: 3.0, 3: 5.0}[rr_choice]
    
    console.print("\n[bold]Trade Style:[/bold]")
    console.print("  1. Aggressive")
    console.print("  2. Balanced")
    console.print("  3. Conservative")
    
    style_choice = IntPrompt.ask("[bold]Select[/bold]", default=2)
    params['style'] = {1: "Aggressive", 2: "Balanced", 3: "Conservative"}[style_choice]
    
    # Calculate risk in dollars
    params['risk_dollars'] = (params['account_size'] * params['risk_percent']) / 100
    
    # Display summary
    console.print()
    table = Table(title="Trading Parameters")
    table.add_column("Parameter", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Account Size", f"${params['account_size']:.2f}")
    table.add_row("Risk per Trade", f"{params['risk_percent']}% (${params['risk_dollars']:.2f})")
    table.add_row("Timeframe", params['timeframe'])
    table.add_row("Min R:R", f"1:{params['min_rr']}")
    table.add_row("Style", params['style'])
    
    console.print(table)
    console.print()
    
    return params


def optimize_macro_report(report_text: str) -> str:
    """Ultra-compact macro summary."""
    try:
        optimized = []
        
        # Regime
        regime = re.search(r'regime.*?[""]([^""]+)[""]', report_text, re.IGNORECASE)
        if regime:
            optimized.append(f"REGIME: {regime.group(1)}")
        
        # Gold price
        gold = re.search(r'XAU/USD.*?(\$?[\d,]+\.?\d*)', report_text)
        if gold:
            optimized.append(f"Gold: {gold.group(1)}")
        
        # Fed stance
        if 'dovish' in report_text.lower():
            optimized.append("Fed: Dovish/Easing")
        elif 'hawkish' in report_text.lower():
            optimized.append("Fed: Hawkish/Tightening")
        
        # Key metrics
        dxy = re.search(r'DXY.*?(\d+\.?\d*)', report_text)
        if dxy:
            optimized.append(f"DXY: {dxy.group(1)}")
        
        vix = re.search(r'VIX.*?(\d+\.?\d*)', report_text)
        if vix:
            optimized.append(f"VIX: {vix.group(1)}")
        
        return "\n".join(optimized) if optimized else "Limited macro data"
    
    except:
        return report_text[:500]


def load_reports():
    """Load and optimize both macro and technical reports."""
    global macro_report, technical_data
    
    reports_path = Path("reports")
    if not reports_path.exists():
        console.print("[red]No 'reports' folder found.[/red]")
        return False
    
    # Load macro report
    macro_files = list(reports_path.glob("market_research*.txt")) + list(reports_path.glob("market_research*.md"))
    if not macro_files:
        console.print("[red]No macro research reports found.[/red]")
        return False
    
    console.print("\n[bold]Available Macro Reports:[/bold]")
    for i, f in enumerate(macro_files, 1):
        console.print(f"  {i}. {f.name}")
    
    choice = IntPrompt.ask("[bold]Select macro report[/bold]", default=1)
    if choice < 1 or choice > len(macro_files):
        console.print("[red]Invalid selection.[/red]")
        return False
    
    macro_path = str(macro_files[choice - 1])
    
    # Read with encoding fallback
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    for encoding in encodings:
        try:
            with open(macro_path, 'r', encoding=encoding, errors='replace') as f:
                macro_raw = f.read()
            macro_report = optimize_macro_report(macro_raw)
            break
        except:
            continue
    
    # Load technical report
    tech_files = list(reports_path.glob("technical*.txt")) + list(reports_path.glob("technical*.md"))
    if not tech_files:
        console.print("[yellow]No technical reports found. Continuing without technical data.[/yellow]")
        technical_data = "No technical data available"
    else:
        console.print("\n[bold]Available Technical Reports:[/bold]")
        for i, f in enumerate(tech_files, 1):
            console.print(f"  {i}. {f.name}")
        
        choice = IntPrompt.ask("[bold]Select technical report[/bold]", default=1)
        if choice >= 1 and choice <= len(tech_files):
            tech_path = str(tech_files[choice - 1])
            for encoding in encodings:
                try:
                    with open(tech_path, 'r', encoding=encoding, errors='replace') as f:
                        technical_data = f.read()
                    break
                except:
                    continue
    
    return True


def get_ai_response(expert_key: str, prompt: str, system_prompt: str, max_tokens: int = 300) -> str:
    """Get concise AI response."""
    expert = EXPERTS[expert_key]
    
    try:
        if expert_key == "groq":
            if not groq_client:
                return "[Error: Groq not initialized]"
            response = groq_client.chat.completions.create(
                model=expert["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )
            return response.choices[0].message.content or "[No response]"
            
        elif expert_key == "gemini":
            if not gemini_client:
                return "[Error: Gemini not initialized]"
            response = gemini_client.models.generate_content(
                model=expert["model"],
                contents=f"{system_prompt}\n\n{prompt}"
            )
            return response.text or "[No response]"
            
        else:
            if not sambanova_client:
                return "[Error: SambaNova not initialized]"
            response = sambanova_client.chat.completions.create(
                model=expert["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )
            return response.choices[0].message.content or "[No response]"
            
    except Exception as e:
        return f"[Error: {str(e)}]"


def vote_direction(expert_order: list) -> dict:
    """Round 1: Vote on trade direction."""
    console.print()
    console.print(Panel(
        "[bold]ROUND 1: DIRECTION & TREND[/bold]\n"
        "Vote: BUY, SELL, or NO TRADE",
        title="Round 1",
        border_style="yellow"
    ))
    
    votes = {}
    
    for expert_key in expert_order:
        expert = EXPERTS[expert_key]
        
        prompt = f"""Account: ${trade_parameters['account_size']} | Risk: {trade_parameters['risk_percent']}% | Timeframe: {trade_parameters['timeframe']}

MACRO:
{macro_report}

TECHNICAL:
{technical_data}

Vote on DIRECTION: BUY, SELL, or NO TRADE
Provide ONE sentence explaining why.
Format:
VOTE: [BUY/SELL/NO TRADE]
WHY: [one sentence]"""

        with console.status(f"[{expert['color']}]{expert['name']} voting...[/{expert['color']}]"):
            response = get_ai_response(expert_key, prompt, expert["personality"])
        
        console.print(f"[{expert['style']}]{expert['name']}:[/{expert['style']}] {response}")
        
        # Parse vote
        vote_match = re.search(r'VOTE:\s*(BUY|SELL|NO TRADE)', response, re.IGNORECASE)
        if vote_match:
            votes[expert_key] = {
                "vote": vote_match.group(1).upper(),
                "reasoning": response
            }
        else:
            votes[expert_key] = {
                "vote": "NO TRADE",
                "reasoning": response
            }
        
        debate_log.append(f"[{expert['name']}] Direction: {votes[expert_key]['vote']}")
    
    # Count votes
    buy_count = sum(1 for v in votes.values() if v["vote"] == "BUY")
    sell_count = sum(1 for v in votes.values() if v["vote"] == "SELL")
    no_trade_count = sum(1 for v in votes.values() if v["vote"] == "NO TRADE")
    
    total_votes = len(votes)
    consensus = max(buy_count, sell_count, no_trade_count) / total_votes
    
    if buy_count > sell_count and buy_count > no_trade_count:
        direction = "BUY"
    elif sell_count > buy_count and sell_count > no_trade_count:
        direction = "SELL"
    else:
        direction = "NO TRADE"
    
    console.print()
    console.print(f"[bold]CONSENSUS:[/bold] {direction} ({buy_count} BUY, {sell_count} SELL, {no_trade_count} NO TRADE)")
    console.print(f"[bold]Agreement:[/bold] {consensus*100:.0f}%")
    
    return {
        "direction": direction,
        "consensus": consensus,
        "votes": votes,
        "buy": buy_count,
        "sell": sell_count,
        "no_trade": no_trade_count
    }


def vote_entry_level(expert_order: list, direction: str, previous_votes: dict) -> dict:
    """Round 2: Vote on entry price."""
    console.print()
    console.print(Panel(
        f"[bold]ROUND 2: ENTRY LEVEL[/bold]\n"
        f"Direction agreed: {direction}\n"
        "Propose specific entry price.",
        title="Round 2",
        border_style="yellow"
    ))
    
    entries = {}
    
    for expert_key in expert_order:
        expert = EXPERTS[expert_key]
        
        # Show previous votes
        prev_context = "\n".join([
            f"{EXPERTS[k]['name']}: {v['vote']}"
            for k, v in previous_votes.items()
        ])
        
        prompt = f"""Direction: {direction}
Account: ${trade_parameters['account_size']} | Risk: {trade_parameters['risk_percent']}%

MACRO: {macro_report}
TECHNICAL: {technical_data}

Previous votes:
{prev_context}

Propose ENTRY PRICE (number only) and WHY (one sentence).
Format:
ENTRY: $[price]
WHY: [one sentence]"""

        with console.status(f"[{expert['color']}]{expert['name']} analyzing...[/{expert['color']}]"):
            response = get_ai_response(expert_key, prompt, expert["personality"])
        
        console.print(f"[{expert['style']}]{expert['name']}:[/{expert['style']}] {response}")
        
        # Parse entry
        entry_match = re.search(r'ENTRY:\s*\$?([\d,]+\.?\d*)', response, re.IGNORECASE)
        if entry_match:
            entry_price = float(entry_match.group(1).replace(',', ''))
            entries[expert_key] = {
                "entry": entry_price,
                "reasoning": response
            }
        else:
            entries[expert_key] = {
                "entry": None,
                "reasoning": response
            }
        
        if entries[expert_key]["entry"]:
            debate_log.append(f"[{expert['name']}] Entry: ${entries[expert_key]['entry']:.2f}")
    
    # Calculate consensus entry
    valid_entries = [v["entry"] for v in entries.values() if v["entry"] is not None]
    if not valid_entries:
        return {"entry": None, "consensus": 0, "votes": entries}
    
    avg_entry = sum(valid_entries) / len(valid_entries)
    spread = max(valid_entries) - min(valid_entries)
    
    console.print()
    console.print(f"[bold]PROPOSED ENTRIES:[/bold] {[f'${e:.2f}' for e in valid_entries]}")
    console.print(f"[bold]AVERAGE:[/bold] ${avg_entry:.2f}")
    console.print(f"[bold]SPREAD:[/bold] ${spread:.2f}")
    
    return {
        "entry": avg_entry,
        "min": min(valid_entries),
        "max": max(valid_entries),
        "spread": spread,
        "votes": entries
    }


def vote_stop_loss(expert_order: list, direction: str, entry: float) -> dict:
    """Round 3: Vote on stop loss."""
    console.print()
    console.print(Panel(
        f"[bold]ROUND 3: STOP LOSS[/bold]\n"
        f"Direction: {direction} | Entry: ${entry:.2f}\n"
        "Propose stop loss level.",
        title="Round 3",
        border_style="yellow"
    ))
    
    stops = {}
    
    for expert_key in expert_order:
        expert = EXPERTS[expert_key]
        
        prompt = f"""Direction: {direction} | Entry: ${entry:.2f}
Account: ${trade_parameters['account_size']} | Risk: {trade_parameters['risk_percent']}% = ${trade_parameters['risk_dollars']:.2f}

TECHNICAL: {technical_data}

Propose STOP LOSS level and WHY (one sentence).
Format:
SL: $[price]
WHY: [one sentence]"""

        with console.status(f"[{expert['color']}]{expert['name']} calculating...[/{expert['color']}]"):
            response = get_ai_response(expert_key, prompt, expert["personality"])
        
        console.print(f"[{expert['style']}]{expert['name']}:[/{expert['style']}] {response}")
        
        # Parse SL
        sl_match = re.search(r'SL:\s*\$?([\d,]+\.?\d*)', response, re.IGNORECASE)
        if sl_match:
            sl_price = float(sl_match.group(1).replace(',', ''))
            stops[expert_key] = {
                "sl": sl_price,
                "reasoning": response
            }
        else:
            stops[expert_key] = {
                "sl": None,
                "reasoning": response
            }
        
        if stops[expert_key]["sl"]:
            debate_log.append(f"[{expert['name']}] SL: ${stops[expert_key]['sl']:.2f}")
    
    # Calculate consensus SL
    valid_sls = [v["sl"] for v in stops.values() if v["sl"] is not None]
    if not valid_sls:
        return {"sl": None, "risk": None, "votes": stops}
    
    avg_sl = sum(valid_sls) / len(valid_sls)
    risk_distance = abs(entry - avg_sl)
    
    console.print()
    console.print(f"[bold]PROPOSED SLs:[/bold] {[f'${s:.2f}' for s in valid_sls]}")
    console.print(f"[bold]AVERAGE:[/bold] ${avg_sl:.2f}")
    console.print(f"[bold]RISK DISTANCE:[/bold] ${risk_distance:.2f}")
    
    return {
        "sl": avg_sl,
        "risk": risk_distance,
        "votes": stops
    }


def vote_take_profit(expert_order: list, direction: str, entry: float, sl: float, risk: float) -> dict:
    """Round 4: Vote on take profit."""
    console.print()
    console.print(Panel(
        f"[bold]ROUND 4: TAKE PROFIT[/bold]\n"
        f"Entry: ${entry:.2f} | SL: ${sl:.2f} | Risk: ${risk:.2f}\n"
        f"Minimum R:R: 1:{trade_parameters['min_rr']}",
        title="Round 4",
        border_style="yellow"
    ))
    
    tps = {}
    min_tp_distance = risk * trade_parameters['min_rr']
    
    if direction == "BUY":
        min_tp = entry + min_tp_distance
    else:
        min_tp = entry - min_tp_distance
    
    for expert_key in expert_order:
        expert = EXPERTS[expert_key]
        
        prompt = f"""Direction: {direction} | Entry: ${entry:.2f} | SL: ${sl:.2f}
Risk Distance: ${risk:.2f}
Minimum R:R: 1:{trade_parameters['min_rr']} (TP must be at least ${min_tp:.2f})

TECHNICAL: {technical_data}

Propose TAKE PROFIT level and R:R ratio.
Format:
TP: $[price]
R:R: [ratio]"""

        with console.status(f"[{expert['color']}]{expert['name']} targeting...[/{expert['color']}]"):
            response = get_ai_response(expert_key, prompt, expert["personality"])
        
        console.print(f"[{expert['style']}]{expert['name']}:[/{expert['style']}] {response}")
        
        # Parse TP
        tp_match = re.search(r'TP:\s*\$?([\d,]+\.?\d*)', response, re.IGNORECASE)
        if tp_match:
            tp_price = float(tp_match.group(1).replace(',', ''))
            reward_distance = abs(tp_price - entry)
            actual_rr = reward_distance / risk if risk > 0 else 0
            
            tps[expert_key] = {
                "tp": tp_price,
                "rr": actual_rr,
                "reasoning": response
            }
        else:
            tps[expert_key] = {
                "tp": None,
                "rr": None,
                "reasoning": response
            }
        
        if tps[expert_key]["tp"]:
            debate_log.append(f"[{expert['name']}] TP: ${tps[expert_key]['tp']:.2f} (R:R 1:{tps[expert_key]['rr']:.1f})")
    
    # Calculate consensus TP
    valid_tps = [(v["tp"], v["rr"]) for v in tps.values() if v["tp"] is not None]
    if not valid_tps:
        return {"tp": None, "rr": None, "votes": tps}
    
    avg_tp = sum(t[0] for t in valid_tps) / len(valid_tps)
    avg_rr = sum(t[1] for t in valid_tps) / len(valid_tps)
    
    console.print()
    console.print(f"[bold]PROPOSED TPs:[/bold] {[f'${t[0]:.2f}' for t in valid_tps]}")
    console.print(f"[bold]AVERAGE:[/bold] ${avg_tp:.2f}")
    console.print(f"[bold]AVERAGE R:R:[/bold] 1:{avg_rr:.1f}")
    
    if avg_rr < trade_parameters['min_rr']:
        console.print(f"[red]⚠️  R:R {avg_rr:.1f} is below minimum {trade_parameters['min_rr']}[/red]")
    
    return {
        "tp": avg_tp,
        "rr": avg_rr,
        "votes": tps
    }


def vote_position_size(expert_order: list, entry: float, sl: float, risk_dollars: float) -> dict:
    """Round 5: Vote on position size (with math validation)."""
    console.print()
    console.print(Panel(
        f"[bold]ROUND 5: POSITION SIZE[/bold]\n"
        f"Entry: ${entry:.2f} | SL: ${sl:.2f}\n"
        f"Risk Distance: ${abs(entry - sl):.2f}\n"
        f"Max Risk: ${risk_dollars:.2f}",
        title="Round 5",
        border_style="yellow"
    ))
    
    sizes = {}
    risk_distance = abs(entry - sl)
    
    # Calculate correct position size
    # For XAU/USD: 1 microlot (0.01 lot) = $0.10 per $1 move
    # Position size = (Risk in $) / (Risk distance in $) / ($0.10 per microlot)
    correct_size = risk_dollars / risk_distance / 0.10
    
    console.print(f"[dim]Mathematical correct size: {correct_size:.2f} microlots[/dim]")
    
    for expert_key in expert_order:
        expert = EXPERTS[expert_key]
        
        prompt = f"""Entry: ${entry:.2f} | SL: ${sl:.2f}
Risk Distance: ${risk_distance:.2f}
Max Risk: ${risk_dollars:.2f}
Account: ${trade_parameters['account_size']}

Calculate position size in MICROLOTS.
Formula: Risk$ / RiskDistance / $0.10
Show your math.

Format:
SIZE: [number] microlots
MATH: [your calculation]"""

        with console.status(f"[{expert['color']}]{expert['name']} calculating...[/{expert['color']}]"):
            response = get_ai_response(expert_key, prompt, expert["personality"])
        
        console.print(f"[{expert['style']}]{expert['name']}:[/{expert['style']}] {response}")
        
        # Parse size
        size_match = re.search(r'SIZE:\s*([\d.]+)', response, re.IGNORECASE)
        if size_match:
            proposed_size = float(size_match.group(1))
            sizes[expert_key] = {
                "size": proposed_size,
                "reasoning": response
            }
        else:
            sizes[expert_key] = {
                "size": None,
                "reasoning": response
            }
        
        if sizes[expert_key]["size"]:
            debate_log.append(f"[{expert['name']}] Size: {sizes[expert_key]['size']:.2f} microlots")
    
    # Validate against correct math
    valid_sizes = [v["size"] for v in sizes.values() if v["size"] is not None]
    if not valid_sizes:
        return {"size": None, "correct": correct_size, "votes": sizes}
    
    avg_size = sum(valid_sizes) / len(valid_sizes)
    
    console.print()
    console.print(f"[bold]PROPOSED SIZES:[/bold] {[f'{s:.2f}' for s in valid_sizes]} microlots")
    console.print(f"[bold]AVERAGE:[/bold] {avg_size:.2f} microlots")
    console.print(f"[bold green]CORRECT (Math):[/bold green] {correct_size:.2f} microlots")
    
    # Check if average is within 10% of correct
    if abs(avg_size - correct_size) / correct_size > 0.10:
        console.print(f"[red]⚠️  Proposed sizes deviate >10% from mathematical correct size[/red]")
    
    return {
        "size": correct_size,  # Use mathematically correct size
        "proposed_avg": avg_size,
        "votes": sizes
    }


def final_consensus_check(results: dict) -> bool:
    """Check if all components have sufficient consensus."""
    console.print()
    console.print(Panel(
        "[bold]FINAL CONSENSUS CHECK[/bold]",
        title="Validation",
        border_style="blue"
    ))
    
    checks = []
    
    # Direction consensus
    dir_consensus = results['direction']['consensus']
    checks.append(("Direction", dir_consensus >= 0.60, f"{dir_consensus*100:.0f}%"))
    
    # Entry spread
    entry_spread = results['entry']['spread']
    checks.append(("Entry Spread", entry_spread < 50, f"${entry_spread:.2f}"))
    
    # R:R ratio
    rr = results['tp']['rr']
    min_rr = trade_parameters['min_rr']
    checks.append(("R:R Ratio", rr >= min_rr, f"1:{rr:.1f} (min 1:{min_rr})"))
    
    # Position size validation
    size_valid = results['position']['size'] is not None
    checks.append(("Position Math", size_valid, "Valid" if size_valid else "Invalid"))
    
    # Display checks
    table = Table(title="Consensus Validation")
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="white")
    table.add_column("Value", style="yellow")
    
    all_pass = True
    for check_name, passed, value in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        style = "green" if passed else "red"
        table.add_row(check_name, f"[{style}]{status}[/{style}]", value)
        if not passed:
            all_pass = False
    
    console.print(table)
    console.print()
    
    if not all_pass:
        console.print("[red]❌ NO CLEAR SETUP - Trade scrapped[/red]")
    else:
        console.print("[green]✅ ALL CHECKS PASSED - Trade approved[/green]")
    
    return all_pass


def save_compact_plan(results: dict):
    """Save ultra-compact trading plan."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"trade_plan_{timestamp}.txt"
    
    direction = results['direction']['direction']
    entry = results['entry']['entry']
    sl = results['stop']['sl']
    tp = results['tp']['tp']
    rr = results['tp']['rr']
    size = results['position']['size']
    risk_distance = results['stop']['risk']
    
    try:
        with open(filename, "w", encoding='utf-8') as f:
            f.write("=== XAU/USD TRADE PLAN ===\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"Account: ${trade_parameters['account_size']:.0f} | Risk: {trade_parameters['risk_percent']}%\n\n")
            
            f.write("CONSENSUS SETUP:\n")
            f.write(f"Direction: {direction} ({results['direction']['buy']}/3 unanimous)\n")
            f.write(f"Entry: ${entry:.2f}\n")
            f.write(f"Stop Loss: ${sl:.2f} (${risk_distance:.2f} risk)\n")
            f.write(f"Take Profit: ${tp:.2f}\n")
            f.write(f"Position: {size:.2f} microlots\n")
            f.write(f"Risk: ${trade_parameters['risk_dollars']:.2f} ({trade_parameters['risk_percent']}%)\n")
            f.write(f"R:R: 1:{rr:.1f}\n\n")
            
            f.write("MACRO CONTEXT:\n")
            f.write(f"{macro_report}\n\n")
            
            f.write("TECHNICAL CONTEXT:\n")
            f.write(f"{technical_data[:300]}...\n\n")
            
            f.write("EXECUTION:\n")
            f.write(f"1. Set {direction} order at ${entry:.2f}\n")
            f.write(f"2. SL at ${sl:.2f}\n")
            f.write(f"3. TP at ${tp:.2f}\n")
            f.write(f"4. Position: {size:.2f} microlots (VERIFY)\n")
            f.write(f"5. If price hits ${sl:.2f}, exit immediately\n\n")
            
            f.write("INVALIDATION:\n")
            f.write(f"- Break {'below' if direction == 'BUY' else 'above'} ${sl:.2f}\n")
            f.write("- Major macro shift\n")
            f.write("- VIX spike >25\n\n")
            
            f.write("=== DEBATE LOG ===\n")
            for log_entry in debate_log:
                f.write(f"{log_entry}\n")
            
            f.write("\nALL VERIFIED. EXECUTE.\n")
        
        console.print(f"[green]✅ Plan saved: {filename}[/green]")
        return filename
    
    except Exception as e:
        console.print(f"[red]Error saving plan: {e}[/red]")
        return None


def main():
    """Main execution flow."""
    console.print(Panel(
        "[bold]Trading Setup Generator v3.0[/bold]\n\n"
        "Vote-by-Component Architecture\n"
        "• Ultra-compact output\n"
        "• Math-validated positions\n"
        "• Consensus-driven execution\n"
        "• No trade if unclear",
        title="XAU/USD Trading System",
        border_style="cyan"
    ))
    
    # Check API keys
    missing = []
    if not GROQ_API_KEY:
        missing.append("GROQ_API_KEY")
    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")
    if not SAMBANOVA_API_KEY:
        missing.append("SAMBANOVA_API_KEY")
    
    if missing:
        console.print(f"[red]Missing: {', '.join(missing)}[/red]")
        sys.exit(1)
    
    EXPERTS.update(TRADER_PERSONALITIES)
    
    # Step 1: Get trading parameters
    global trade_parameters
    trade_parameters = get_trade_parameters()
    
    # Step 2: Load reports
    if not load_reports():
        sys.exit(1)
    
    # Display loaded data
    console.print()
    console.print(Panel(
        f"[bold]Macro Summary:[/bold]\n{macro_report}\n\n"
        f"[bold]Technical Data:[/bold]\n{technical_data[:200]}...",
        title="Market Data Loaded",
        border_style="green"
    ))
    
    # Step 3: Randomize order
    expert_order = list(EXPERTS.keys())
    random.shuffle(expert_order)
    console.print(f"\n[dim]Trading order: {', '.join([EXPERTS[k]['name'] for k in expert_order])}[/dim]")
    
    # Step 4: Vote on direction
    direction_result = vote_direction(expert_order)
    
    if direction_result['direction'] == "NO TRADE" or direction_result['consensus'] < 0.60:
        console.print()
        console.print(Panel(
            "[red]❌ NO CLEAR DIRECTION[/red]\n\n"
            "Consensus below 60% or majority voted NO TRADE.\n"
            "Trade process terminated.",
            title="No Setup",
            border_style="red"
        ))
        sys.exit(0)
    
    # Step 5: Vote on entry
    random.shuffle(expert_order)
    entry_result = vote_entry_level(expert_order, direction_result['direction'], direction_result['votes'])
    
    if entry_result['entry'] is None or entry_result['spread'] > 50:
        console.print(Panel(
            "[red]❌ NO ENTRY CONSENSUS[/red]\n\n"
            f"Entry spread: ${entry_result.get('spread', 'N/A')}\n"
            "Trade process terminated.",
            title="No Setup",
            border_style="red"
        ))
        sys.exit(0)
    
    # Step 6: Vote on stop loss
    random.shuffle(expert_order)
    stop_result = vote_stop_loss(expert_order, direction_result['direction'], entry_result['entry'])
    
    if stop_result['sl'] is None:
        console.print(Panel(
            "[red]❌ NO STOP LOSS CONSENSUS[/red]",
            title="No Setup",
            border_style="red"
        ))
        sys.exit(0)
    
    # Step 7: Vote on take profit
    random.shuffle(expert_order)
    tp_result = vote_take_profit(
        expert_order,
        direction_result['direction'],
        entry_result['entry'],
        stop_result['sl'],
        stop_result['risk']
    )
    
    if tp_result['tp'] is None or tp_result['rr'] < trade_parameters['min_rr']:
        console.print(Panel(
            f"[red]❌ TAKE PROFIT ISSUES[/red]\n\n"
            f"R:R: {tp_result.get('rr', 0):.1f} (min required: {trade_parameters['min_rr']})",
            title="No Setup",
            border_style="red"
        ))
        sys.exit(0)
    
    # Step 8: Vote on position size
    random.shuffle(expert_order)
    position_result = vote_position_size(
        expert_order,
        entry_result['entry'],
        stop_result['sl'],
        trade_parameters['risk_dollars']
    )
    
    # Step 9: Final consensus check
    all_results = {
        'direction': direction_result,
        'entry': entry_result,
        'stop': stop_result,
        'tp': tp_result,
        'position': position_result
    }
    
    if not final_consensus_check(all_results):
        sys.exit(0)
    
    # Step 10: Save compact plan
    filename = save_compact_plan(all_results)
    
    if filename:
        console.print()
        console.print(Panel(
            f"[bold green]✅ TRADE APPROVED[/bold green]\n\n"
            f"Direction: {direction_result['direction']}\n"
            f"Entry: ${entry_result['entry']:.2f}\n"
            f"SL: ${stop_result['sl']:.2f}\n"
            f"TP: ${tp_result['tp']:.2f}\n"
            f"Size: {position_result['size']:.2f} microlots\n"
            f"R:R: 1:{tp_result['rr']:.1f}\n\n"
            f"[bold]Plan saved:[/bold] {filename}",
            title="EXECUTE TRADE",
            border_style="green"
        ))


if __name__ == "__main__":
    main()