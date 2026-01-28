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
    
    def analyze(self, date: str) -> Optional[Dict]:
        """Override analyze to check for data availability first"""
        try:
            # Load today's files
            today_data = super().load_today_data(date)
            
            # Check for usable data
            has_news = today_data.get('news.txt') and today_data['news.txt'].strip() not in ['N/A', '', 'No data', '[ERROR']
            has_forums = today_data.get('forums.txt') and today_data['forums.txt'].strip() not in ['N/A', '', 'No data', '[ERROR']
            
            # If BOTH missing, skip
            if not has_news and not has_forums:
                print(f"⚠️  NARRATIVE AGENT: Skipping {date} - no news or forums data available")
                return None
            
            # Warn if partial data
            if not has_news:
                print(f"⚠️  NARRATIVE AGENT: {date} - news.txt missing, using forums only")
            if not has_forums:
                print(f"⚠️  NARRATIVE AGENT: {date} - forums.txt missing, using news only")
            
            # Load memory
            memory = super().load_memory(date)
            
            # Build prompt
            prompt = self.build_prompt(date, today_data, memory, has_news, has_forums)
            
            # Call LLM
            llm_response = self.call_llm(prompt)
            
            # Parse and validate
            result = json.loads(llm_response)
            
            # Validate output
            if not super().validate_output(result):
                print(f"❌ NARRATIVE AGENT: {date} - Output validation failed")
                return None
            
            # Save output
            if not super().save_output(date, result):
                print(f"❌ NARRATIVE AGENT: {date} - Failed to save output")
                return None
            
            print(f"✅ NARRATIVE AGENT: {date} completed")
            return result
            
        except Exception as e:
            print(f"❌ NARRATIVE AGENT ERROR on {date}: {e}")
            return None
    
    def build_prompt(self, date: str, today_data: Dict, memory: Optional[Dict], 
                     has_news: bool, has_forums: bool) -> str:
        memory_section = "First analysis - no historical context." if memory is None else f"MEMORY:\n{json.dumps(memory, indent=2)}"
        
        data_note = ""
        if not has_news:
            data_note = "⚠️ NEWS DATA MISSING - Analyze forums only\n"
        elif not has_forums:
            data_note = "⚠️ FORUMS DATA MISSING - Analyze news only\n"
        
        return f"""NARRATIVE analyst for gold intelligence system.

{memory_section}

{data_note}TODAY'S DATA ({date}):
News: {today_data.get('news.txt', 'N/A')}
Forums: {today_data.get('forums.txt', 'N/A')}

TASK: Analyze news headlines, social sentiment, catalysts, geopolitical risk, sentiment shifts.

Output regime: RISK_ON_NARRATIVE / RISK_OFF_NARRATIVE / NEUTRAL_NARRATIVE / BULLISH_SENTIMENT / BEARISH_SENTIMENT

Return ONLY valid JSON (NO confidence score):
{{"metadata":{{"agent":"narrative","date":"{date}","timestamp":"{datetime.now().isoformat()}","model":"Meta-Llama-3.3-70B"}},"data_snapshot":{{"dominant_story":"...","sentiment":"...","catalysts":"...","geopolitical":"...","data_quality":"{'partial - news only' if not has_forums else 'partial - forums only' if not has_news else 'complete'}"}},"analysis":{{"regime":"RISK_ON_NARRATIVE/RISK_OFF_NARRATIVE/NEUTRAL_NARRATIVE","trend":"...","key_drivers":["..."],"reasoning":"...","risk_factors":["..."]}},"memory_references":{{"compared_to":[],"corrections":[]}}}}"""
    
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
                        {"role": "system", "content": "Respond ONLY with valid JSON. NO confidence scores."},
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
        print("Analysis failed or skipped due to missing data")
    
    print("\ndone")