import json
import requests
import re
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from config import API_KEYS, AGENT_CONFIGS, DATA_DIR, MONTHLY_REF_DIR, MONTHLY_DATA_FILE, MACRO_FALLBACK_MODELS, STICKY_MODEL_CONFIG
from base_agent import BaseAgent

class MacroAgent(BaseAgent):
    def __init__(self):
        super().__init__("macro")
        self.fallback_models = MACRO_FALLBACK_MODELS
        self.sticky_model_index = 0
        self.sticky_success_count = 0
        self.fundamentals_cache = {}
    
    def analyze(self, date: str) -> Optional[Dict]:
        """Override analyze to handle forward-fill and monthly context"""
        try:
            today_data = super().load_today_data(date)
            
            monthly_data = super().load_monthly_data()
            if monthly_data:
                today_data['monthly_data.txt'] = monthly_data
                self.update_monthly_reference_if_new(date, monthly_data)
            
            today_data = self.forward_fill_fundamentals(date, today_data)
            monthly_context = self.extract_monthly_context(monthly_data)
            
            has_fundamentals = today_data.get('fundamentals.txt') and today_data['fundamentals.txt'].strip() not in ['N/A', '', 'No data', '[ERROR']
            
            if not has_fundamentals:
                print(f"MACRO {date}: No data")
                return None
            
            memory = super().load_memory(date)
            prompt = self.build_prompt(date, today_data, memory, monthly_context)
            
            llm_response = self.call_llm(prompt)
            result = json.loads(llm_response)
            
            if not super().validate_output(result):
                print(f"MACRO {date}: Validation failed")
                return None
            
            if not super().save_output(date, result):
                print(f"MACRO {date}: Save failed")
                return None
            
            # Clean output
            model_used = result.get('metadata', {}).get('model', 'Unknown')
            if self.sticky_model_index != 0:
                print(f"MACRO {date}: Complete ({model_used})")
            else:
                print(f"MACRO {date}: Complete")
            
            return result
            
        except Exception as e:
            error_type = self._detect_error_type(str(e))
            print(f"MACRO {date}: Failed ({error_type})")
            return None
    
    def extract_monthly_context(self, monthly_data: Optional[str]) -> str:
        """Extract key monthly metrics"""
        if not monthly_data:
            return "No monthly data available"
        
        context_parts = []
        
        cpi_match = re.search(r'CPI[:\s]+([0-9.]+)%?\s*.*?(\d{4}-\d{2}-\d{2})?', monthly_data, re.IGNORECASE)
        if cpi_match:
            cpi_val = cpi_match.group(1)
            cpi_date = cpi_match.group(2) if cpi_match.group(2) else "date unknown"
            context_parts.append(f"CPI: {cpi_val}% (as of {cpi_date})")
        
        pce_match = re.search(r'PCE[:\s]+([0-9.]+)%?\s*.*?(\d{4}-\d{2}-\d{2})?', monthly_data, re.IGNORECASE)
        if pce_match:
            pce_val = pce_match.group(1)
            pce_date = pce_match.group(2) if pce_match.group(2) else "date unknown"
            context_parts.append(f"PCE: {pce_val}% (as of {pce_date})")
        
        ppi_match = re.search(r'PPI[:\s]+([0-9.]+)%?\s*.*?(\d{4}-\d{2}-\d{2})?', monthly_data, re.IGNORECASE)
        if ppi_match:
            ppi_val = ppi_match.group(1)
            ppi_date = ppi_match.group(2) if ppi_match.group(2) else "date unknown"
            context_parts.append(f"PPI: {ppi_val}% (as of {ppi_date})")
        
        if context_parts:
            return " | ".join(context_parts)
        else:
            return "Monthly data present but format unrecognized"
    
    def update_monthly_reference_if_new(self, date: str, monthly_data: str):
        """Update monthly reference file if new data detected"""
        try:
            monthly_file = MONTHLY_REF_DIR / MONTHLY_DATA_FILE
            
            if not monthly_file.exists():
                MONTHLY_REF_DIR.mkdir(parents=True, exist_ok=True)
                with open(monthly_file, 'w') as f:
                    f.write(monthly_data)
                return
            
            with open(monthly_file, 'r') as f:
                existing_data = f.read()
            
            if monthly_data.strip() != existing_data.strip():
                with open(monthly_file, 'w') as f:
                    f.write(monthly_data)
        
        except Exception:
            pass
    
    def forward_fill_fundamentals(self, date: str, today_data: Dict) -> Dict:
        """Forward-fill missing fundamental metrics (1-8 days back)"""
        fundamentals = today_data.get('fundamentals.txt', '').strip()
        
        if fundamentals and 'T10Y' in fundamentals and len(fundamentals) > 50 and not fundamentals.startswith('[ERROR'):
            self.fundamentals_cache[date] = fundamentals
            return today_data
        
        # Try 1-8 days back
        current_date = datetime.strptime(date, "%Y-%m-%d")
        for days_back in range(1, 9):
            lookback_date = (current_date - timedelta(days=days_back)).strftime("%Y-%m-%d")
            
            if lookback_date in self.fundamentals_cache:
                filled_data = self.fundamentals_cache[lookback_date]
                today_data['fundamentals.txt'] = f"""=== FORWARD-FILLED from {lookback_date} ===
(Market holiday/weekend - using previous available data)

{filled_data}

=== END FORWARD-FILL ==="""
                print(f"MACRO {date}: Forward-filled from -{days_back}d")
                return today_data
            
            try:
                lookback_path = DATA_DIR / lookback_date / 'fundamentals.txt'
                if lookback_path.exists():
                    with open(lookback_path, 'r') as f:
                        filled_data = f.read().strip()
                    
                    if filled_data and 'T10Y' in filled_data and len(filled_data) > 50 and not filled_data.startswith('[ERROR'):
                        self.fundamentals_cache[lookback_date] = filled_data
                        today_data['fundamentals.txt'] = f"""=== FORWARD-FILLED from {lookback_date} ===
(Market holiday/weekend - using previous available data)

{filled_data}

=== END FORWARD-FILL ==="""
                        print(f"MACRO {date}: Forward-filled from -{days_back}d")
                        return today_data
            
            except Exception:
                continue
        
        return today_data
    
    def build_prompt(self, date: str, today_data: Dict, memory: Optional[Dict], monthly_context: str) -> str:
        memory_section = "First analysis - no historical context." if memory is None else f"MEMORY:\n{json.dumps(memory, indent=2)}"
        
        is_forward_filled = 'FORWARD-FILLED' in today_data.get('fundamentals.txt', '')
        forward_fill_note = ""
        if is_forward_filled:
            forward_fill_note = "\nNOTE: Fundamentals data is FORWARD-FILLED from previous day (weekend/holiday).\n"
        
        return f"""MACRO analyst for gold intelligence system.

{memory_section}

MONTHLY CONTEXT (include in EVERY data_snapshot):
{monthly_context}

{forward_fill_note}TODAY'S DATA ({date}):
Calendar: {today_data.get('calendar.txt', 'N/A')}
Fundamentals: {today_data.get('fundamentals.txt', 'N/A')}
Monthly: {today_data.get('monthly_data.txt', 'N/A')}

CRITICAL INSTRUCTIONS:

1. MONTHLY CONTEXT: Include in data_snapshot EVERY day as "monthly_context": "{monthly_context}"
2. REAL RATE: T10Y - CPI_YoY (>1.5% bearish gold, <0% bullish gold)
3. FED POLICY: Analyze FEDFUNDS and calendar events

Return ONLY valid JSON (NO confidence score):
{{"metadata":{{"agent":"macro","date":"{date}","timestamp":"{datetime.now().isoformat()}","model":"[MODEL_NAME]"}},"data_snapshot":{{"economic_events":"...","rates":"T10Y: X.XX%, FEDFUNDS: X.XX%","inflation":"CPI YoY: X.XX%","real_rate":"calculation shown","monthly_context":"{monthly_context}"}},"analysis":{{"regime":"RISK_ON/RISK_OFF/NEUTRAL","trend":"dovish/hawkish/neutral","key_drivers":["..."],"reasoning":"...","risk_factors":["..."]}},"memory_references":{{"compared_to":[],"corrections":[]}}}}"""
    
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
                        {"role": "system", "content": "Financial analyst. Respond ONLY with valid JSON. NO confidence scores."},
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
    agent = MacroAgent()
    result = agent.analyze("2026-01-20")
    
    if result:
        print(f"\nModel: {result.get('metadata', {}).get('model')}")
        print(f"Regime: {result.get('analysis', {}).get('regime')}")
    
    print("\ndone")