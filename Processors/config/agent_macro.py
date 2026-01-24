import json
import requests
from datetime import datetime
from typing import Dict, Optional
from config import API_KEYS, AGENT_CONFIGS
from base_agent import BaseAgent

class MacroAgent(BaseAgent):
    def __init__(self):
        super().__init__("macro")
        self.api_key = API_KEYS.get("cerebras", "")
        self.api_endpoint = "https://api.cerebras.ai/v1/chat/completions"
    
    def build_prompt(self, date: str, today_data: Dict, memory: Optional[Dict]) -> str:
        memory_section = "First analysis - no historical context." if memory is None else f"MEMORY:\n{json.dumps(memory, indent=2)}"
        
        prompt = f"""MACRO analyst for gold intelligence system.

{memory_section}

TODAY'S DATA ({date}):
Calendar: {today_data.get('calendar.txt', 'N/A')}
Fundamentals: {today_data.get('fundamentals.txt', 'N/A')}
Monthly: {today_data.get('monthly_fundamentals.txt', 'N/A')}

TASK: Analyze Fed policy, rates, inflation. Calculate Real Rate = T10Y - CPI.
Output regime: RISK_ON (dovish Fed, falling real rates) / RISK_OFF (hawkish Fed, rising real rates) / NEUTRAL

Return ONLY valid JSON:
{{"metadata":{{"agent":"macro","date":"{date}","timestamp":"{datetime.now().isoformat()}","model":"Qwen-235B"}},"data_snapshot":{{"economic_events":"...","rates":"...","inflation":"...","real_rate":"..."}},"analysis":{{"regime":"RISK_ON/OFF/NEUTRAL","trend":"...","key_drivers":["..."],"reasoning":"...","confidence":0.85,"risk_factors":["..."]}},"memory_references":{{"compared_to":[],"corrections":[]}}}}"""
        return prompt
    
    def call_llm(self, prompt: str) -> str:
        if not self.api_key:
            raise Exception("Cerebras API key not configured")
        
        response = requests.post(
            self.api_endpoint,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={"model": "llama3.3-70b", "messages": [{"role": "system", "content": "Respond ONLY with valid JSON."}, {"role": "user", "content": prompt}], "temperature": self.config['temperature'], "max_tokens": self.config['max_tokens']},
            timeout=60
        )
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content'].strip()
        return content.replace('```json', '').replace('```', '').strip()
