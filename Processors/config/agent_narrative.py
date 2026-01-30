import json
import requests
from datetime import datetime
from typing import Dict, Optional, Tuple
from config import API_KEYS, AGENT_CONFIGS, NARRATIVE_FALLBACK_MODELS, STICKY_MODEL_CONFIG
from base_agent import BaseAgent

class NarrativeAgent(BaseAgent):
    def __init__(self):
        super().__init__("narrative")
        self.fallback_models = NARRATIVE_FALLBACK_MODELS
        self.sticky_model_index = 0
        self.sticky_success_count = 0
    
    def analyze(self, date: str) -> Optional[Dict]:
        """Override analyze to check for data availability first"""
        try:
            today_data = super().load_today_data(date)
            
            has_news = today_data.get('news.txt') and today_data['news.txt'].strip() not in ['N/A', '', 'No data', '[ERROR']
            has_forums = today_data.get('forums.txt') and today_data['forums.txt'].strip() not in ['N/A', '', 'No data', '[ERROR']
            
            if not has_news and not has_forums:
                print(f"NARRATIVE {date}: No data")
                return None
            
            memory = super().load_memory(date)
            prompt = self.build_prompt(date, today_data, memory, has_news, has_forums)
            
            llm_response = self.call_llm(prompt)
            result = json.loads(llm_response)
            
            if not super().validate_output(result):
                print(f"NARRATIVE {date}: Validation failed")
                return None
            
            if not super().save_output(date, result):
                print(f"NARRATIVE {date}: Save failed")
                return None
            
            # Clean output
            model_used = result.get('metadata', {}).get('model', 'Unknown')
            if self.sticky_model_index != 0:
                print(f"NARRATIVE {date}: Complete ({model_used})")
            else:
                print(f"NARRATIVE {date}: Complete")
            
            return result
            
        except Exception as e:
            error_type = self._detect_error_type(str(e))
            print(f"NARRATIVE {date}: Failed ({error_type})")
            return None
    
    def build_prompt(self, date: str, today_data: Dict, memory: Optional[Dict], 
                     has_news: bool, has_forums: bool) -> str:
        memory_section = "First analysis - no historical context." if memory is None else f"MEMORY:\n{json.dumps(memory, indent=2)}"
        
        data_note = ""
        if not has_news:
            data_note = "NOTE: NEWS DATA MISSING - Analyze forums only\n"
        elif not has_forums:
            data_note = "NOTE: FORUMS DATA MISSING - Analyze news only\n"
        
        return f"""NARRATIVE analyst for gold intelligence system.

{memory_section}

{data_note}TODAY'S DATA ({date}):
News: {today_data.get('news.txt', 'N/A')}
Forums: {today_data.get('forums.txt', 'N/A')}

TASK: Analyze news headlines, social sentiment, catalysts, geopolitical risk, sentiment shifts.

Output regime: RISK_ON_NARRATIVE / RISK_OFF_NARRATIVE / NEUTRAL_NARRATIVE / BULLISH_SENTIMENT / BEARISH_SENTIMENT

Return ONLY valid JSON (NO confidence score):
{{"metadata":{{"agent":"narrative","date":"{date}","timestamp":"{datetime.now().isoformat()}","model":"[MODEL_NAME]"}},"data_snapshot":{{"dominant_story":"...","sentiment":"...","catalysts":"...","geopolitical":"...","data_quality":"{'partial - news only' if not has_forums else 'partial - forums only' if not has_news else 'complete'}"}},"analysis":{{"regime":"RISK_ON_NARRATIVE/RISK_OFF_NARRATIVE/NEUTRAL_NARRATIVE","trend":"...","key_drivers":["..."],"reasoning":"...","risk_factors":["..."]}},"memory_references":{{"compared_to":[],"corrections":[]}}}}"""
    
    def _detect_error_type(self, error_response: str) -> str:
        """Detect error type for minimal logging"""
        error_str = error_response.lower()
        
        if any(x in error_str for x in ["context_length", "token limit", "too many tokens"]):
            return "token limit"
        elif any(x in error_str for x in ["rate limit", "rate_limit"]):
            return "rate limit"
        elif any(x in error_str for x in ["timeout", "timed out"]):
            return "timeout"
        else:
            return "error"
    
    def _call_model_with_config(self, prompt: str, model_config: Dict) -> Tuple[bool, Optional[str], Optional[str]]:
        """Call a specific model configuration"""
        model_name = model_config['name']
        api_endpoint = model_config['api_endpoint']
        max_tokens = model_config['max_tokens']
        provider = model_config['provider']
        
        api_key = API_KEYS.get(provider, "")
        if not api_key:
            return False, None, "No API key"
        
        prompt_with_model = prompt.replace("[MODEL_NAME]", model_name)
        
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
                        {"role": "system", "content": "Respond ONLY with valid JSON. NO confidence scores."},
                        {"role": "user", "content": prompt_with_model}
                    ],
                    "temperature": self.config['temperature'],
                    "max_tokens": max_tokens
                },
                timeout=90
            )
            
            response.raise_for_status()
            content = response.json()['choices'][0]['message']['content'].strip()
            cleaned_content = content.replace('```json', '').replace('```', '').strip()
            
            return True, cleaned_content, None
            
        except Exception as e:
            error_msg = str(e)
            try:
                error_detail = response.json()
                error_msg = json.dumps(error_detail)
            except:
                pass
            
            return False, None, error_msg
    
    def call_llm(self, prompt: str) -> str:
        """Call LLM with sticky model logic and automatic fallback"""
        
        # Check if we should retry primary model
        if (STICKY_MODEL_CONFIG['enabled'] and 
            self.sticky_success_count >= STICKY_MODEL_CONFIG['retry_primary_after_days'] and
            self.sticky_model_index != 0):
            self.sticky_model_index = 0
            self.sticky_success_count = 0
        
        # Try sticky model first
        sticky_config = self.fallback_models[self.sticky_model_index]
        success, response, error = self._call_model_with_config(prompt, sticky_config)
        
        if success:
            self.sticky_success_count += 1
            return response
        
        # Sticky model failed - try full fallback chain
        for idx, model_config in enumerate(self.fallback_models):
            if idx == self.sticky_model_index:
                continue
            
            success, response, error = self._call_model_with_config(prompt, model_config)
            
            if success:
                self.sticky_model_index = idx
                self.sticky_success_count = 1
                return response
        
        # All models failed
        error_type = self._detect_error_type(str(error))
        raise Exception(f"All models failed ({error_type})")

if __name__ == "__main__":
    agent = NarrativeAgent()
    result = agent.analyze("2026-01-20")
    
    if result:
        print(f"\nModel: {result.get('metadata', {}).get('model')}")
        print(f"Regime: {result.get('analysis', {}).get('regime')}")
    
    print("\ndone")