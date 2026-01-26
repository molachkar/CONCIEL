import json
import requests
from datetime import datetime
from typing import Dict, Optional
from config import API_KEYS, AGENT_CONFIGS
from base_agent import BaseAgent

class MarketAgent(BaseAgent):
    def __init__(self):
        super().__init__("market")
        self.api_key = API_KEYS.get("cerebras", "")
        self.api_endpoint = "https://api.cerebras.ai/v1/chat/completions"
    
    def build_prompt(self, date: str, today_data: Dict, memory: Optional[Dict]) -> str:
        memory_section = "First analysis - no historical context." if memory is None else f"MEMORY:\n{json.dumps(memory, indent=2)}"
        return f"""MARKET analyst for gold intelligence system.

{memory_section}

TODAY'S DATA ({date}):
Technicals: {today_data.get('technicals.txt', 'N/A')}
Calculations: {today_data.get('calculos.txt', 'N/A')}

TASK: Analyze price action, momentum (RSI/MACD/ADX), volatility regime, cross-asset signals (DXY/SPX/VIX).
Output regime: BREAKOUT / BREAKDOWN / CONSOLIDATION / RISK_ON / RISK_OFF

Return ONLY valid JSON:
{{"metadata":{{"agent":"market","date":"{date}","timestamp":"{datetime.now().isoformat()}","model":"deepseek-r1-distill-llama-70b"}},"data_snapshot":{{"price_action":"...","momentum":"...","volatility":"...","cross_assets":"..."}},"analysis":{{"regime":"BREAKOUT/BREAKDOWN/CONSOLIDATION/RISK_ON/RISK_OFF","trend":"...","key_drivers":["..."],"reasoning":"...","confidence":0.85,"risk_factors":["..."]}},"memory_references":{{"compared_to":[],"corrections":[]}}}}"""
    
    def call_llm(self, prompt: str) -> str:
        if not self.api_key:
            raise Exception("Cerebras API key not configured")
        response = requests.post(self.api_endpoint, headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}, json={"model": "deepseek-r1-distill-llama-70b", "messages": [{"role": "system", "content": "Respond ONLY with valid JSON."}, {"role": "user", "content": prompt}], "temperature": self.config['temperature'], "max_tokens": self.config['max_tokens']}, timeout=60)
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content'].strip()
        return content.replace('```json', '').replace('```', '').strip()

if __name__ == "__main__":
    agent = MarketAgent()
    result = agent.analyze("2026-01-20")
    print(json.dumps(result, indent=2) if result else "Analysis failed")
    print("\ndone")