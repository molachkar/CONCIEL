import json
import requests
from datetime import datetime
from typing import Dict, Optional
from config import API_KEYS, AGENT_CONFIGS
from base_agent import BaseAgent

class NarrativeAgent(BaseAgent):
    def __init__(self):
        super().__init__("narrative")
        self.api_key = API_KEYS.get("sambanova", "")
        self.api_endpoint = "https://api.sambanova.ai/v1/chat/completions"
    
    def build_prompt(self, date: str, today_data: Dict, memory: Optional[Dict]) -> str:
        memory_section = "First analysis - no historical context." if memory is None else f"MEMORY:\n{json.dumps(memory, indent=2)}"
        
        return f"""NARRATIVE analyst for gold intelligence system.

{memory_section}

TODAY'S DATA ({date}):
News: {today_data.get('news.txt', 'N/A')}
Forums: {today_data.get('forums.txt', 'N/A')}

TASK: Analyze news headlines, social sentiment, catalysts, geopolitical risk, sentiment shifts.
Output regime: RISK_ON_NARRATIVE / RISK_OFF_NARRATIVE / NEUTRAL_NARRATIVE / BULLISH_SENTIMENT / BEARISH_SENTIMENT

Return ONLY valid JSON:
{{"metadata":{{"agent":"narrative","date":"{date}","timestamp":"{datetime.now().isoformat()}","model":"Meta-Llama-3.3-70B"}},"data_snapshot":{{"dominant_story":"...","sentiment":"...","catalysts":"...","geopolitical":"..."}},"analysis":{{"regime":"RISK_ON_NARRATIVE/RISK_OFF_NARRATIVE/NEUTRAL_NARRATIVE/BULLISH_SENTIMENT/BEARISH_SENTIMENT","trend":"...","key_drivers":["..."],"reasoning":"...","confidence":0.85,"risk_factors":["..."]}},"memory_references":{{"compared_to":[],"corrections":[]}}}}"""
    
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
                    "model": "Meta-Llama-3.3-70B-Instruct",
                    "messages": [
                        {"role": "system", "content": "Respond ONLY with valid JSON."},
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
    agent = NarrativeAgent()
    result = agent.analyze("2026-01-20")
    
    if result:
        print(json.dumps(result, indent=2))
    else:
        print("Analysis failed")
    
    print("\ndone")