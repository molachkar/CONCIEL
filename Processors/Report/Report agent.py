import json
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent / "config"))

from config_report import (
    API_KEYS, 
    REPORT_LLM_FALLBACKS, 
    STICKY_MODEL_CONFIG,
    REPORT_CONFIG,
    get_working_file
)

class ReportAgent:
    
    def __init__(self, agent_name: str, char_budget: int):
        self.agent_name = agent_name
        self.char_budget = char_budget
        self.fallback_models = REPORT_LLM_FALLBACKS
        self.sticky_model_index = 0
        
    def load_json_files(self, json_files: List[Path]) -> List[Dict]:
        data = []
        for file_path in json_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data.append(json.load(f))
            except Exception as e:
                print(f"Warning: Failed to load {file_path.name}: {e}")
        data.sort(key=lambda x: x.get('date', ''))
        return data
    
    def _detect_error_type(self, error_response: str) -> str:
        error_str = str(error_response).lower()
        if any(x in error_str for x in ["context_length", "token limit", "too many tokens"]):
            return "token limit"
        elif any(x in error_str for x in ["rate limit", "rate_limit"]):
            return "rate limit"
        elif any(x in error_str for x in ["timeout", "timed out"]):
            return "timeout"
        else:
            return "error"
    
    def _call_model_with_config(self, prompt: str, model_config: Dict) -> Tuple[bool, Optional[str], Optional[str]]:
        model_name = model_config['name']
        api_endpoint = model_config['api_endpoint']
        max_tokens = model_config['max_tokens']
        provider = model_config['provider']
        
        api_key = API_KEYS.get(provider, "")
        if not api_key:
            return False, None, "No API key"
        
        try:
            response = requests.post(
                api_endpoint,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": "Professional financial analyst. Write clear, evidence-based analysis."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": REPORT_CONFIG['temperature'],
                    "max_tokens": max_tokens
                },
                timeout=REPORT_CONFIG['timeout']
            )
            
            response.raise_for_status()
            content = response.json()['choices'][0]['message']['content'].strip()
            return True, content, None
            
        except Exception as e:
            error_msg = str(e)
            try:
                error_detail = response.json()
                error_msg = json.dumps(error_detail)
            except:
                pass
            return False, None, error_msg
    
    def call_llm(self, prompt: str) -> str:
        sticky_config = self.fallback_models[self.sticky_model_index]
        success, response, error = self._call_model_with_config(prompt, sticky_config)
        
        if success:
            return response
        
        error_type = self._detect_error_type(str(error))
        print(f"{self.agent_name}: {sticky_config['name']} failed ({error_type}), trying fallbacks")
        
        for idx, model_config in enumerate(self.fallback_models):
            if idx == self.sticky_model_index:
                continue
            
            success, response, error = self._call_model_with_config(prompt, model_config)
            
            if success:
                if STICKY_MODEL_CONFIG['persist_across_agents']:
                    self.sticky_model_index = idx
                    print(f"{self.agent_name}: Switched to {model_config['name']}")
                return response
        
        raise Exception(f"All models failed ({error_type})")
    
    def save_working_file(self, content: str, start_date: str, end_date: str):
        working_file = get_working_file(self.agent_name, start_date, end_date)
        try:
            with open(working_file, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            print(f"Warning: Failed to save working file: {e}")
    
    def generate(self, all_data: List[Dict], previous_outputs: List[str], 
                 start_date: str, end_date: str) -> str:
        raise NotImplementedError("Subclass must implement generate()")


class MacroReportAgent(ReportAgent):
    
    def __init__(self):
        super().__init__("agent1_macro", REPORT_CONFIG['agent1_char_budget'])
    
    def generate(self, all_data: List[Dict], previous_outputs: List[str], 
                 start_date: str, end_date: str) -> str:
        
        num_days = len(all_data)
        
        prompt = f"""Write Part I of a gold market intelligence report analyzing {num_days} days ({start_date} to {end_date}).

STRUCTURE (4-5 pages, ~{self.char_budget} chars):

PART I: MACRO REGIME ANALYSIS

1. EXECUTIVE SUMMARY
Overview of macro evolution, key inflection points, primary drivers.

2. FEDERAL RESERVE POLICY TRAJECTORY
FEDFUNDS evolution. Identify distinct phases (dovish/hawkish). Use narrative paragraphs to explain each phase. Use bullets only for rate timeline data.

3. REAL RATE REGIME ANALYSIS
Calculate T10Y - CPI_YoY path. Identify phases. Correlate with gold price movements from market data. Example format: "Real rate compressed from 4.35% to 3.85% during Dec 1-8. Cross-referencing market data shows gold rallied from $4150 to $4320 (+4.1%). This validates real rate compression triggers gold appreciation."

4. CROSS-ASSET CORRELATION
DXY inverse correlation with gold. S&P500 risk-on/risk-off alignment. VIX as regime validator. Calculate correlation coefficients where possible.

5. INFLATION DYNAMICS
CPI trajectory. Michigan inflation expectations. Impact on real rates.

6. HANDOFF TO AGENT 2
List macro inflection dates that need technical validation. State correlation findings. Pose specific questions for market analysis.

INSTRUCTIONS:
- You have {num_days} JSON files with macro, market, and narrative data
- Primary focus: macro regime BUT cross-validate with gold prices and sentiment
- Write in professional Financial Times style prose
- Paragraphs for analysis, bullets only for data tables
- Each paragraph max 6-8 lines
- When discussing macro events, cite gold price response
- Be specific with dates, numbers, and evidence
- Calculate real rates for key dates

DATA SAMPLE:
{self._format_data_summary(all_data)}

Write Part I now. Focus on causal relationships between macro factors and gold price movements."""

        print(f"Agent 1: Generating macro analysis")
        output = self.call_llm(prompt)
        self.save_working_file(output, start_date, end_date)
        print(f"Agent 1: Complete ({len(output)} chars)")
        return output
    
    def _format_data_summary(self, all_data: List[Dict]) -> str:
        summary_lines = []
        sample_indices = [0, len(all_data)//2, -1]
        for idx in sample_indices:
            if idx < len(all_data):
                day = all_data[idx]
                date = day.get('date', 'unknown')
                macro = day.get('agents', {}).get('macro', {})
                macro_data = macro.get('data_snapshot', {})
                summary_lines.append(f"{date}: FEDFUNDS={macro_data.get('rates', 'N/A')}, CPI={macro_data.get('inflation', 'N/A')}")
        return "\n".join(summary_lines) + f"\n({len(all_data)} total days)"


class MarketReportAgent(ReportAgent):
    
    def __init__(self):
        super().__init__("agent2_market", REPORT_CONFIG['agent2_char_budget'])
    
    def generate(self, all_data: List[Dict], previous_outputs: List[str], 
                 start_date: str, end_date: str) -> str:
        
        num_days = len(all_data)
        agent1_summary = previous_outputs[0][:1500] if previous_outputs else "No previous context"
        
        prompt = f"""Write Part II of gold market intelligence report analyzing {num_days} days ({start_date} to {end_date}).

AGENT 1 FINDINGS:
{agent1_summary}

STRUCTURE (4-5 pages, ~{self.char_budget} chars):

PART II: MARKET TECHNICAL ANALYSIS

1. EXECUTIVE SUMMARY
Gold price trajectory. Key breakouts/breakdowns with dates. Technical regime.

2. PRICE STRUCTURE EVOLUTION
Opening to closing price path. Support/resistance levels. EMA changes. Ichimoku cloud.

3. MOMENTUM & TREND DYNAMICS
RSI behavior. MACD signals. ADX trend strength. Stochastic patterns.

4. VOLATILITY REGIME ASSESSMENT
ATR evolution. Volatility clustering. Hurst exponent. Accumulation/distribution.

5. MACRO INFLECTION VALIDATION
Validate Agent 1's macro inflection dates with technical data. For each: identify technical response, calculate lag, assess alignment. Create validation table.

6. HANDOFF TO AGENT 3
List technical patterns needing narrative confirmation. Identify anomalies.

INSTRUCTIONS:
- Primary focus: technical BUT validate Agent 1's macro findings
- {num_days} JSON files with market data available
- Professional prose, bullets only for tables
- Be specific with dates and indicators
- Show causal relationships

Write Part II now.
"""

        print(f"Agent 2: Generating market analysis")
        output = self.call_llm(prompt)
        self.save_working_file(output, start_date, end_date)
        print(f"Agent 2: Complete ({len(output)} chars)")
        return output


class NarrativeReportAgent(ReportAgent):
    
    def __init__(self):
        super().__init__("agent3_narrative", REPORT_CONFIG['agent3_char_budget'])
    
    def generate(self, all_data: List[Dict], previous_outputs: List[str], 
                 start_date: str, end_date: str) -> str:
        
        num_days = len(all_data)
        context_summary = ""
        if len(previous_outputs) >= 2:
            context_summary = previous_outputs[0][:800] + "\n...\n" + previous_outputs[1][:800]
        
        prompt = f"""Write Part III (FINAL) of gold market intelligence report analyzing {num_days} days ({start_date} to {end_date}).

PREVIOUS AGENTS:
Agent 1: Macro regime (inflection points, real rates, correlations)
Agent 2: Market technicals (validated macro with price action)

Context:
{context_summary}

STRUCTURE (5-6 pages, ~{self.char_budget} chars):

PART III: NARRATIVE SYNTHESIS & INTEGRATED OUTLOOK

1. EXECUTIVE SUMMARY
Dominant themes. Sentiment regime. Key catalysts.

2. NARRATIVE EVOLUTION
How news/sentiment themes evolved. Narrative-driven moves. Geopolitical risk windows. Forum sentiment.

3. CROSS-DOMAIN PATTERN LIBRARY (MOST IMPORTANT - 2 pages)
Identify 3-5 recurring patterns involving ALL three domains.

For each pattern use this structure:

Pattern N: [Name]

Conditions:
- Macro: [thresholds from Agent 1]
- Market: [indicators from Agent 2]
- Narrative: [sentiment/themes]

Occurrences: X times in {num_days}-day window
[List date ranges]

Outcome: [Price %, duration, success rate]

Mechanism: [2-3 sentence causal explanation]

4. LEAD-LAG RELATIONSHIPS
Which domain leads. Average lags. Anomalies.

5. FORWARD OUTLOOK
Probable scenarios based on patterns. Assign probabilities (must sum to 100%). Risk factors and invalidation signals.

6. APPENDIX: DAILY REGIME TABLE
All {num_days} days in table format:
Date | Macro Regime | Market Regime | Narrative Regime

INSTRUCTIONS:
- Synthesize, don't summarize
- Pattern library reveals NEW insights not visible to individual agents
- Be evidence-based in forward outlook
- This is final section, wrap up professionally
- {num_days} JSON files with narrative data available

Write Part III now. Focus on cross-domain synthesis and pattern discovery."""

        print(f"Agent 3: Generating narrative synthesis")
        output = self.call_llm(prompt)
        self.save_working_file(output, start_date, end_date)
        print(f"Agent 3: Complete ({len(output)} chars)")
        return output