#!/usr/bin/env python3

import os, sys, re
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import IntPrompt, FloatPrompt
from rich.markdown import Markdown

try:
    from dotenv import load_dotenv
    load_dotenv('Ai_conciel/api.env')
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
CEREBRAS_API_KEY = os.environ.get("CEREBRAS_API_KEY")

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
sambanova_client = OpenAI(api_key=SAMBANOVA_API_KEY, base_url="https://api.sambanova.ai/v1") if SAMBANOVA_API_KEY else None
cerebras_client = OpenAI(api_key=CEREBRAS_API_KEY, base_url="https://api.cerebras.ai/v1") if CEREBRAS_API_KEY else None

# FIXED ORDER - Strategic leads first for context building
COUNCIL_ORDER = [
    "macro_quant",      # Qwen 235B - strongest first
    "swing_trader",     # Gemini 2.5 - structure
    "speed_technician", # Llama 70B - patterns
    "momentum_scalper", # Llama 8B - timing
    "risk_quant"        # Llama 8B - math
]

TRADERS = {
    "macro_quant": {
        "name": "Macro Quant",
        "color": "yellow",
        "lens": "Probabilistic regime analysis + macro-technical synthesis + base probability calculation",
        "model": "qwen-3-235b-a22b-instruct-2507",
        "provider": "cerebras",
        "weight": 0.30
    },
    "swing_trader": {
        "name": "Swing Trader",
        "color": "green",
        "lens": "Market structure + HTF context + key S/R levels + trend alignment",
        "model": "gemini-2.5-flash",
        "provider": "gemini",
        "weight": 0.25
    },
    "speed_technician": {
        "name": "Speed Technician",
        "color": "blue",
        "lens": "Technical patterns + key levels + volume analysis + order blocks",
        "model": "llama-3.3-70b",
        "provider": "cerebras",
        "weight": 0.20
    },
    "momentum_scalper": {
        "name": "Momentum Scalper",
        "color": "cyan",
        "lens": "Entry timing + price action + immediate execution optimization",
        "model": "llama-3.1-8b-instant",
        "provider": "groq",
        "weight": 0.125
    },
    "risk_quant": {
        "name": "Risk Quant",
        "color": "magenta",
        "lens": "Position sizing + Kelly Criterion + risk mathematics + probability validation",
        "model": "Meta-Llama-3.1-8B-Instruct",
        "provider": "sambanova",
        "weight": 0.125
    }
}

params, macro_data, tech_data, meeting_log = {}, {}, {}, []

def get_params():
    console.print(Panel("[bold yellow]Trading Parameters[/bold yellow]", border_style="yellow"))
    p = {}
    p['account_size'] = FloatPrompt.ask("[bold]Account Size (USD)[/bold]", default=100.0)
    p['risk_percent'] = FloatPrompt.ask("[bold]Risk (%)[/bold]", default=10.0)
    
    console.print("\n[bold]Timeframe:[/bold] 1.Scalp 2.Intraday 3.Swing")
    p['timeframe'] = {1:"Scalp",2:"Intraday",3:"Swing"}[IntPrompt.ask("Select", default=2)]
    
    console.print("\n[bold]Min R:R:[/bold] 1.1:2 2.1:3 3.1:5")
    p['min_rr'] = {1:2.0,2:3.0,3:5.0}[IntPrompt.ask("Select", default=2)]
    
    p['risk_dollars'] = (p['account_size'] * p['risk_percent']) / 100
    
    t = Table(title="Parameters")
    t.add_column("Param", style="cyan")
    t.add_column("Value", style="green")
    t.add_row("Account", f"${p['account_size']:.2f}")
    t.add_row("Risk/Trade", f"{p['risk_percent']}% (${p['risk_dollars']:.2f})")
    t.add_row("Timeframe", p['timeframe'])
    t.add_row("Min R:R", f"1:{p['min_rr']}")
    console.print(t)
    return p

def extract_macro_data(report_path):
    """Extract structured macro data from report"""
    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        data = {}
        
        # Extract KEY METRICS SNAPSHOT
        metrics_section = re.search(r'## KEY METRICS SNAPSHOT\s*\n(.*?)\n---', content, re.DOTALL | re.I)
        if metrics_section:
            metrics = metrics_section.group(1)
            
            regime = re.search(r'\*\*Regime\*\*:\s*"([^"]+)"', metrics, re.I)
            if regime: data['regime'] = regime.group(1)
            
            gold = re.search(r'\*\*XAU/USD\*\*:\s*\$?([\d,]+\.?\d*)', metrics, re.I)
            if gold: data['gold_macro'] = float(gold.group(1).replace(',', ''))
            
            dxy = re.search(r'\*\*DXY\*\*:\s*([\d.]+)', metrics, re.I)
            if dxy: data['dxy'] = float(dxy.group(1))
            
            vix = re.search(r'\*\*VIX\*\*:\s*([\d.]+)', metrics, re.I)
            if vix: data['vix'] = float(vix.group(1))
            
            fed = re.search(r'\*\*Fed Stance\*\*:\s*(\w+)', metrics, re.I)
            if fed: data['fed_stance'] = fed.group(1)
            
            treasury = re.search(r'\*\*10Y Treasury\*\*:\s*([\d.]+)', metrics, re.I)
            if treasury: data['treasury_10y'] = float(treasury.group(1))
            
            real_rate = re.search(r'\*\*Real Rate Estimate\*\*:\s*([+-]?[\d.]+)', metrics, re.I)
            if real_rate: data['real_rate'] = float(real_rate.group(1))
        
        # Store full report for reference
        data['full_report'] = content
        
        return data
    except Exception as e:
        console.print(f"[red]Error extracting macro: {e}[/red]")
        return None

def extract_tech_data(tech_path):
    """Extract pure technical data from technical file"""
    try:
        with open(tech_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        data = {}
        
        # Extract price data
        current = re.search(r'Current:\s*\$?([\d,]+\.?\d*)', content, re.I)
        if current: data['current_price'] = float(current.group(1).replace(',', ''))
        
        open_match = re.search(r'Open:\s*\$?([\d,]+\.?\d*)', content, re.I)
        if open_match: data['day_open'] = float(open_match.group(1).replace(',', ''))
        
        high_match = re.search(r'High:\s*\$?([\d,]+\.?\d*)', content, re.I)
        if high_match: data['day_high'] = float(high_match.group(1).replace(',', ''))
        
        low_match = re.search(r'Low:\s*\$?([\d,]+\.?\d*)', content, re.I)
        if low_match: data['day_low'] = float(low_match.group(1).replace(',', ''))
        
        # Extract EMAs
        ema9 = re.search(r'EMA9:\s*\$?([\d,]+\.?\d*)', content, re.I)
        if ema9: data['ema9'] = float(ema9.group(1).replace(',', ''))
        
        ema21 = re.search(r'EMA21:\s*\$?([\d,]+\.?\d*)', content, re.I)
        if ema21: data['ema21'] = float(ema21.group(1).replace(',', ''))
        
        ema50 = re.search(r'EMA50:\s*\$?([\d,]+\.?\d*)', content, re.I)
        if ema50: data['ema50'] = float(ema50.group(1).replace(',', ''))
        
        ema200 = re.search(r'EMA200:\s*\$?([\d,]+\.?\d*)', content, re.I)
        if ema200: data['ema200'] = float(ema200.group(1).replace(',', ''))
        
        # Extract full technical content for patterns/levels
        data['full_technical'] = content
        
        return data
    except Exception as e:
        console.print(f"[red]Error extracting technicals: {e}[/red]")
        return None

def load_reports():
    global macro_data, tech_data
    rp = Path("Ai_conciel/reports")
    
    if not rp.exists():
        console.print("[red]No reports folder[/red]")
        return False
    
    # Load macro report
    macro_files = list(rp.glob("*gold_regime*.md"))
    if not macro_files:
        console.print("[red]No macro reports found[/red]")
        return False
    
    console.print("\n[bold]Macro Reports:[/bold]")
    for i, f in enumerate(macro_files, 1):
        console.print(f"  {i}. {f.name}")
    choice = IntPrompt.ask("Select", default=1)
    if choice < 1 or choice > len(macro_files):
        return False
    
    macro_data = extract_macro_data(macro_files[choice-1])
    if not macro_data:
        return False
    
    # Load technical report
    tech_files = list(rp.glob("tech*.txt")) + list(rp.glob("tech*.md")) + list(rp.glob("technical*.txt")) + list(rp.glob("technical*.md"))
    if not tech_files:
        console.print("[red]No technical reports found[/red]")
        return False
    
    console.print("\n[bold]Technical Reports:[/bold]")
    for i, f in enumerate(tech_files, 1):
        console.print(f"  {i}. {f.name}")
    choice = IntPrompt.ask("Select", default=1)
    if choice < 1 or choice > len(tech_files):
        return False
    
    tech_data = extract_tech_data(tech_files[choice-1])
    if not tech_data:
        return False
    
    return True

def ai_call(key, prompt, max_tok=500):
    t = TRADERS[key]
    prov = t["provider"]
    try:
        if prov == "groq" and groq_client:
            r = groq_client.chat.completions.create(
                model=t["model"],
                messages=[{"role":"user","content":prompt}],
                max_tokens=max_tok, temperature=0.3
            )
            return r.choices[0].message.content or "[No response]"
        elif prov == "gemini" and gemini_client:
            r = gemini_client.models.generate_content(
                model=t["model"], contents=prompt
            )
            return r.text or "[No response]"
        elif prov == "sambanova" and sambanova_client:
            r = sambanova_client.chat.completions.create(
                model=t["model"],
                messages=[{"role":"user","content":prompt}],
                max_tokens=max_tok, temperature=0.3
            )
            return r.choices[0].message.content or "[No response]"
        elif prov == "cerebras" and cerebras_client:
            r = cerebras_client.chat.completions.create(
                model=t["model"],
                messages=[{"role":"user","content":prompt}],
                max_tokens=max_tok, temperature=0.3
            )
            return r.choices[0].message.content or "[No response]"
    except Exception as e:
        return f"[Error: {e}]"
    return "[Provider not available]"

def format_meeting_log(include_round=None):
    """Format meeting log for display in prompts"""
    output = []
    for entry in meeting_log:
        if include_round and entry.get('round') != include_round:
            continue
        output.append(f"[{entry['model']}]:\n{entry['response']}\n")
    return "\n".join(output)

# PHASE 1: OPEN ANALYSIS

def round_1_initial_assessment():
    """Round 1: All models provide initial market assessment"""
    console.print(Panel("[bold]PHASE 1 - ROUND 1: INITIAL ASSESSMENT[/bold]", border_style="yellow"))
    
    for key in COUNCIL_ORDER:
        t = TRADERS[key]
        
        prompt = f"""=== TRADING MEETING ROOM ===

ACCOUNT: ${params['account_size']:.2f} | RISK: {params['risk_percent']}% (${params['risk_dollars']:.2f}) | TIMEFRAME: {params['timeframe']} | MIN R:R: 1:{params['min_rr']}

MACRO REPORT (Economic Context):
Regime: {macro_data.get('regime', 'N/A')}
DXY: {macro_data.get('dxy', 'N/A')}
VIX: {macro_data.get('vix', 'N/A')}
Fed Stance: {macro_data.get('fed_stance', 'N/A')}
10Y Treasury: {macro_data.get('treasury_10y', 'N/A')}%
Real Rate: {macro_data.get('real_rate', 'N/A')}%

[Full Report Context]
{macro_data.get('full_report', 'N/A')[:1500]}...

TECHNICAL DATA (Pure):
XAUUSD Current: ${tech_data.get('current_price', 'N/A')}
Open: ${tech_data.get('day_open', 'N/A')}
High: ${tech_data.get('day_high', 'N/A')}
Low: ${tech_data.get('day_low', 'N/A')}
EMA9: ${tech_data.get('ema9', 'N/A')}
EMA21: ${tech_data.get('ema21', 'N/A')}
EMA50: ${tech_data.get('ema50', 'N/A')}
EMA200: ${tech_data.get('ema200', 'N/A')}

[Full Technical Data]
{tech_data.get('full_technical', 'N/A')[:1000]}...

YOUR ANALYTICAL LENS: {t['lens']}

TASK: Provide your initial market assessment from your lens perspective.

1. What do you see from your analytical lens?
2. What's your probability assessment?
   P(BUY) = ?
   P(SELL) = ?
   P(NONE) = ?
3. What's your confidence level? (LOW/MEDIUM/HIGH)
4. Key risks or opportunities you notice?

Speak freely. 3-5 sentences max. Focus on building understanding, not criticizing."""

        with console.status(f"[{t['color']}]{t['name']}...[/{t['color']}]"):
            response = ai_call(key, prompt, max_tok=400)
        
        console.print(f"[{t['color']}]{t['name']}:[/{t['color']}]")
        console.print(f"{response}\n")
        meeting_log.append({"round": 1, "model": t['name'], "key": key, "response": response})
    
    return True

def round_2_collaborative_response():
    """Round 2: All models respond to Round 1 discussion"""
    console.print(Panel("[bold]PHASE 1 - ROUND 2: COLLABORATIVE RESPONSE[/bold]", border_style="yellow"))
    
    round1_discussion = format_meeting_log(include_round=1)
    
    for key in COUNCIL_ORDER:
        t = TRADERS[key]
        
        prompt = f"""=== MEETING ROOM - ROUND 2 ===

ROUND 1 DISCUSSION:
{round1_discussion}

YOUR ANALYTICAL LENS: {t['lens']}

TASK: Respond to the discussion and refine your view.

1. Which analysis do you most AGREE with? Why?
2. Which analysis do you DISAGREE with? Why?
3. Do you want to adjust your probability? 
   New: P(BUY) = ?
   New: P(SELL) = ?
   New: P(NONE) = ?
4. What's missing from the discussion that needs attention?

Focus on COLLABORATION to build consensus. 3-4 sentences max."""

        with console.status(f"[{t['color']}]{t['name']}...[/{t['color']}]"):
            response = ai_call(key, prompt, max_tok=400)
        
        console.print(f"[{t['color']}]{t['name']}:[/{t['color']}]")
        console.print(f"{response}\n")
        meeting_log.append({"round": 2, "model": t['name'], "key": key, "response": response})
    
    # Calculate aggregate probabilities
    probs = {'BUY': [], 'SELL': [], 'NONE': []}
    for entry in meeting_log:
        resp = entry['response']
        buy = re.findall(r'P\(BUY\)\s*=?\s*(0?\.\d+|\d+%?)', resp, re.I)
        sell = re.findall(r'P\(SELL\)\s*=?\s*(0?\.\d+|\d+%?)', resp, re.I)
        none = re.findall(r'P\(NONE\)\s*=?\s*(0?\.\d+|\d+%?)', resp, re.I)
        
        if buy:
            val = buy[-1].replace('%', '')
            probs['BUY'].append(float(val) if '.' in val else float(val)/100)
        if sell:
            val = sell[-1].replace('%', '')
            probs['SELL'].append(float(val) if '.' in val else float(val)/100)
        if none:
            val = none[-1].replace('%', '')
            probs['NONE'].append(float(val) if '.' in val else float(val)/100)
    
    avg_probs = {
        'BUY': sum(probs['BUY'])/len(probs['BUY']) if probs['BUY'] else 0,
        'SELL': sum(probs['SELL'])/len(probs['SELL']) if probs['SELL'] else 0,
        'NONE': sum(probs['NONE'])/len(probs['NONE']) if probs['NONE'] else 0
    }
    
    console.print(Panel(
        f"[bold]PHASE 1 SUMMARY:[/bold]\n"
        f"P(BUY) = {avg_probs['BUY']:.2f}\n"
        f"P(SELL) = {avg_probs['SELL']:.2f}\n"
        f"P(NONE) = {avg_probs['NONE']:.2f}",
        border_style="cyan"
    ))
    
    max_prob = max(avg_probs.values())
    if max_prob < 0.60:
        console.print(Panel("[red]NO CLEAR DIRECTION - Probability < 0.60[/red]", border_style="red"))
        return False, None
    
    direction = max(avg_probs, key=avg_probs.get)
    if direction == 'NONE':
        console.print(Panel("[red]CONSENSUS: NO TRADE[/red]", border_style="red"))
        return False, None
    
    return True, {'direction': direction, 'probability': max_prob}

# PHASE 2: DIRECTION CONSENSUS

def round_3_direction_vote(phase1_result):
    """Round 3: Final direction vote with supermajority"""
    console.print(Panel("[bold]PHASE 2 - ROUND 3: FINAL DIRECTION VOTE[/bold]", border_style="yellow"))
    
    votes = {}
    
    for key in COUNCIL_ORDER:
        t = TRADERS[key]
        
        prompt = f"""=== MEETING ROOM - DIRECTION VOTE ===

PHASE 1 SUMMARY:
Direction Indication: {phase1_result['direction']}
Probability: {phase1_result['probability']:.2f}

FULL DISCUSSION SO FAR:
{format_meeting_log()}

YOUR LENS: {t['lens']}

FINAL VOTE: Given all discussion, what is your FINAL direction vote?

OUTPUT FORMAT (STRICT):
VOTE: BUY / SELL / NO_TRADE
PROBABILITY: 0.XX (your final confidence in this direction)
WHY: [1-2 sentences - final reasoning]"""

        with console.status(f"[{t['color']}]{t['name']}...[/{t['color']}]"):
            response = ai_call(key, prompt, max_tok=300)
        
        console.print(f"[{t['color']}]{t['name']}:[/{t['color']}]")
        console.print(f"{response}\n")
        
        # Parse vote
        vote_match = re.search(r'VOTE:\s*(BUY|SELL|NO_TRADE)', response, re.I)
        prob_match = re.search(r'PROBABILITY:\s*(0?\.\d+)', response, re.I)
        
        vote = vote_match.group(1).upper() if vote_match else "NO_TRADE"
        prob = float(prob_match.group(1)) if prob_match else 0.5
        
        votes[key] = {'vote': vote, 'probability': prob, 'response': response}
        meeting_log.append({"round": 3, "model": t['name'], "key": key, "response": response})
    
    # Count votes
    buy_votes = sum(1 for v in votes.values() if v['vote'] == 'BUY')
    sell_votes = sum(1 for v in votes.values() if v['vote'] == 'SELL')
    no_votes = sum(1 for v in votes.values() if v['vote'] == 'NO_TRADE')
    
    # Supermajority check (4/5)
    if buy_votes >= 4:
        direction = 'BUY'
        consensus_prob = sum(v['probability'] for v in votes.values() if v['vote'] == 'BUY') / buy_votes
    elif sell_votes >= 4:
        direction = 'SELL'
        consensus_prob = sum(v['probability'] for v in votes.values() if v['vote'] == 'SELL') / sell_votes
    else:
        direction = None
        consensus_prob = 0
    
    t = Table(title="VOTE RESULTS")
    t.add_column("Model", style="cyan")
    t.add_column("Vote", style="yellow")
    t.add_column("Probability", style="green")
    
    for key, vote_data in votes.items():
        t.add_row(TRADERS[key]['name'], vote_data['vote'], f"{vote_data['probability']:.2f}")
    
    console.print(t)
    console.print(f"\nBUY: {buy_votes} | SELL: {sell_votes} | NO_TRADE: {no_votes}\n")
    
    if not direction or consensus_prob < 0.60:
        console.print(Panel("[red]NO CONSENSUS - Need 4/5 votes & P ≥ 0.60[/red]", border_style="red"))
        return False, None
    
    console.print(Panel(
        f"[bold green]✅ CONSENSUS: {direction}[/bold green]\n"
        f"Probability: {consensus_prob:.2f}",
        border_style="green"
    ))
    
    return True, {'direction': direction, 'probability': consensus_prob, 'votes': votes}

# PHASE 3: LEVELS NEGOTIATION

def round_4_entry_proposals(consensus):
    """Round 4: Entry price proposals"""
    console.print(Panel("[bold]PHASE 3 - ROUND 4: ENTRY PROPOSALS[/bold]", border_style="yellow"))
    
    entries = {}
    
    for key in COUNCIL_ORDER:
        t = TRADERS[key]
        
        prompt = f"""=== MEETING ROOM - ENTRY DISCUSSION ===

CONSENSUS DIRECTION: {consensus['direction']}
CONSENSUS PROBABILITY: {consensus['probability']:.2f}

MACRO CONTEXT:
Regime: {macro_data.get('regime', 'N/A')}
DXY: {macro_data.get('dxy', 'N/A')} | VIX: {macro_data.get('vix', 'N/A')}
Fed: {macro_data.get('fed_stance', 'N/A')} | Real Rate: {macro_data.get('real_rate', 'N/A')}%

TECHNICAL LEVELS:
Current: ${tech_data.get('current_price', 'N/A')}
Range: ${tech_data.get('day_low', 'N/A')} - ${tech_data.get('day_high', 'N/A')}
EMA50: ${tech_data.get('ema50', 'N/A')} | EMA200: ${tech_data.get('ema200', 'N/A')}

YOUR LENS: {t['lens']}

TASK: Propose your entry price for this {consensus['direction']} setup.

1. ENTRY: $X.XX (specific price)
2. REASONING: Why this level? (cite technical OR macro support)
3. QUALITY: How good is this entry? (EXCELLENT/GOOD/ACCEPTABLE)

Reference others if you want, but focus on YOUR analysis. 2-3 sentences."""

        with console.status(f"[{t['color']}]{t['name']}...[/{t['color']}]"):
            response = ai_call(key, prompt, max_tok=350)
        
        console.print(f"[{t['color']}]{t['name']}:[/{t['color']}]")
        console.print(f"{response}\n")
        
        # Parse entry
        entry_match = re.search(r'ENTRY:\s*\$?([\d,]+\.?\d*)', response, re.I)
        entry = float(entry_match.group(1).replace(',', '')) if entry_match else None
        
        entries[key] = {'entry': entry, 'response': response}
        meeting_log.append({"round": 4, "model": t['name'], "key": key, "response": response})
    
    return entries

def round_5_sl_tp_collaboration(consensus, entries):
    """Round 5: Stop Loss & Take Profit proposals"""
    console.print(Panel("[bold]PHASE 3 - ROUND 5: SL & TP COLLABORATION[/bold]", border_style="yellow"))
    
    # Format entry proposals
    entry_summary = "\n".join([
        f"- {TRADERS[k]['name']}: ${v['entry']:.2f}" 
        for k, v in entries.items() if v['entry']
    ])
    
    levels = {}
    
    for key in COUNCIL_ORDER:
        t = TRADERS[key]
        
        prompt = f"""=== MEETING ROOM - LEVELS NEGOTIATION ===

DIRECTION: {consensus['direction']}
ENTRY PROPOSALS:
{entry_summary}

MACRO: {macro_data.get('regime', 'N/A')}
DXY: {macro_data.get('dxy', 'N/A')} | VIX: {macro_data.get('vix', 'N/A')}

TECHNICAL LEVELS:
Current: ${tech_data.get('current_price', 'N/A')}
Range: ${tech_data.get('day_low', 'N/A')} - ${tech_data.get('day_high', 'N/A')}
EMA50: ${tech_data.get('ema50', 'N/A')} | EMA200: ${tech_data.get('ema200', 'N/A')}

MIN R:R REQUIRED: 1:{params['min_rr']}

YOUR LENS: {t['lens']}

TASK: Build a complete levels package.

1. ENTRY: $X.XX (your final choice - can pick from proposals or adjust)
2. SL: $X.XX (where structure/regime breaks)
3. TP: $X.XX (realistic target given R:R requirement)
4. R:R: 1:X.X (calculated)
5. REASONING: Why these levels work together? (2 sentences)

COLLABORATE to find levels everyone can accept."""

        with console.status(f"[{t['color']}]{t['name']}...[/{t['color']}]"):
            response = ai_call(key, prompt, max_tok=400)
        
        console.print(f"[{t['color']}]{t['name']}:[/{t['color']}]")
        console.print(f"{response}\n")
        
        # Parse levels
        entry_match = re.search(r'ENTRY:\s*\$?([\d,]+\.?\d*)', response, re.I)
        sl_match = re.search(r'SL:\s*\$?([\d,]+\.?\d*)', response, re.I)
        tp_match = re.search(r'TP:\s*\$?([\d,]+\.?\d*)', response, re.I)
        rr_match = re.search(r'R:?R:\s*1?:?([\d.]+)', response, re.I)
        
        entry = float(entry_match.group(1).replace(',', '')) if entry_match else None
        sl = float(sl_match.group(1).replace(',', '')) if sl_match else None
        tp = float(tp_match.group(1).replace(',', '')) if tp_match else None
        rr = float(rr_match.group(1)) if rr_match else None
        
        levels[key] = {'entry': entry, 'sl': sl, 'tp': tp, 'rr': rr, 'response': response}
        meeting_log.append({"round": 5, "model": t['name'], "key": key, "response": response})
    
    return levels

def round_6_levels_consensus(consensus, levels):
    """Round 6: Final levels consensus negotiation"""
    console.print(Panel("[bold]PHASE 3 - ROUND 6: LEVELS CONSENSUS[/bold]", border_style="yellow"))
    
    # Calculate medians and spreads
    valid_entries = [v['entry'] for v in levels.values() if v['entry']]
    valid_sls = [v['sl'] for v in levels.values() if v['sl']]
    valid_tps = [v['tp'] for v in levels.values() if v['tp']]
    
    if not valid_entries or not valid_sls or not valid_tps:
        console.print("[red]Missing level proposals[/red]")
        return False, None
    
    median_entry = sorted(valid_entries)[len(valid_entries)//2]
    median_sl = sorted(valid_sls)[len(valid_sls)//2]
    median_tp = sorted(valid_tps)[len(valid_tps)//2]
    
    entry_spread = max(valid_entries) - min(valid_entries)
    risk_dist = abs(median_entry - median_sl)
    reward_dist = abs(median_tp - median_entry)
    median_rr = reward_dist / risk_dist if risk_dist > 0 else 0
    
    # Display proposals table
    t = Table(title="LEVEL PROPOSALS")
    t.add_column("Model", style="cyan")
    t.add_column("Entry", style="yellow")
    t.add_column("SL", style="red")
    t.add_column("TP", style="green")
    t.add_column("R:R", style="magenta")
    
    for key, lvl in levels.items():
        t.add_row(
            TRADERS[key]['name'],
            f"${lvl['entry']:.2f}" if lvl['entry'] else "N/A",
            f"${lvl['sl']:.2f}" if lvl['sl'] else "N/A",
            f"${lvl['tp']:.2f}" if lvl['tp'] else "N/A",
            f"1:{lvl['rr']:.1f}" if lvl['rr'] else "N/A"
        )
    
    console.print(t)
    console.print(f"\n[bold]MEDIANS:[/bold] Entry: ${median_entry:.2f} | SL: ${median_sl:.2f} | TP: ${median_tp:.2f} | R:R: 1:{median_rr:.1f}")
    console.print(f"[bold]SPREADS:[/bold] Entry: ${entry_spread:.2f} | Risk: ${risk_dist:.2f}")
    
    # Acceptance votes
    accepts = 0
    for key in COUNCIL_ORDER:
        t = TRADERS[key]
        
        prompt = f"""=== MEETING ROOM - FINAL LEVELS CONSENSUS ===

CURRENT PROPOSALS:
[See table above]

MEDIAN LEVELS (Most Democratic):
- Entry: ${median_entry:.2f}
- SL: ${median_sl:.2f}
- TP: ${median_tp:.2f}
- R:R: 1:{median_rr:.1f}

SPREADS:
- Entry spread: ${entry_spread:.2f}
- Risk distance: ${risk_dist:.2f}

MIN R:R REQUIRED: 1:{params['min_rr']}

YOUR LENS: {t['lens']}

TASK: Final negotiation on levels.

Can you ACCEPT the median levels?

OUTPUT FORMAT:
ACCEPT: YES / NO
WHY: [1 sentence - reasoning]
ADJUSTMENT: [If NO, what specific levels do you propose? Entry/SL/TP]"""

        with console.status(f"[{t['color']}]{t['name']} deciding...[/{t['color']}]"):
            response = ai_call(key, prompt, max_tok=300)
        
        console.print(f"[{t['style']}]{t['name']}:[/{t['style']}]\n{response}\n")
        
        accept_match = re.search(r'ACCEPT:\s*(YES|NO)', response, re.I)
        if accept_match and accept_match.group(1).upper() == 'YES':
            accepts += 1
        
        meeting_log.append({"round": 6, "model": t['name'], "key": key, "response": response})
    
    console.print(f"[bold]ACCEPTANCE:[/bold] {accepts}/5 models accept median levels")
    
    # If 4/5 accept, use median
    if accepts >= 4:
        final_levels = {
            'entry': median_entry,
            'sl': median_sl,
            'tp': median_tp,
            'rr': median_rr
        }
    else:
        # Use weighted average
        console.print("[yellow]Using weighted average (capability-based)[/yellow]")
        weighted_entry = sum(levels[k]['entry'] * TRADERS[k]['weight'] for k in levels if levels[k]['entry'])
        weighted_sl = sum(levels[k]['sl'] * TRADERS[k]['weight'] for k in levels if levels[k]['sl'])
        weighted_tp = sum(levels[k]['tp'] * TRADERS[k]['weight'] for k in levels if levels[k]['tp'])
        
        w_risk = abs(weighted_entry - weighted_sl)
        w_reward = abs(weighted_tp - weighted_entry)
        w_rr = w_reward / w_risk if w_risk > 0 else 0
        
        final_levels = {
            'entry': weighted_entry,
            'sl': weighted_sl,
            'tp': weighted_tp,
            'rr': w_rr
        }
    
    # Validation checks
    if entry_spread > 30:
        console.print(f"[red]❌ Entry spread too wide: ${entry_spread:.2f}[/red]")
        return False, None
    
    if risk_dist < 10:
        console.print(f"[red]❌ Risk distance too small: ${risk_dist:.2f}[/red]")
        return False, None
    
    if final_levels['rr'] < params['min_rr']:
        console.print(f"[red]❌ R:R below minimum: {final_levels['rr']:.1f} < {params['min_rr']}[/red]")
        return False, None
    
    console.print(Panel(
        f"[bold green]✅ LEVELS APPROVED[/bold green]\n"
        f"Entry: ${final_levels['entry']:.2f}\n"
        f"SL: ${final_levels['sl']:.2f}\n"
        f"TP: ${final_levels['tp']:.2f}\n"
        f"R:R: 1:{final_levels['rr']:.1f}",
        border_style="green"
    ))
    
    return True, final_levels

# PHASE 4: EXECUTION PLAN

def round_7_kelly_sizing_validation(consensus, final_levels):
    """Round 7: Kelly-adjusted position sizing and final validation"""
    console.print(Panel("[bold]PHASE 4 - ROUND 7: KELLY SIZING & FINAL VALIDATION[/bold]", border_style="yellow"))
    
    risk_dist = abs(final_levels['entry'] - final_levels['sl'])
    base_size = params['risk_dollars'] / risk_dist / 0.10
    
    sizes = []
    approvals = []
    kelly_fractions = []
    
    for key in COUNCIL_ORDER:
        t = TRADERS[key]
        
        prompt = f"""=== MEETING ROOM - FINAL EXECUTION ===

CONSENSUS TRADE PLAN:
- Direction: {consensus['direction']}
- Entry: ${final_levels['entry']:.2f}
- SL: ${final_levels['sl']:.2f}
- TP: ${final_levels['tp']:.2f}
- R:R: 1:{final_levels['rr']:.1f}
- Probability: {consensus['probability']:.2f}

ACCOUNT: ${params['account_size']:.2f} | RISK: {params['risk_percent']}% = ${params['risk_dollars']:.2f}
Risk Distance: ${risk_dist:.2f}

BASE SIZE CALCULATION:
Formula: Risk$ / RiskDist / $0.10
= ${params['risk_dollars']:.2f} / ${risk_dist:.2f} / $0.10
= {base_size:.2f} microlots

YOUR LENS: {t['lens']}

TASK: Position sizing + final validation

1. SIZE: Calculate position size in microlots (show math)

2. KELLY ADJUSTMENT: Given P={consensus['probability']:.2f}, should we size down?
   Kelly Formula: f* = (p * b - q) / b, where p=prob, b=R:R, q=1-p
   Calculate your Kelly fraction: 0.XX
   Adjusted size: X.XX microlots

3. FINAL VALIDATION: Is this trade APPROVED or VETOED?
   Check all conditions:
   - R:R ≥ {params['min_rr']} ? {'✅' if final_levels['rr'] >= params['min_rr'] else '❌'}
   - Probability ≥ 0.60 ? {'✅' if consensus['probability'] >= 0.60 else '❌'}
   - Risk distance ≥ $10 ? {'✅' if risk_dist >= 10 else '❌'}
   - VIX < 25 ? {'✅' if macro_data.get('vix', 100) < 25 else '❌'}
   
   VOTE: APPROVE / VETO
   WHY: [1 sentence - final reasoning]

OUTPUT FORMAT:
SIZE: X.XX microlots
KELLY_FRACTION: 0.XX
ADJUSTED_SIZE: X.XX microlots
VOTE: APPROVE / VETO
WHY: [reasoning]"""

        with console.status(f"[{t['color']}]{t['name']} calculating...[/{t['color']}]"):
            response = ai_call(key, prompt, max_tok=500)
        
        console.print(f"[{t['style']}]{t['name']}:[/{t['style']}]\n{response}\n")
        
        # Parse size and kelly
        size_match = re.search(r'ADJUSTED_SIZE:\s*([\d.]+)', response, re.I)
        kelly_match = re.search(r'KELLY_FRACTION:\s*([\d.]+)', response, re.I)
        vote_match = re.search(r'VOTE:\s*(APPROVE|VETO)', response, re.I)
        
        size = float(size_match.group(1)) if size_match else base_size
        kelly = float(kelly_match.group(1)) if kelly_match else 1.0
        vote = vote_match.group(1).upper() if vote_match else 'APPROVE'
        
        sizes.append(size)
        kelly_fractions.append(kelly)
        approvals.append(vote == 'APPROVE')
        
        meeting_log.append({"round": 7, "model": t['name'], "key": key, "response": response})
    
    # Final calculations
    median_size = sorted(sizes)[len(sizes)//2]
    avg_kelly = sum(kelly_fractions) / len(kelly_fractions)
    final_size = median_size * avg_kelly
    
    approve_count = sum(approvals)
    
    t = Table(title="EXECUTION SUMMARY")
    t.add_column("Model", style="cyan")
    t.add_column("Size", style="yellow")
    t.add_column("Kelly", style="magenta")
    t.add_column("Vote", style="green")
    
    for i, key in enumerate(COUNCIL_ORDER):
        t.add_row(
            TRADERS[key]['name'],
            f"{sizes[i]:.2f}",
            f"{kelly_fractions[i]:.2f}",
            "✅ APPROVE" if approvals[i] else "❌ VETO"
        )
    
    console.print(t)
    console.print(f"\n[bold]FINAL SIZE:[/bold] {final_size:.2f} microlots (Median: {median_size:.2f} × Avg Kelly: {avg_kelly:.2f})")
    console.print(f"[bold]APPROVAL:[/bold] {approve_count}/5 models approve")
    
    # Hard validation rules
    checks = [
        ("R:R ≥ Min", final_levels['rr'] >= params['min_rr'], f"1:{final_levels['rr']:.1f}"),
        ("Probability ≥ 0.60", consensus['probability'] >= 0.60, f"{consensus['probability']:.2f}"),
        ("Risk Dist ≥ $10", risk_dist >= 10, f"${risk_dist:.2f}"),
        ("VIX < 25", macro_data.get('vix', 100) < 25, f"{macro_data.get('vix', 'N/A')}"),
        ("Entry Spread < $30", True, "✓"),  # Already checked
        ("Supermajority (4/5)", approve_count >= 4, f"{approve_count}/5")
    ]
    
    validation_table = Table(title="VALIDATION CHECKS")
    validation_table.add_column("Check", style="cyan")
    validation_table.add_column("Status")
    validation_table.add_column("Value", style="yellow")
    
    all_pass = True
    for name, passed, val in checks:
        status = "[green]✅ PASS[/green]" if passed else "[red]❌ FAIL[/red]"
        validation_table.add_row(name, status, val)
        if not passed:
            all_pass = False
    
    console.print(validation_table)
    
    if not all_pass:
        console.print(Panel("[red]❌ TRADE REJECTED - Validation Failed[/red]", border_style="red"))
        return False, None
    
    console.print(Panel("[bold green]✅ TRADE APPROVED - All Checks Pass[/bold green]", border_style="green"))
    
    return True, {'size': final_size, 'kelly': avg_kelly, 'base_size': base_size}

def save_trade_plan(consensus, final_levels, execution):
    """Save the complete trade plan"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fn = f"trade_plan_{ts}.txt"
    
    with open(fn, "w", encoding='utf-8') as f:
        f.write("=== XAU/USD TRADE PLAN ===\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Account: ${params['account_size']:.0f} | Risk: {params['risk_percent']}%\n\n")
        
        f.write("SETUP:\n")
        f.write(f"Dir: {consensus['direction']}\n")
        f.write(f"Entry: ${final_levels['entry']:.2f}\n")
        f.write(f"SL: ${final_levels['sl']:.2f} (${abs(final_levels['entry']-final_levels['sl']):.2f})\n")
        f.write(f"TP: ${final_levels['tp']:.2f}\n")
        f.write(f"Size: {execution['size']:.2f} microlots\n")
        f.write(f"Risk: ${params['risk_dollars']:.2f}\n")
        f.write(f"R:R: 1:{final_levels['rr']:.1f}\n")
        f.write(f"Probability: {consensus['probability']:.2f}\n\n")
        
        f.write("MACRO:\n")
        f.write(f"REGIME: {macro_data.get('regime', 'N/A')}\n")
        f.write(f"Gold: ${macro_data.get('gold_macro', tech_data.get('current_price', 'N/A'))}\n")
        f.write(f"DXY: {macro_data.get('dxy', 'N/A')}\n")
        f.write(f"VIX: {macro_data.get('vix', 'N/A')}\n")
        f.write(f"Fed: {macro_data.get('fed_stance', 'N/A')}\n")
        f.write(f"10Y: {macro_data.get('treasury_10y', 'N/A')}%\n")
        f.write(f"Real Rate: {macro_data.get('real_rate', 'N/A')}%\n\n")
        
        f.write("TECH:\n")
        f.write(f"Current: ${tech_data.get('current_price', 'N/A')}\n")
        f.write(f"Day Range: ${tech_data.get('day_low', 'N/A')} - ${tech_data.get('day_high', 'N/A')}\n")
        f.write(f"EMA50: ${tech_data.get('ema50', 'N/A')}\n")
        f.write(f"EMA200: ${tech_data.get('ema200', 'N/A')}\n\n")
        
        f.write("EXECUTION:\n")
        f.write(f"1. {consensus['direction']} at ${final_levels['entry']:.2f}\n")
        f.write(f"2. SL ${final_levels['sl']:.2f}\n")
        f.write(f"3. TP ${final_levels['tp']:.2f}\n")
        f.write(f"4. Size {execution['size']:.2f} microlots (Kelly: {execution['kelly']:.2f})\n\n")
        
        f.write("INVALIDATION:\n")
        direction_word = 'below' if consensus['direction'] == 'BUY' else 'above'
        f.write(f"- Break {direction_word} ${final_levels['sl']:.2f}\n")
        f.write(f"- Major macro regime shift\n")
        f.write(f"- VIX >25\n\n")
        
        f.write("=== MEETING LOG ===\n")
        for entry in meeting_log:
            f.write(f"\n[Round {entry['round']}] {entry['model']}:\n{entry['response']}\n")
    
    console.print(f"[green]✅ Saved: {fn}[/green]")
    return fn

def main():
    global params
    
    console.print(Panel(
        "[bold]AI Trading Council v4[/bold]\n"
        "Collaborative Meeting Room | Lens-Based Analysis | Kelly Sizing\n"
        "5 Models | 7 Rounds | Supermajority Consensus",
        border_style="cyan"
    ))
    
    # Check API availability
    missing = []
    for k, v in [("GROQ", GROQ_API_KEY), ("GEMINI", GEMINI_API_KEY), 
                 ("SAMBANOVA", SAMBANOVA_API_KEY), ("CEREBRAS", CEREBRAS_API_KEY)]:
        if not v:
            missing.append(k)
    if missing:
        console.print(f"[yellow]⚠️ Missing APIs: {', '.join(missing)}[/yellow]")
        console.print("[red]All APIs required for v4 council[/red]")
        sys.exit(1)
    
    params = get_params()
    
    if not load_reports():
        sys.exit(1)
    
    console.print(Panel(
        f"[bold]Data Loaded:[/bold]\n"
        f"Regime: {macro_data.get('regime', 'N/A')[:50]}...\n"
        f"XAUUSD: ${tech_data.get('current_price', 'N/A')}\n"
        f"DXY: {macro_data.get('dxy', 'N/A')} | VIX: {macro_data.get('vix', 'N/A')}\n"
        f"Fed: {macro_data.get('fed_stance', 'N/A')} | Real Rate: {macro_data.get('real_rate', 'N/A')}%",
        border_style="green"
    ))
    
    console.print(f"\n[bold]Council Order (Fixed):[/bold] {' → '.join([TRADERS[k]['name'] for k in COUNCIL_ORDER])}\n")
    
    # PHASE 1: Open Analysis
    if not round_1_initial_assessment():
        sys.exit(0)
    
    success, phase1_result = round_2_collaborative_response()
    if not success:
        sys.exit(0)
    
    # PHASE 2: Direction Consensus
    success, consensus = round_3_direction_vote(phase1_result)
    if not success:
        sys.exit(0)
    
    # PHASE 3: Levels Negotiation
    entries = round_4_entry_proposals(consensus)
    levels = round_5_sl_tp_collaboration(consensus, entries)
    success, final_levels = round_6_levels_consensus(consensus, levels)
    if not success:
        sys.exit(0)
    
    # PHASE 4: Execution
    success, execution = round_7_kelly_sizing_validation(consensus, final_levels)
    if not success:
        sys.exit(0)
    
    # Save trade plan
    filename = save_trade_plan(consensus, final_levels, execution)
    
    console.print(Panel(
        f"[bold green]✅ TRADE PLAN COMPLETE[/bold green]\n\n"
        f"Direction: {consensus['direction']}\n"
        f"Entry: ${final_levels['entry']:.2f}\n"
        f"SL: ${final_levels['sl']:.2f}\n"
        f"TP: ${final_levels['tp']:.2f}\n"
        f"Size: {execution['size']:.2f} microlots\n"
        f"R:R: 1:{final_levels['rr']:.1f}\n"
        f"Probability: {consensus['probability']:.2f}\n\n"
        f"[bold]Saved:[/bold] {filename}",
        title="EXECUTION READY",
        border_style="green"
    ))

if __name__ == "__main__":
    main()