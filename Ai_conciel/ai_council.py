#!/usr/bin/env python3

import os, sys, random, re
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import IntPrompt, FloatPrompt
from rich.table import Table

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

TRADERS = {
    "groq": {
        "name": "Momentum Scalper", 
        "color": "cyan", 
        "style": "bold cyan",
        "personality": "Momentum scalper. Focus: price action, S/R, quick entries. Tight stops, 1:2+ R:R. Trade WITH trend. Max 3 sentences.",
        "model": "llama-3.1-8b-instant", 
        "provider": "groq"
    },
    "gemini": {
        "name": "Swing Trader", 
        "color": "green", 
        "style": "bold green",
        "personality": "Swing structure trader. Focus: market structure, EMAs, HTF context. Wider stops, 1:3+ R:R. WITH HTF trend only. Max 3 sentences.",
        "model": "gemini-2.5-flash", 
        "provider": "gemini"
    },
    "sambanova": {
        "name": "Risk Quant", 
        "color": "magenta", 
        "style": "bold magenta",
        "personality": "Risk quant. Focus: position sizing, probability, math. Math-first. If math fails, no trade. Max 3 sentences.",
        "model": "Meta-Llama-3.1-8B-Instruct", 
        "provider": "sambanova"
    },
    "cerebras_llama": {
        "name": "Speed Technician", 
        "color": "blue", 
        "style": "bold blue",
        "personality": "Speed technical analyst. Focus: rapid patterns, key levels, volume. Fast decisions, chart structure, fib, orderblocks. Max 3 sentences.",
        "model": "llama-3.3-70b", 
        "provider": "cerebras"
    },
    "cerebras_qwen": {
        "name": "Macro Quant", 
        "color": "yellow", 
        "style": "bold yellow",
        "personality": "Deep macro quant. Focus: macro-technical synthesis, regime analysis, MTF confluence. Large reasoning, correlations, probability. Max 3 sentences.",
        "model": "qwen-3-235b-a22b-instruct-2507", 
        "provider": "cerebras"
    }
}

params, macro, tech, log = {}, "", "", []

def get_params():
    console.print(Panel("[bold yellow]Trading Parameters[/bold yellow]", border_style="yellow"))
    p = {}
    p['account_size'] = FloatPrompt.ask("[bold]Account Size (USD)[/bold]", default=300.0)
    p['risk_percent'] = FloatPrompt.ask("[bold]Risk (%)[/bold]", default=2.0)
    
    console.print("\n[bold]Timeframe:[/bold] 1.Scalp 2.Intraday 3.Swing")
    p['timeframe'] = {1:"Scalp",2:"Intraday",3:"Swing"}[IntPrompt.ask("Select", default=2)]
    
    console.print("\n[bold]Min R:R:[/bold] 1.1:2 2.1:3 3.1:5")
    p['min_rr'] = {1:2.0,2:3.0,3:5.0}[IntPrompt.ask("Select", default=1)]
    
    console.print("\n[bold]Style:[/bold] 1.Aggressive 2.Balanced 3.Conservative")
    p['style'] = {1:"Aggressive",2:"Balanced",3:"Conservative"}[IntPrompt.ask("Select", default=2)]
    
    p['risk_dollars'] = (p['account_size'] * p['risk_percent']) / 100
    
    t = Table(title="Parameters")
    t.add_column("Param", style="cyan")
    t.add_column("Value", style="green")
    t.add_row("Account", f"${p['account_size']:.2f}")
    t.add_row("Risk/Trade", f"{p['risk_percent']}% (${p['risk_dollars']:.2f})")
    t.add_row("Timeframe", p['timeframe'])
    t.add_row("Min R:R", f"1:{p['min_rr']}")
    t.add_row("Style", p['style'])
    console.print(t)
    return p

def optimize_macro(txt):
    """
    Extract structured key metrics from the macro report.
    Expects a KEY METRICS SNAPSHOT section at the top of the report.
    """
    try:
        output = []
        
        # Extract the KEY METRICS SNAPSHOT section if present
        metrics_section = re.search(
            r'## KEY METRICS SNAPSHOT\s*\n(.*?)\n---', 
            txt, 
            re.DOTALL | re.IGNORECASE
        )
        
        if metrics_section:
            metrics_text = metrics_section.group(1)
            
            # Extract Regime (in quotes)
            regime = re.search(r'\*\*Regime\*\*:\s*"([^"]+)"', metrics_text, re.I)
            if regime:
                output.append(f"REGIME: {regime.group(1)}")
            
            # Extract Gold price
            gold = re.search(r'\*\*XAU/USD\*\*:\s*\$?([\d,]+\.?\d*)', metrics_text, re.I)
            if gold:
                output.append(f"Gold: ${gold.group(1)}")
            
            # Extract DXY
            dxy = re.search(r'\*\*DXY\*\*:\s*([\d,]+\.?\d*)', metrics_text, re.I)
            if dxy:
                output.append(f"DXY: {dxy.group(1)}")
            
            # Extract VIX
            vix = re.search(r'\*\*VIX\*\*:\s*([\d,]+\.?\d*)', metrics_text, re.I)
            if vix:
                output.append(f"VIX: {vix.group(1)}")
            
            # Extract Fed Stance
            fed = re.search(r'\*\*Fed Stance\*\*:\s*(\w+)', metrics_text, re.I)
            if fed:
                output.append(f"Fed: {fed.group(1)}")
            
            # Extract 10Y Treasury
            treasury = re.search(r'\*\*10Y Treasury\*\*:\s*([\d.]+)%?', metrics_text, re.I)
            if treasury:
                output.append(f"10Y: {treasury.group(1)}%")
            
            # Extract Real Rate Estimate
            real_rate = re.search(r'\*\*Real Rate Estimate\*\*:\s*([+-]?[\d.]+)%?', metrics_text, re.I)
            if real_rate:
                output.append(f"Real Rate: {real_rate.group(1)}%")
        
        # Fallback: try old extraction methods if KEY METRICS section not found
        if not output:
            regime = re.search(r'regime.*?[""]([^""]+)[""]', txt, re.I)
            if regime:
                output.append(f"REGIME: {regime.group(1)}")
            
            gold = re.search(r'XAU/USD.*?(\$?[\d,]+\.?\d*)', txt, re.I)
            if gold:
                output.append(f"Gold: {gold.group(1)}")
            
            if 'dovish' in txt.lower():
                output.append("Fed: Dovish")
            elif 'hawkish' in txt.lower():
                output.append("Fed: Hawkish")
            
            dxy = re.search(r'DXY.*?(\d+\.?\d*)', txt, re.I)
            if dxy:
                output.append(f"DXY: {dxy.group(1)}")
            
            vix = re.search(r'VIX.*?(\d+\.?\d*)', txt, re.I)
            if vix:
                output.append(f"VIX: {vix.group(1)}")
        
        # Return formatted output or fallback
        if output:
            return "\n".join(output)
        else:
            return "Limited macro data - check report format"
    
    except Exception as e:
        # If all parsing fails, return truncated text
        return txt[:500] + "\n\n[Parsing failed - using raw excerpt]"

def load_reports():
    global macro, tech
    rp = Path("Ai_conciel/reports")
    if not rp.exists():
        console.print("[red]No reports folder[/red]")
        return False
    
    mf = list(rp.glob("*gold_regime*.md")) + list(rp.glob("*macro*.txt")) + list(rp.glob("*macro*.md"))
    if not mf:
        console.print("[red]No macro reports[/red]")
        return False
    
    console.print("\n[bold]Macro Reports:[/bold]")
    for i,f in enumerate(mf,1): 
        console.print(f"  {i}. {f.name}")
    c = IntPrompt.ask("Select", default=1)
    if c<1 or c>len(mf): 
        return False
    
    for enc in ['utf-8','latin-1','cp1252']:
        try:
            with open(mf[c-1],'r',encoding=enc,errors='replace') as f:
                macro = optimize_macro(f.read())
            break
        except: 
            continue
    
    tf = list(rp.glob("technical*.txt")) + list(rp.glob("technical*.md"))
    if not tf:
        tech = "No technical data"
    else:
        console.print("\n[bold]Technical Reports:[/bold]")
        for i,f in enumerate(tf,1): 
            console.print(f"  {i}. {f.name}")
        c = IntPrompt.ask("Select", default=1)
        if 1<=c<=len(tf):
            for enc in ['utf-8','latin-1','cp1252']:
                try:
                    with open(tf[c-1],'r',encoding=enc,errors='replace') as f:
                        tech = f.read()
                    break
                except: 
                    continue
    return True

def ai_call(key, prompt, sys, max_tok=300):
    t = TRADERS[key]
    prov = t["provider"]
    try:
        if prov == "groq":
            if not groq_client: 
                return "[Groq not init]"
            r = groq_client.chat.completions.create(
                model=t["model"],
                messages=[{"role":"system","content":sys},{"role":"user","content":prompt}],
                max_tokens=max_tok, 
                temperature=0.7
            )
            return r.choices[0].message.content or "[No response]"
        elif prov == "gemini":
            if not gemini_client: 
                return "[Gemini not init]"
            r = gemini_client.models.generate_content(
                model=t["model"], 
                contents=f"{sys}\n\n{prompt}"
            )
            return r.text or "[No response]"
        elif prov == "sambanova":
            if not sambanova_client: 
                return "[SambaNova not init]"
            r = sambanova_client.chat.completions.create(
                model=t["model"],
                messages=[{"role":"system","content":sys},{"role":"user","content":prompt}],
                max_tokens=max_tok, 
                temperature=0.7
            )
            return r.choices[0].message.content or "[No response]"
        elif prov == "cerebras":
            if not cerebras_client: 
                return "[Cerebras not init]"
            r = cerebras_client.chat.completions.create(
                model=t["model"],
                messages=[{"role":"system","content":sys},{"role":"user","content":prompt}],
                max_tokens=max_tok, 
                temperature=0.7
            )
            return r.choices[0].message.content or "[No response]"
    except Exception as e:
        return f"[Error: {e}]"

def vote_direction(order):
    console.print(Panel("[bold]ROUND 1: DIRECTION[/bold]\nVote: BUY/SELL/NO TRADE", border_style="yellow"))
    votes = {}
    for k in order:
        t = TRADERS[k]
        p = f"Account: ${params['account_size']} | Risk: {params['risk_percent']}% | TF: {params['timeframe']}\n\nMACRO:\n{macro}\n\nTECH:\n{tech}\n\nVote DIRECTION: BUY/SELL/NO TRADE\nOne sentence why.\nFormat:\nVOTE: [choice]\nWHY: [sentence]"
        with console.status(f"[{t['color']}]{t['name']}...[/{t['color']}]"):
            resp = ai_call(k, p, t["personality"])
        console.print(f"[{t['style']}]{t['name']}:[/{t['style']}] {resp}")
        vm = re.search(r'VOTE:\s*(BUY|SELL|NO TRADE)', resp, re.I)
        votes[k] = {"vote": vm.group(1).upper() if vm else "NO TRADE", "reasoning": resp}
        log.append(f"[{t['name']}] Dir: {votes[k]['vote']}")
    
    buy = sum(1 for v in votes.values() if v["vote"]=="BUY")
    sell = sum(1 for v in votes.values() if v["vote"]=="SELL")
    no = sum(1 for v in votes.values() if v["vote"]=="NO TRADE")
    cons = max(buy,sell,no)/len(votes)
    
    if buy>sell and buy>no: 
        direction = "BUY"
    elif sell>buy and sell>no: 
        direction = "SELL"
    else: 
        direction = "NO TRADE"
    
    console.print(f"\n[bold]CONSENSUS:[/bold] {direction} ({buy} BUY, {sell} SELL, {no} NO)\n[bold]Agreement:[/bold] {cons*100:.0f}%")
    return {"direction":direction, "consensus":cons, "votes":votes, "buy":buy, "sell":sell, "no_trade":no}

def vote_entry(order, direction, prev):
    console.print(Panel(f"[bold]ROUND 2: ENTRY[/bold]\nDirection: {direction}", border_style="yellow"))
    entries = {}
    for k in order:
        t = TRADERS[k]
        pctx = "\n".join([f"{TRADERS[x]['name']}: {v['vote']}" for x,v in prev.items()])
        p = f"Dir: {direction}\nAccount: ${params['account_size']} | Risk: {params['risk_percent']}%\n\nMACRO: {macro}\nTECH: {tech}\n\nPrev votes:\n{pctx}\n\nPropose ENTRY (number) and WHY (sentence).\nFormat:\nENTRY: $[price]\nWHY: [sentence]"
        with console.status(f"[{t['color']}]{t['name']}...[/{t['color']}]"):
            resp = ai_call(k, p, t["personality"])
        console.print(f"[{t['style']}]{t['name']}:[/{t['style']}] {resp}")
        em = re.search(r'ENTRY:\s*\$?([\d,]+\.?\d*)', resp, re.I)
        if em:
            ep = float(em.group(1).replace(',',''))
            entries[k] = {"entry":ep, "reasoning":resp}
            log.append(f"[{t['name']}] Entry: ${ep:.2f}")
        else:
            entries[k] = {"entry":None, "reasoning":resp}
    
    valid = [v["entry"] for v in entries.values() if v["entry"]]
    if not valid: 
        return {"entry":None, "spread":0, "votes":entries}
    
    avg = sum(valid)/len(valid)
    spread = max(valid)-min(valid)
    console.print(f"\n[bold]ENTRIES:[/bold] {[f'${e:.2f}' for e in valid]}\n[bold]AVG:[/bold] ${avg:.2f}\n[bold]SPREAD:[/bold] ${spread:.2f}")
    return {"entry":avg, "min":min(valid), "max":max(valid), "spread":spread, "votes":entries}

def vote_sl(order, direction, entry):
    console.print(Panel(f"[bold]ROUND 3: STOP LOSS[/bold]\nDir: {direction} | Entry: ${entry:.2f}", border_style="yellow"))
    stops = {}
    for k in order:
        t = TRADERS[k]
        p = f"Dir: {direction} | Entry: ${entry:.2f}\nAccount: ${params['account_size']} | Risk: {params['risk_percent']}% = ${params['risk_dollars']:.2f}\n\nTECH: {tech}\n\nPropose SL and WHY.\nFormat:\nSL: $[price]\nWHY: [sentence]"
        with console.status(f"[{t['color']}]{t['name']}...[/{t['color']}]"):
            resp = ai_call(k, p, t["personality"])
        console.print(f"[{t['style']}]{t['name']}:[/{t['style']}] {resp}")
        sm = re.search(r'SL:\s*\$?([\d,]+\.?\d*)', resp, re.I)
        if sm:
            sp = float(sm.group(1).replace(',',''))
            stops[k] = {"sl":sp, "reasoning":resp}
            log.append(f"[{t['name']}] SL: ${sp:.2f}")
        else:
            stops[k] = {"sl":None, "reasoning":resp}
    
    valid = [v["sl"] for v in stops.values() if v["sl"]]
    if not valid: 
        return {"sl":None, "risk":None, "votes":stops}
    
    avg = sum(valid)/len(valid)
    risk = abs(entry-avg)
    console.print(f"\n[bold]SLs:[/bold] {[f'${s:.2f}' for s in valid]}\n[bold]AVG:[/bold] ${avg:.2f}\n[bold]RISK:[/bold] ${risk:.2f}")
    return {"sl":avg, "risk":risk, "votes":stops}

def vote_tp(order, direction, entry, sl, risk):
    console.print(Panel(f"[bold]ROUND 4: TP[/bold]\nEntry: ${entry:.2f} | SL: ${sl:.2f} | Risk: ${risk:.2f}\nMin R:R: 1:{params['min_rr']}", border_style="yellow"))
    tps = {}
    min_dist = risk * params['min_rr']
    min_tp = entry + min_dist if direction=="BUY" else entry - min_dist
    
    for k in order:
        t = TRADERS[k]
        p = f"Dir: {direction} | Entry: ${entry:.2f} | SL: ${sl:.2f}\nRisk: ${risk:.2f}\nMin R:R: 1:{params['min_rr']} (TP >= ${min_tp:.2f})\n\nTECH: {tech}\n\nPropose TP and R:R.\nFormat:\nTP: $[price]\nR:R: [ratio]"
        with console.status(f"[{t['color']}]{t['name']}...[/{t['color']}]"):
            resp = ai_call(k, p, t["personality"])
        console.print(f"[{t['style']}]{t['name']}:[/{t['style']}] {resp}")
        tm = re.search(r'TP:\s*\$?([\d,]+\.?\d*)', resp, re.I)
        if tm:
            tp = float(tm.group(1).replace(',',''))
            rew = abs(tp-entry)
            rr = rew/risk if risk>0 else 0
            tps[k] = {"tp":tp, "rr":rr, "reasoning":resp}
            log.append(f"[{t['name']}] TP: ${tp:.2f} (R:R 1:{rr:.1f})")
        else:
            tps[k] = {"tp":None, "rr":None, "reasoning":resp}
    
    valid = [(v["tp"],v["rr"]) for v in tps.values() if v["tp"]]
    if not valid: 
        return {"tp":None, "rr":None, "votes":tps}
    
    avg_tp = sum(t[0] for t in valid)/len(valid)
    avg_rr = sum(t[1] for t in valid)/len(valid)
    console.print(f"\n[bold]TPs:[/bold] {[f'${t[0]:.2f}' for t in valid]}\n[bold]AVG:[/bold] ${avg_tp:.2f}\n[bold]R:R:[/bold] 1:{avg_rr:.1f}")
    if avg_rr < params['min_rr']: 
        console.print(f"[red]R:R below min[/red]")
    return {"tp":avg_tp, "rr":avg_rr, "votes":tps}

def vote_size(order, entry, sl, risk_dollars):
    console.print(Panel(f"[bold]ROUND 5: SIZE[/bold]\nEntry: ${entry:.2f} | SL: ${sl:.2f}\nRisk: ${abs(entry-sl):.2f}\nMax Risk: ${risk_dollars:.2f}", border_style="yellow"))
    sizes = {}
    risk_dist = abs(entry-sl)
    correct = risk_dollars/risk_dist/0.10
    console.print(f"[dim]Math correct: {correct:.2f} microlots[/dim]")
    
    for k in order:
        t = TRADERS[k]
        p = f"Entry: ${entry:.2f} | SL: ${sl:.2f}\nRisk Dist: ${risk_dist:.2f}\nMax Risk: ${risk_dollars:.2f}\nAccount: ${params['account_size']}\n\nCalc position in MICROLOTS.\nFormula: Risk$/RiskDist/$0.10\nShow math.\n\nFormat:\nSIZE: [num] microlots\nMATH: [calc]"
        with console.status(f"[{t['color']}]{t['name']}...[/{t['color']}]"):
            resp = ai_call(k, p, t["personality"])
        console.print(f"[{t['style']}]{t['name']}:[/{t['style']}] {resp}")
        sm = re.search(r'SIZE:\s*([\d.]+)', resp, re.I)
        if sm:
            sz = float(sm.group(1))
            sizes[k] = {"size":sz, "reasoning":resp}
            log.append(f"[{t['name']}] Size: {sz:.2f} microlots")
        else:
            sizes[k] = {"size":None, "reasoning":resp}
    
    valid = [v["size"] for v in sizes.values() if v["size"]]
    if not valid: 
        return {"size":None, "correct":correct, "votes":sizes}
    
    avg = sum(valid)/len(valid)
    console.print(f"\n[bold]SIZES:[/bold] {[f'{s:.2f}' for s in valid]}\n[bold]AVG:[/bold] {avg:.2f}\n[bold green]CORRECT:[/bold green] {correct:.2f}")
    if abs(avg-correct)/correct>0.10: 
        console.print(f"[red]Deviation >10%[/red]")
    return {"size":correct, "proposed_avg":avg, "votes":sizes}

def final_check(res):
    console.print(Panel("[bold]FINAL CHECK[/bold]", border_style="blue"))
    checks = [
        ("Direction", res['direction']['consensus']>=0.60, f"{res['direction']['consensus']*100:.0f}%"),
        ("Entry Spread", res['entry']['spread']<50, f"${res['entry']['spread']:.2f}"),
        ("R:R", res['tp']['rr']>=params['min_rr'], f"1:{res['tp']['rr']:.1f}"),
        ("Size", res['position']['size'] is not None, "Valid")
    ]
    
    t = Table(title="Validation")
    t.add_column("Check", style="cyan")
    t.add_column("Status")
    t.add_column("Value", style="yellow")
    
    ok = True
    for name, passed, val in checks:
        st = "✅ PASS" if passed else "❌ FAIL"
        sty = "green" if passed else "red"
        t.add_row(name, f"[{sty}]{st}[/{sty}]", val)
        if not passed: 
            ok = False
    
    console.print(t)
    console.print(f"\n[{'green' if ok else 'red'}]{'✅ APPROVED' if ok else '❌ NO SETUP'}[/{'green' if ok else 'red'}]")
    return ok

def save_plan(res):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fn = f"trade_plan_{ts}.txt"
    direction = res['direction']['direction']
    entry = res['entry']['entry']
    sl = res['stop']['sl']
    tp = res['tp']['tp']
    rr = res['tp']['rr']
    size = res['position']['size']
    risk = res['stop']['risk']
    
    with open(fn, "w", encoding='utf-8') as f:
        f.write("=== XAU/USD TRADE PLAN ===\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Account: ${params['account_size']:.0f} | Risk: {params['risk_percent']}%\n\n")
        f.write("SETUP:\n")
        f.write(f"Dir: {direction}\nEntry: ${entry:.2f}\nSL: ${sl:.2f} (${risk:.2f})\nTP: ${tp:.2f}\nSize: {size:.2f} microlots\nRisk: ${params['risk_dollars']:.2f}\nR:R: 1:{rr:.1f}\n\n")
        f.write(f"MACRO:\n{macro}\n\nTECH:\n{tech[:300]}...\n\n")
        f.write("EXECUTION:\n")
        f.write(f"1. {direction} at ${entry:.2f}\n2. SL ${sl:.2f}\n3. TP ${tp:.2f}\n4. Size {size:.2f} microlots\n\n")
        f.write("INVALIDATION:\n")
        f.write(f"- Break {'below' if direction=='BUY' else 'above'} ${sl:.2f}\n- Major macro shift\n- VIX >25\n\n")
        f.write("=== LOG ===\n" + "\n".join(log) + "\n")
    
    console.print(f"[green]✅ Saved: {fn}[/green]")
    return fn

def main():
    global params
    console.print(Panel("[bold]AI Trading Council v3[/bold]\n5 Models | Vote-by-Component", border_style="cyan"))
    
    missing = []
    for k,v in [("GROQ",GROQ_API_KEY),("GEMINI",GEMINI_API_KEY),("SAMBANOVA",SAMBANOVA_API_KEY),("CEREBRAS",CEREBRAS_API_KEY)]:
        if not v: 
            missing.append(k)
    if missing:
        console.print(f"[yellow]Missing: {','.join(missing)}[/yellow]")
        console.print("[yellow]Will use available models only[/yellow]")
    
    params = get_params()
    if not load_reports(): 
        sys.exit(1)
    
    console.print(Panel(f"[bold]Data Loaded[/bold]\nMacro:\n{macro}\n\nTech:\n{tech[:200]}...", border_style="green"))
    
    available_keys = []
    if groq_client:
        available_keys.append("groq")
    if gemini_client:
        available_keys.append("gemini")
    if sambanova_client:
        available_keys.append("sambanova")
    if cerebras_client:
        available_keys.extend(["cerebras_llama", "cerebras_qwen"])
    
    order = available_keys[:]
    random.shuffle(order)
    console.print(f"\n[dim]Order: {', '.join([TRADERS[k]['name'] for k in order])}[/dim]")
    
    dir_res = vote_direction(order)
    if dir_res['direction']=="NO TRADE" or dir_res['consensus']<0.60:
        console.print(Panel("[red]NO CLEAR DIRECTION[/red]", border_style="red"))
        sys.exit(0)
    
    random.shuffle(order)
    entry_res = vote_entry(order, dir_res['direction'], dir_res['votes'])
    if not entry_res['entry'] or entry_res['spread']>50:
        console.print(Panel("[red]NO ENTRY CONSENSUS[/red]", border_style="red"))
        sys.exit(0)
    
    random.shuffle(order)
    sl_res = vote_sl(order, dir_res['direction'], entry_res['entry'])
    if not sl_res['sl']:
        console.print(Panel("[red]NO SL CONSENSUS[/red]", border_style="red"))
        sys.exit(0)
    
    random.shuffle(order)
    tp_res = vote_tp(order, dir_res['direction'], entry_res['entry'], sl_res['sl'], sl_res['risk'])
    if not tp_res['tp'] or tp_res['rr']<params['min_rr']:
        console.print(Panel("[red]TP ISSUES[/red]", border_style="red"))
        sys.exit(0)
    
    random.shuffle(order)
    size_res = vote_size(order, entry_res['entry'], sl_res['sl'], params['risk_dollars'])
    
    all_res = {
        'direction': dir_res, 
        'entry': entry_res, 
        'stop': sl_res, 
        'tp': tp_res, 
        'position': size_res
    }
    
    if not final_check(all_res): 
        sys.exit(0)
    
    fn = save_plan(all_res)
    
    console.print(Panel(
        f"[bold green]✅ TRADE APPROVED[/bold green]\n\n"
        f"Dir: {dir_res['direction']}\nEntry: ${entry_res['entry']:.2f}\nSL: ${sl_res['sl']:.2f}\n"
        f"TP: ${tp_res['tp']:.2f}\nSize: {size_res['size']:.2f} microlots\nR:R: 1:{tp_res['rr']:.1f}\n\n"
        f"[bold]Plan:[/bold] {fn}", 
        title="EXECUTE", 
        border_style="green"
    ))

if __name__ == "__main__":
    main()