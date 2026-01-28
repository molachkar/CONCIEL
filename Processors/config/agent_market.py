import json
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional
from config import API_KEYS, AGENT_CONFIGS, AGENT_OUTPUT_DIR
from base_agent import BaseAgent

class MarketAgent(BaseAgent):
    def __init__(self):
        super().__init__("market")
        self.api_key = API_KEYS.get("sambanova", "")
        self.api_endpoint = "https://api.sambanova.ai/v1/chat/completions"
    
    def analyze(self, date: str) -> Optional[Dict]:
        """Override analyze to handle weekend forward-fill"""
        try:
            # Check if weekend
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            is_weekend = date_obj.weekday() in [5, 6]  # Saturday=5, Sunday=6
            
            if is_weekend:
                return self.forward_fill_weekend(date)
            
            # Weekday - normal processing
            return super().analyze(date)
            
        except Exception as e:
            print(f"❌ MARKET AGENT ERROR on {date}: {e}")
            return None
    
    def forward_fill_weekend(self, date: str) -> Optional[Dict]:
        """
        For weekends, copy the last Friday's analysis with a note
        that market was closed.
        """
        print(f"⚠️  MARKET AGENT: {date} is weekend - forward-filling from last trading day")
        
        # Find last trading day (go back max 3 days to find Friday)
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        
        for days_back in range(1, 4):
            lookback_date = (date_obj - timedelta(days=days_back)).strftime("%Y-%m-%d")
            lookback_file = AGENT_OUTPUT_DIR / "market" / f"{lookback_date}.json"
            
            if lookback_file.exists():
                try:
                    with open(lookback_file, 'r') as f:
                        last_trading_data = json.load(f)
                    
                    # Create weekend JSON with market closed note
                    weekend_data = {
                        "metadata": {
                            "agent": "market",
                            "date": date,
                            "timestamp": datetime.now().isoformat(),
                            "model": "DeepSeek-V3.1",
                            "note": "MARKET CLOSED - Using last trading day values",
                            "source_date": lookback_date
                        },
                        "data_snapshot": {
                            "market_status": "CLOSED - Weekend/Holiday",
                            "last_trading_day": lookback_date,
                            **last_trading_data.get('data_snapshot', {})
                        },
                        "analysis": last_trading_data.get('analysis', {}),
                        "memory_references": {
                            "compared_to": [f"Forward-filled from {lookback_date} (last trading day)"],
                            "corrections": []
                        }
                    }
                    
                    # Save the forward-filled output
                    if super().save_output(date, weekend_data):
                        print(f"✅ MARKET AGENT: {date} forward-filled from {lookback_date}")
                        return weekend_data
                    
                except Exception as e:
                    print(f"⚠️  MARKET AGENT: Error loading {lookback_date}: {e}")
                    continue
        
        # If we couldn't find any recent trading day
        print(f"❌ MARKET AGENT: Could not find recent trading day for {date}")
        return None
    
    def build_prompt(self, date: str, today_data: Dict, memory: Optional[Dict]) -> str:
        memory_section = "First analysis - no historical context." if memory is None else f"MEMORY:\n{json.dumps(memory, indent=2)}"
        
        return f"""MARKET analyst for gold intelligence system.

{memory_section}

TODAY'S DATA ({date}):
Technicals: {today_data.get('technicals.txt', 'N/A')}
Calculations: {today_data.get('calculos.txt', 'N/A')}

TASK: Analyze price action, momentum (RSI/MACD/ADX), volatility regime, cross-asset signals (DXY/SPX/VIX).
Output regime: BREAKOUT / BREAKDOWN / CONSOLIDATION / RISK_ON / RISK_OFF

Return ONLY valid JSON (NO confidence score):
{{"metadata":{{"agent":"market","date":"{date}","timestamp":"{datetime.now().isoformat()}","model":"DeepSeek-V3.1"}},"data_snapshot":{{"price_action":"...","momentum":"...","volatility":"...","cross_assets":"..."}},"analysis":{{"regime":"BREAKOUT/BREAKDOWN/CONSOLIDATION/RISK_ON/RISK_OFF","trend":"...","key_drivers":["..."],"reasoning":"...","risk_factors":["..."]}},"memory_references":{{"compared_to":[],"corrections":[]}}}}"""
    
    def call_llm(self, prompt: str) -> str:
        if not self.api_key:
            raise Exception("SambaNova API key not configured")
        
        try:
            response = requests.post(
                self.api_endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "DeepSeek-V3.1",
                    "messages": [
                        {"role": "system", "content": "Respond ONLY with valid JSON. Do not include confidence scores."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": self.config['temperature'],
                    "max_tokens": self.config['max_tokens']
                },
                timeout=60
            )
            response.raise_for_status()
            content = response.json()['choices'][0]['message']['content'].strip()
            return content.replace('```json', '').replace('```', '').strip()
        
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            raise

if __name__ == "__main__":
    agent = MarketAgent()
    result = agent.analyze("2026-01-20")
    
    if result:
        print(json.dumps(result, indent=2))
    else:
        print("Analysis failed")
    
    print("\ndone")