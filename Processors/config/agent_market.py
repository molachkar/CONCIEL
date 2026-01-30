import json
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from config import API_KEYS, AGENT_CONFIGS, AGENT_OUTPUT_DIR, MARKET_FALLBACK_MODELS, STICKY_MODEL_CONFIG
from base_agent import BaseAgent

class MarketAgent(BaseAgent):
    def __init__(self):
        super().__init__("market")
        self.fallback_models = MARKET_FALLBACK_MODELS
        self.sticky_model_index = 0  # Start with priority 1
        self.sticky_success_count = 0  # Count successful runs with sticky model
        self.api_key = API_KEYS.get("sambanova", "")
    
    def analyze(self, date: str) -> Optional[Dict]:
        """Override analyze to handle weekend forward-fill"""
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            is_weekend = date_obj.weekday() in [5, 6]
            
            if is_weekend:
                return self.forward_fill_weekend(date)
            
            return super().analyze(date)
            
        except Exception as e:
            print(f"MARKET {date}: Failed - {str(e)[:50]}")
            return None
    
    def forward_fill_weekend(self, date: str) -> Optional[Dict]:
        """For weekends, copy the last Friday's analysis"""
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        
        for days_back in range(1, 4):
            lookback_date = (date_obj - timedelta(days=days_back)).strftime("%Y-%m-%d")
            lookback_file = AGENT_OUTPUT_DIR / "market" / f"{lookback_date}.json"
            
            if lookback_file.exists():
                try:
                    with open(lookback_file, 'r') as f:
                        last_trading_data = json.load(f)
                    
                    weekend_data = {
                        "metadata": {
                            "agent": "market",
                            "date": date,
                            "timestamp": datetime.now().isoformat(),
                            "model": last_trading_data.get('metadata', {}).get('model', 'Unknown'),
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
                    
                    if super().save_output(date, weekend_data):
                        print(f"MARKET {date}: Forward-filled from {lookback_date}")
                        return weekend_data
                    
                except Exception:
                    continue
        
        print(f"MARKET {date}: No recent data for forward-fill")
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
{{"metadata":{{"agent":"market","date":"{date}","timestamp":"{datetime.now().isoformat()}","model":"[MODEL_NAME]"}},"data_snapshot":{{"price_action":"...","momentum":"...","volatility":"...","cross_assets":"..."}},"analysis":{{"regime":"BREAKOUT/BREAKDOWN/CONSOLIDATION/RISK_ON/RISK_OFF","trend":"...","key_drivers":["..."],"reasoning":"...","risk_factors":["..."]}},"memory_references":{{"compared_to":[],"corrections":[]}}}}"""
    
    def _detect_error_type(self, error_response: Dict) -> str:
        """Detect error type for minimal logging"""
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
                        {"role": "system", "content": "Respond ONLY with valid JSON. Do not include confidence scores."},
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
        
        # Check if we should retry primary model after N successful days
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
        error_type = self._detect_error_type(error)
        switched_to = None
        
        for idx, model_config in enumerate(self.fallback_models):
            if idx == self.sticky_model_index:
                continue  # Already tried
            
            success, response, error = self._call_model_with_config(prompt, model_config)
            
            if success:
                # Update sticky model
                old_model = self.fallback_models[self.sticky_model_index]['name']
                new_model = model_config['name']
                self.sticky_model_index = idx
                self.sticky_success_count = 1
                
                # Only print if switching models (not first run)
                if self.sticky_success_count > 1 or old_model != new_model:
                    switched_to = new_model
                
                return response
        
        # All models failed
        raise Exception(f"All models failed ({error_type})")
    
    def analyze(self, date: str) -> Optional[Dict]:
        """Override with clean output"""
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            is_weekend = date_obj.weekday() in [5, 6]
            
            if is_weekend:
                result = self.forward_fill_weekend(date)
                return result
            
            # Normal weekday processing
            result = super().analyze(date)
            
            if result:
                model_used = result.get('metadata', {}).get('model', 'Unknown')
                # Only show model if it's not the first priority model
                if self.sticky_model_index != 0:
                    print(f"MARKET {date}: Complete ({model_used})")
                else:
                    print(f"MARKET {date}: Complete")
            
            return result
            
        except Exception as e:
            error_type = self._detect_error_type(str(e))
            print(f"MARKET {date}: Failed ({error_type})")
            return None

if __name__ == "__main__":
    agent = MarketAgent()
    result = agent.analyze("2026-01-20")
    
    if result:
        print(f"\nModel: {result.get('metadata', {}).get('model')}")
        print(f"Regime: {result.get('analysis', {}).get('regime')}")
    
    print("\ndone")