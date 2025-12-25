#!/usr/bin/env python3

import os, sys, re
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import IntPrompt, FloatPrompt

try:
    from dotenv import load_dotenv
    load_dotenv('Ai_conciel/api.env')
except ImportError:
    pass

from groq import Groq
from google import genai
from openai import OpenAI

console = Console()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SAMBANOVA_API_KEY = os.environ.get("SAMBANOVA_API_KEY")
CEREBRAS_API_KEY = os.environ.get("CEREBRAS_API_KEY")

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
sambanova_client = OpenAI(api_key=SAMBANOVA_API_KEY, base_url="https://api.sambanova.ai/v1") if SAMBANOVA_API_KEY else None
cerebras_client = OpenAI(api_key=CEREBRAS_API_KEY, base_url="https://api.cerebras.ai/v1") if CEREBRAS_API_KEY else None

COUNCIL_ORDER = [
    "macro_quant",
    "swing_trader",
    "speed_technician",
    "gpt_oss_strategist",
    "risk_quant"
]

TRADERS = {
    "macro_quant": {
        "name": "Macro Quant",
        "lens": "Regime suitability + probability calculation + macro-technical alignment",
        "model": "qwen-3-235b-a22b-instruct-2507",
        "provider": "cerebras",
        "weight": 0.30
    },
    "swing_trader": {
        "name": "Swing Trader",
        "lens": "Market structure + trend alignment + key support/resistance levels",
        "model": "gemini-2.5-flash",
        "provider": "gemini",
        "weight": 0.25
    },
    "speed_technician": {
        "name": "Speed Technician",
        "lens": "Technical patterns + key levels + volume analysis + order blocks",
        "model": "llama-3.3-70b",
        "provider": "cerebras",
        "weight": 0.20
    },
    "gpt_oss_strategist": {
        "name": "GPT-OSS Strategist",
        "lens": "Entry timing + multi-timeframe confluence + execution optimization",
        "model": "llama3-groq-70b-8192-tool-use-preview",
        "provider": "groq",
        "weight": 0.15
    },
    "risk_quant": {
        "name": "Risk Quant",
        "lens": "Position sizing + Kelly Criterion + risk mathematics + probability validation",
        "model": "Meta-Llama-3.1-8B-Instruct",
        "provider": "sambanova",
        "weight": 0.10
    }
}

params, macro_data, tech_data, meeting_log = {}, {}, {}, []

def get_params():
    console.print("Trading Parameters:")
    p = {}
    p['account_size'] = FloatPrompt.ask("Account Size (USD)", default=100.0)
    p['risk_percent'] = FloatPrompt.ask("Risk (%)", default=10.0)
    
    console.print("\nTimeframe: 1.Scalp 2.Intraday 3.Swing")
    p['timeframe'] = {1:"Scalp",2:"Intraday",3:"Swing"}[IntPrompt.ask("Select", default=2)]
    
    console.print("\nMin R:R: 1.1:2 2.1:3 3.1:5")
    p['min_rr'] = {1:2.0,2:3.0,3:5.0}[IntPrompt.ask("Select", default=2)]
    
    p['risk_dollars'] = (p['account_size'] * p['risk_percent']) / 100
    
    console.print(f"\nAccount: ${p['account_size']:.2f}")
    console.print(f"Risk/Trade: {p['risk_percent']}% (${p['risk_dollars']:.2f})")
    console.print(f"Timeframe: {p['timeframe']}")
    console.print(f"Min R:R: 1:{p['min_rr']}")
    return p

def extract_macro_data(report_path):
    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        data = {}
        
        metrics_section = re.search(r'## KEY METRICS SNAPSHOT\s*\n(.*?)\n---', content, re.DOTALL | re.I)
        if metrics_section:
            metrics = metrics_section.group(1)
            
            regime = re.search(r'[-*]\s*\*\*Regime\*\*:\s*(.+?)(?:\n|$)', metrics, re.I)
            if regime: data['regime'] = regime.group(1).strip()
            
            gold = re.search(r'[-*]\s*\*\*XAU/USD\*\*:\s*\$?([\d,]+\.?\d*)', metrics, re.I)
            if gold: data['gold_macro'] = float(gold.group(1).replace(',', ''))
            
            dxy = re.search(r'[-*]\s*\*\*DXY\*\*:\s*([\d.]+)', metrics, re.I)
            if dxy: data['dxy'] = float(dxy.group(1))
            
            vix = re.search(r'[-*]\s*\*\*VIX\*\*:\s*([\d.]+)', metrics, re.I)
            if vix: data['vix'] = float(vix.group(1))
            
            fed = re.search(r'[-*]\s*\*\*Fed Stance\*\*:\s*(\w+)', metrics, re.I)
            if fed: data['fed_stance'] = fed.group(1)
            
            treasury = re.search(r'[-*]\s*\*\*10Y Treasury\*\*:\s*([\d.]+)', metrics, re.I)
            if treasury: data['treasury_10y'] = float(treasury.group(1))
            
            real_rate = re.search(r'[-*]\s*\*\*Real Rate Estimate\*\*:\s*([+-]?[\d.]+)', metrics, re.I)
            if real_rate: data['real_rate'] = float(real_rate.group(1))
        
        forces_section = re.search(r'### 2\. (?:Five |Three )?Dominant Forces\s*\n(.*?)(?:\n### [3-9]\.|$)', content, re.DOTALL | re.I)
        if forces_section:
            data['dominant_forces'] = forces_section.group(1).strip()[:1500]
        
        triggers_section = re.search(r'### 4\. What Matters Next\s*\n(.*?)(?:\n### [5-9]\.|$)', content, re.DOTALL | re.I)
        if triggers_section:
            data['forward_triggers'] = triggers_section.group(1).strip()[:800]
        
        risk_section = re.search(r'### 5\. Mispriced Risk\s*\n(.*?)(?:\n### [6-9]\.|$)', content, re.DOTALL | re.I)
        if risk_section:
            data['mispriced_risks'] = risk_section.group(1).strip()[:600]
        
        invalidation_section = re.search(r'### 6\. Final Bias.*?\n(.*?)(?:\n##|$)', content, re.DOTALL | re.I)
        if invalidation_section:
            data['invalidation'] = invalidation_section.group(1).strip()[:500]
        
        return data
    except Exception as e:
        console.print(f"Error extracting macro: {e}")
        return None

def extract_tech_data(tech_path):
    try:
        with open(tech_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        data = {}
        
        current = re.search(r'Current:\s*\$?([\d,]+\.?\d*)', content, re.I)
        if current: data['current_price'] = float(current.group(1).replace(',', ''))
        
        open_match = re.search(r'Open:\s*\$?([\d,]+\.?\d*)', content, re.I)
        if open_match: data['day_open'] = float(open_match.group(1).replace(',', ''))
        
        high_match = re.search(r'High:\s*\$?([\d,]+\.?\d*)', content, re.I)
        if high_match: data['day_high'] = float(high_match.group(1).replace(',', ''))
        
        low_match = re.search(r'Low:\s*\$?([\d,]+\.?\d*)', content, re.I)
        if low_match: data['day_low'] = float(low_match.group(1).replace(',', ''))
        
        ema9 = re.search(r'EMA9:\s*\$?([\d,]+\.?\d*)', content, re.I)
        if ema9: data['ema9'] = float(ema9.group(1).replace(',', ''))
        
        ema21 = re.search(r'EMA21:\s*\$?([\d,]+\.?\d*)', content, re.I)
        if ema21: data['ema21'] = float(ema21.group(1).replace(',', ''))
        
        ema50 = re.search(r'EMA50:\s*\$?([\d,]+\.?\d*)', content, re.I)
        if ema50: data['ema50'] = float(ema50.group(1).replace(',', ''))
        
        ema200 = re.search(r'EMA200:\s*\$?([\d,]+\.?\d*)', content, re.I)
        if ema200: data['ema200'] = float(ema200.group(1).replace(',', ''))
        
        rsi = re.search(r'RSI[:\s]*([\d.]+)', content, re.I)
        if rsi: data['rsi'] = float(rsi.group(1))
        
        support_section = re.search(r'(?:Support|S/R|Key Levels)[:\s]*\n(.*?)(?:\n\n|$)', content, re.DOTALL | re.I)
        if support_section:
            data['sr_levels'] = support_section.group(1).strip()[:500]
        
        volume_section = re.search(r'Volume[:\s]*\n(.*?)(?:\n\n|$)', content, re.DOTALL | re.I)
        if volume_section:
            data['volume_analysis'] = volume_section.group(1).strip()[:300]
        
        data['full_technical'] = content[:2000]
        
        return data
    except Exception as e:
        console.print(f"Error extracting technicals: {e}")
        return None

def load_reports():
    global macro_data, tech_data
    rp = Path("Ai_conciel/reports")
    
    if not rp.exists():
        console.print("No reports folder")
        return False
    
    macro_files = list(rp.glob("*gold_regime*.md"))
    if not macro_files:
        console.print("No macro reports found")
        return False
    
    console.print("\nMacro Reports:")
    for i, f in enumerate(macro_files, 1):
        console.print(f"  {i}. {f.name}")
    choice = IntPrompt.ask("Select", default=1)
    if choice < 1 or choice > len(macro_files):
        return False
    
    macro_data = extract_macro_data(macro_files[choice-1])
    if not macro_data:
        return False
    
    tech_files = list(rp.glob("tech*.txt")) + list(rp.glob("tech*.md")) + list(rp.glob("technical*.txt")) + list(rp.glob("technical*.md"))
    if not tech_files:
        console.print("No technical reports found")
        return False
    
    console.print("\nTechnical Reports:")
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

def round_0_pre_filter():
    console.print("\nPRE-FILTER: Regime Suitability Check")
    
    checks = [
        ("VIX < 25", macro_data.get('vix', 100) < 25),
        ("Regime Defined", 'regime' in macro_data),
        ("RSI Not Extreme", tech_data.get('rsi', 50) < 85 and tech_data.get('rsi', 50) > 15),
        ("Price Range Normal", abs(tech_data.get('day_high', 0) - tech_data.get('day_low', 0)) < 100)
    ]
    
    for name, passed in checks:
        status = "PASS" if passed else "FAIL"
        console.print(f"{name}: {status}")
        if not passed:
            console.print(f"REJECTED: {name}")
            return False
    
    prompt = f"""Quick regime check for {params['timeframe']} trading:

REGIME: {macro_data.get('regime', 'N/A')}
DOMINANT FORCES: {macro_data.get('dominant_forces', 'N/A')[:300]}
MISPRICED RISKS: {macro_data.get('mispriced_risks', 'N/A')[:200]}
INVALIDATION: {macro_data.get('invalidation', 'N/A')[:200]}
CURRENT PRICE: ${tech_data.get('current_price', 'N/A')}
RSI: {tech_data.get('rsi', 'N/A')}
VIX: {macro_data.get('vix', 'N/A')}

Is this regime tradeable for {params['timeframe']} RIGHT NOW?

OUTPUT:
TRADEABLE: YES / NO
REASON: [1 sentence]"""
    
    response = ai_call("macro_quant", prompt, max_tok=150)
    console.print(f"Macro Quant: {response}")
    
    meeting_log.append({"round": 0, "model": "Macro Quant", "key": "macro_quant", "response": response})
    
    tradeable_match = re.search(r'TRADEABLE:\s*(YES|NO)', response, re.I)
    if tradeable_match and tradeable_match.group(1).upper() == 'NO':
        console.print("REGIME FILTER: Not tradeable")
        return False
    
    console.print("PASSED PRE-FILTER\n")
    return True

def round_1_direction_and_levels():
    console.print("ROUND 1: Direction + Levels Proposals")
    
    proposals = {}
    
    for key in COUNCIL_ORDER:
        t = TRADERS[key]
        
        prompt = f"""Complete trade proposal from your lens.

MACRO INTELLIGENCE:
Regime: {macro_data.get('regime', 'N/A')}
DXY: {macro_data.get('dxy', 'N/A')} | VIX: {macro_data.get('vix', 'N/A')}
Fed: {macro_data.get('fed_stance', 'N/A')} | Real Rate: {macro_data.get('real_rate', 'N/A')}%

DOMINANT FORCES:
{macro_data.get('dominant_forces', 'N/A')[:800]}

FORWARD TRIGGERS:
{macro_data.get('forward_triggers', 'N/A')[:400]}

MISPRICED RISKS:
{macro_data.get('mispriced_risks', 'N/A')[:300]}

TECHNICAL CONTEXT:
Current: ${tech_data.get('current_price', 'N/A')}
Range: ${tech_data.get('day_low', 'N/A')} - ${tech_data.get('day_high', 'N/A')}
EMA9: ${tech_data.get('ema9', 'N/A')} | EMA21: ${tech_data.get('ema21', 'N/A')}
EMA50: ${tech_data.get('ema50', 'N/A')} | EMA200: ${tech_data.get('ema200', 'N/A')}
RSI: {tech_data.get('rsi', 'N/A')}

S/R LEVELS:
{tech_data.get('sr_levels', 'N/A')[:300]}

VOLUME:
{tech_data.get('volume_analysis', 'N/A')[:200]}

YOUR LENS: {t['lens']}
TIMEFRAME: {params['timeframe']}
MIN R:R: 1:{params['min_rr']}

OUTPUT (exact format):
DIRECTION: BUY / SELL / NO_TRADE
PROBABILITY: 0.XX
ENTRY: $X.XX
SL: $X.XX
TP: $X.XX
R:R: 1:X.X
WHY: [2 sentences citing macro OR technical support]"""
        
        response = ai_call(key, prompt, max_tok=500)
        console.print(f"\n{t['name']}:\n{response}")
        
        direction_match = re.search(r'DIRECTION:\s*(BUY|SELL|NO_TRADE)', response, re.I)
        prob_match = re.search(r'PROBABILITY:\s*(0?\.\d+)', response, re.I)
        entry_match = re.search(r'ENTRY:\s*\$?([\d,]+\.?\d*)', response, re.I)
        sl_match = re.search(r'SL:\s*\$?([\d,]+\.?\d*)', response, re.I)
        tp_match = re.search(r'TP:\s*\$?([\d,]+\.?\d*)', response, re.I)
        rr_match = re.search(r'R:?R:\s*1?:?([\d.]+)', response, re.I)
        
        proposals[key] = {
            'direction': direction_match.group(1).upper() if direction_match else 'NO_TRADE',
            'probability': float(prob_match.group(1)) if prob_match else 0.5,
            'entry': float(entry_match.group(1).replace(',', '')) if entry_match else None,
            'sl': float(sl_match.group(1).replace(',', '')) if sl_match else None,
            'tp': float(tp_match.group(1).replace(',', '')) if tp_match else None,
            'rr': float(rr_match.group(1)) if rr_match else None,
            'response': response
        }
        
        meeting_log.append({"round": 1, "model": t['name'], "key": key, "response": response})
    
    buy_votes = sum(1 for p in proposals.values() if p['direction'] == 'BUY')
    sell_votes = sum(1 for p in proposals.values() if p['direction'] == 'SELL')
    no_votes = sum(1 for p in proposals.values() if p['direction'] == 'NO_TRADE')
    
    console.print(f"\nVOTE RESULTS: BUY={buy_votes} SELL={sell_votes} NO_TRADE={no_votes}")
    
    if buy_votes >= 4:
        direction = 'BUY'
        consensus_prob = sum(p['probability'] for p in proposals.values() if p['direction'] == 'BUY') / buy_votes
    elif sell_votes >= 4:
        direction = 'SELL'
        consensus_prob = sum(p['probability'] for p in proposals.values() if p['direction'] == 'SELL') / sell_votes
    else:
        console.print("No consensus (need 4/5 votes)")
        return False, None
    
    console.print(f"CONSENSUS: {direction} (P={consensus_prob:.2f})")
    
    if consensus_prob < 0.60:
        console.print("Probability < 0.60")
        return False, None
    
    return True, {'direction': direction, 'probability': consensus_prob, 'proposals': proposals}

def round_2_levels_refinement(consensus):
    console.print("\nROUND 2: Levels Refinement")
    
    proposals = consensus['proposals']
    direction = consensus['direction']
    
    valid_entries = [p['entry'] for p in proposals.values() if p['direction'] == direction and p['entry']]
    valid_sls = [p['sl'] for p in proposals.values() if p['direction'] == direction and p['sl']]
    valid_tps = [p['tp'] for p in proposals.values() if p['direction'] == direction and p['tp']]
    
    if not valid_entries or not valid_sls or not valid_tps:
        console.print("Missing levels")
        return False, None
    
    median_entry = sorted(valid_entries)[len(valid_entries)//2]
    median_sl = sorted(valid_sls)[len(valid_sls)//2]
    median_tp = sorted(valid_tps)[len(valid_tps)//2]
    
    entry_spread = max(valid_entries) - min(valid_entries)
    risk_dist = abs(median_entry - median_sl)
    reward_dist = abs(median_tp - median_entry)
    median_rr = reward_dist / risk_dist if risk_dist > 0 else 0
    
    console.print(f"\nMedian Levels:")
    console.print(f"Entry: ${median_entry:.2f}")
    console.print(f"SL: ${median_sl:.2f}")
    console.print(f"TP: ${median_tp:.2f}")
    console.print(f"R:R: 1:{median_rr:.1f}")
    console.print(f"Entry Spread: ${entry_spread:.2f}")
    console.print(f"Risk Distance: ${risk_dist:.2f}")
    
    if entry_spread > 30:
        console.print(f"Entry spread too wide: ${entry_spread:.2f}")
        return False, None
    
    if risk_dist < 10:
        console.print(f"Risk distance too small: ${risk_dist:.2f}")
        return False, None
    
    if median_rr < params['min_rr']:
        console.print(f"R:R below minimum: {median_rr:.1f} < {params['min_rr']}")
        return False, None
    
    accepts = 0
    for key in COUNCIL_ORDER:
        t = TRADERS[key]
        
        prompt = f"""Review median levels for {direction} trade:

Entry: ${median_entry:.2f}
SL: ${median_sl:.2f}
TP: ${median_tp:.2f}
R:R: 1:{median_rr:.1f}

Entry Spread: ${entry_spread:.2f}
Risk Distance: ${risk_dist:.2f}
Min R:R Required: 1:{params['min_rr']}

MACRO CONTEXT:
Regime: {macro_data.get('regime', 'N/A')[:50]}
DXY: {macro_data.get('dxy', 'N/A')} | VIX: {macro_data.get('vix', 'N/A')}

TECHNICAL CONTEXT:
Current: ${tech_data.get('current_price', 'N/A')}
RSI: {tech_data.get('rsi', 'N/A')}

ACCEPT: YES / NO
WHY: [1 sentence]
ADJUSTMENT: [if NO, suggest specific Entry/SL/TP]"""
        
        response = ai_call(key, prompt, max_tok=300)
        console.print(f"{t['name']}: {response}")
        
        accept_match = re.search(r'ACCEPT:\s*(YES|NO)', response, re.I)
        if accept_match and accept_match.group(1).upper() == 'YES':
            accepts += 1
        
        meeting_log.append({"round": 2, "model": t['name'], "key": key, "response": response})
    
    console.print(f"\nAcceptance: {accepts}/5")
    
    if accepts >= 4:
        final_levels = {'entry': median_entry, 'sl': median_sl, 'tp': median_tp, 'rr': median_rr}
    else:
        console.print("Using weighted average")
        total_weight = sum(TRADERS[k]['weight'] for k in proposals if proposals[k]['entry'] and proposals[k]['direction'] == direction)
        weighted_entry = sum(proposals[k]['entry'] * TRADERS[k]['weight'] for k in proposals if proposals[k]['entry'] and proposals[k]['direction'] == direction) / total_weight
        weighted_sl = sum(proposals[k]['sl'] * TRADERS[k]['weight'] for k in proposals if proposals[k]['sl'] and proposals[k]['direction'] == direction) / total_weight
        weighted_tp = sum(proposals[k]['tp'] * TRADERS[k]['weight'] for k in proposals if proposals[k]['tp'] and proposals[k]['direction'] == direction) / total_weight
        
        w_risk = abs(weighted_entry - weighted_sl)
        w_reward = abs(weighted_tp - weighted_entry)
        w_rr = w_reward / w_risk if w_risk > 0 else 0
        
        final_levels = {'entry': weighted_entry, 'sl': weighted_sl, 'tp': weighted_tp, 'rr': w_rr}
    
    console.print(f"\nFinal Levels:")
    console.print(f"Entry: ${final_levels['entry']:.2f}")
    console.print(f"SL: ${final_levels['sl']:.2f}")
    console.print(f"TP: ${final_levels['tp']:.2f}")
    console.print(f"R:R: 1:{final_levels['rr']:.1f}")
    
    return True, final_levels

def round_3_kelly_validation(consensus, final_levels):
    console.print("\nROUND 3: Kelly Sizing + Validation")
    
    risk_dist = abs(final_levels['entry'] - final_levels['sl'])
    base_size = params['risk_dollars'] / risk_dist / 0.10
    
    sizes = []
    approvals = []
    kelly_fractions = []
    
    for key in COUNCIL_ORDER:
        t = TRADERS[key]
        
        prompt = f"""Final validation for {consensus['direction']} trade:

Direction: {consensus['direction']}
Entry: ${final_levels['entry']:.2f}
SL: ${final_levels['sl']:.2f}
TP: ${final_levels['tp']:.2f}
R:R: 1:{final_levels['rr']:.1f}
Probability: {consensus['probability']:.2f}

Account: ${params['account_size']:.2f}
Risk: {params['risk_percent']}% = ${params['risk_dollars']:.2f}
Risk Distance: ${risk_dist:.2f}
Base Size: {base_size:.2f} microlots

Kelly Formula: f = (p * b - q) / b
where p={consensus['probability']:.2f}, b={final_levels['rr']:.1f}, q={1-consensus['probability']:.2f}

Calculate Kelly fraction and adjusted size.

VALIDATION CHECKS:
- R:R >= {params['min_rr']}
- Probability >= 0.60
- Risk Distance >= $10
- VIX < 25 (current: {macro_data.get('vix', 'N/A')})

OUTPUT:
KELLY_FRACTION: 0.XX
ADJUSTED_SIZE: X.XX microlots
VOTE: APPROVE / VETO
WHY: [1 sentence]"""
        
        response = ai_call(key, prompt, max_tok=400)
        console.print(f"{t['name']}: {response}")
        
        size_match = re.search(r'ADJUSTED_SIZE:\s*([\d.]+)', response, re.I)
        kelly_match = re.search(r'KELLY_FRACTION:\s*([\d.]+)', response, re.I)
        vote_match = re.search(r'VOTE:\s*(APPROVE|VETO)', response, re.I)
        
        size = float(size_match.group(1)) if size_match else base_size
        kelly = float(kelly_match.group(1)) if kelly_match else 1.0
        vote = vote_match.group(1).upper() if vote_match else 'APPROVE'
        
        sizes.append(size)
        kelly_fractions.append(kelly)
        approvals.append(vote == 'APPROVE')
        
        meeting_log.append({"round": 3, "model": t['name'], "key": key, "response": response})
    
    median_size = sorted(sizes)[len(sizes)//2]
    avg_kelly = sum(kelly_fractions) / len(kelly_fractions)
    final_size = median_size * avg_kelly
    approve_count = sum(approvals)
    
    console.print(f"\nFinal Size: {final_size:.2f} microlots")
    console.print(f"Median: {median_size:.2f} x Avg Kelly: {avg_kelly:.2f}")
    console.print(f"Approval: {approve_count}/5")
    
    checks = [
        ("R:R >= Min", final_levels['rr'] >= params['min_rr'], f"1:{final_levels['rr']:.1f}"),
        ("Probability >= 0.60", consensus['probability'] >= 0.60, f"{consensus['probability']:.2f}"),
        ("Risk Dist >= $10", risk_dist >= 10, f"${risk_dist:.2f}"),
        ("VIX < 25", macro_data.get('vix', 100) < 25, f"{macro_data.get('vix', 'N/A')}"),
        ("Supermajority", approve_count >= 4, f"{approve_count}/5")
    ]
    
    all_pass = True
    for name, passed, val in checks:
        status = "PASS" if passed else "FAIL"
        console.print(f"{name}: {status} ({val})")
        if not passed:
            all_pass = False
    
    if not all_pass:
        console.print("\nTRADE REJECTED")
        return False, None
    
    console.print("\nTRADE APPROVED")
    return True, {'size': final_size, 'kelly': avg_kelly, 'base_size': base_size}

def save_trade_plan(consensus, final_levels, execution):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fn = f"trade_plan_{ts}.txt"
    
    with open(fn, "w", encoding='utf-8') as f:
        f.write("XAU/USD TRADE PLAN\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Account: ${params['account_size']:.0f} | Risk: {params['risk_percent']}%\n\n")
        
        f.write("SETUP:\n")
        f.write(f"Direction: {consensus['direction']}\n")
        f.write(f"Entry: ${final_levels['entry']:.2f}\n")
        f.write(f"SL: ${final_levels['sl']:.2f} (${abs(final_levels['entry']-final_levels['sl']):.2f})\n")
        f.write(f"TP: ${final_levels['tp']:.2f}\n")
        f.write(f"Size: {execution['size']:.2f} microlots\n")
        f.write(f"Risk: ${params['risk_dollars']:.2f}\n")
        f.write(f"R:R: 1:{final_levels['rr']:.1f}\n")
        f.write(f"Probability: {consensus['probability']:.2f}\n\n")
        
        f.write("MACRO INTELLIGENCE:\n")
        f.write(f"Regime: {macro_data.get('regime', 'N/A')}\n")
        f.write(f"Gold: ${macro_data.get('gold_macro', tech_data.get('current_price', 'N/A'))}\n")
        f.write(f"DXY: {macro_data.get('dxy', 'N/A')}\n")
        f.write(f"VIX: {macro_data.get('vix', 'N/A')}\n")
        f.write(f"Fed: {macro_data.get('fed_stance', 'N/A')}\n")
        f.write(f"10Y: {macro_data.get('treasury_10y', 'N/A')}%\n")
        f.write(f"Real Rate: {macro_data.get('real_rate', 'N/A')}%\n\n")
        
        f.write("DOMINANT FORCES:\n")
        f.write(f"{macro_data.get('dominant_forces', 'N/A')[:500]}\n\n")
        
        f.write("TECHNICAL CONTEXT:\n")
        f.write(f"Current: ${tech_data.get('current_price', 'N/A')}\n")
        f.write(f"Day Range: ${tech_data.get('day_low', 'N/A')} - ${tech_data.get('day_high', 'N/A')}\n")
        f.write(f"EMA50: ${tech_data.get('ema50', 'N/A')}\n")
        f.write(f"EMA200: ${tech_data.get('ema200', 'N/A')}\n")
        f.write(f"RSI: {tech_data.get('rsi', 'N/A')}\n\n")
        
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
        
        f.write("MEETING LOG:\n")
        for entry in meeting_log:
            f.write(f"\n[Round {entry['round']}] {entry['model']}:\n{entry['response']}\n")
    
    console.print(f"Saved: {fn}")
    return fn

def main():
    global params
    
    console.print(Panel(
        "AI Trading Council v5 Streamlined\n"
        "16 Total Calls | 4 Rounds | Supermajority Consensus",
        border_style="cyan"
    ))
    
    missing = []
    for k, v in [("GROQ", GROQ_API_KEY), ("GEMINI", GEMINI_API_KEY), 
                 ("SAMBANOVA", SAMBANOVA_API_KEY), ("CEREBRAS", CEREBRAS_API_KEY)]:
        if not v:
            missing.append(k)
    if missing:
        console.print(f"Missing APIs: {', '.join(missing)}")
        console.print("All APIs required")
        sys.exit(1)
    
    params = get_params()
    
    if not load_reports():
        sys.exit(1)
    
    console.print(Panel(
        f"Data Loaded:\n"
        f"Regime: {macro_data.get('regime', 'N/A')[:50]}\n"
        f"XAUUSD: ${tech_data.get('current_price', 'N/A')}\n"
        f"DXY: {macro_data.get('dxy', 'N/A')} | VIX: {macro_data.get('vix', 'N/A')}\n"
        f"Fed: {macro_data.get('fed_stance', 'N/A')} | Real Rate: {macro_data.get('real_rate', 'N/A')}%",
        border_style="green"
    ))
    
    if not round_0_pre_filter():
        sys.exit(0)
    
    success, consensus = round_1_direction_and_levels()
    if not success:
        sys.exit(0)
    
    success, final_levels = round_2_levels_refinement(consensus)
    if not success:
        sys.exit(0)
    
    success, execution = round_3_kelly_validation(consensus, final_levels)
    if not success:
        sys.exit(0)
    
    filename = save_trade_plan(consensus, final_levels, execution)
    
    console.print(Panel(
        f"TRADE PLAN COMPLETE\n\n"
        f"Direction: {consensus['direction']}\n"
        f"Entry: ${final_levels['entry']:.2f}\n"
        f"SL: ${final_levels['sl']:.2f}\n"
        f"TP: ${final_levels['tp']:.2f}\n"
        f"Size: {execution['size']:.2f} microlots\n"
        f"R:R: 1:{final_levels['rr']:.1f}\n"
        f"Probability: {consensus['probability']:.2f}\n\n"
        f"Saved: {filename}",
        title="EXECUTION READY",
        border_style="green"
    ))

if __name__ == "__main__":
    main()